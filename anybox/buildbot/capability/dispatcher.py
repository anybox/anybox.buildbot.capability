"""Core functionnality to manipulate capabilities."""

import re
from copy import deepcopy

from buildbot.plugins import util

from .version import Version
from .steps import SetCapabilityProperties
from .constants import CAPABILITY_PROP_FMT

RE_PROP_CAP_OPT = re.compile(r'cap\((\w*)\)')
Interpolate = util.Interpolate

_missing_cap = object()


def does_meet_requirements(caps, requirements):
    """True if a worker capabilities fulfills all requirements.

    :param caps: the capabilities to check, a :class:`dict` whose keys
                 are capability names, and values an iterable of version
                 options
    :param requirements: a :class:`VersionFilter` instance
    """
    for req in requirements:
        version_options = caps.get(req.cap, _missing_cap)
        if version_options is _missing_cap:
            return False
        if version_options is None:
            if req.match(None):
                continue
            return False
        for version in version_options:
            if req.match(Version.parse(version)):
                break
        else:
            return False
    return True


class BuilderDispatcher(object):
    """Provide the means to spawn builders according to capability settings.

    This class implements:

      - filtering by capability
      - creation of variants according to capabilities
      - setting properties in the build derived from capability version and
        options

    The ``capabilities`` attribute describes the available capabilities,
    and governs how they will interact with the build. Here's an example::

      dict(python=dict(version_prop='py_version',
                       abbrev='py'),
           postgresql=dict(version_prop='pg_version',
                           abbrev='pg',
                           environ={'PGPORT': '%(cap(port):-)s',
                                    'PGHOST': '%(cap(host):-)s',
                                    'LD_LIBRARY_PATH': '%(cap(lib):-)s',
                                    'PATH': '%(cap(bin):-)s',
                                    'PGCLUSTER': '%(prop:pg_version:-)s/main',
                                    },
                           ))

    """
    def __init__(self, workers, capabilities):
        self.all_workers = dict((worker.workername, worker)
                                for worker in workers)
        self.capabilities = capabilities

    def set_properties_make_environ(self, factory, cap_names):
        """Add property setting steps to factory and return environment vars.

        :returns: a :class:`dict` suitable to pass as ``env`` in subsequent
                  :class:`ShellCommand` steps, using :class:`Interpolate`
        :param cap_names: iterable of capability names to consider
        :param factory: a :class:`BuildFactory` instance.

        *Example usage*: assume the ``self.capability`` :class:`dict`
                         contains this::

           'capname' : dict(version_prop='the_cap_version',
                             environ={'CAPABIN': '%(cap(bin))s/prog'})

        For a build occuring on a worker with the ``capname`` capability, in
        version ``x.y`` and options ``bin=/usr/local/capname/bin``, one will
        get

        * a build property ``cap_capname_bin``, with value
          ``/usr/local/capname/bin``, available to the steps that have been
          added after the call to this method,
        * a return value of::

            {'CAPABIN': Interpolate('%(prop:cap_capname_bin)s/prog')}

          meaning at at build time, if used to construct the environment in a
          build step, it will evaluate as::

            ``CAPABIN=/usr/local/capname/bin/prog``

        This demonstrates in particular how values of the ``environ`` subdicts
        are meant for :class:`Interpolate`, with substitution of
        ``cap(<option>)`` by
        the property that will hold the value of this capability option.
        Apart from this substitution, the full expressivity of
        :class:`Interpolate` applies.

        As a special case, the ``PATH`` environment variable is always an
        insertion at the beginning of the list.

        The limitation of considered capabilities by means of the ``cap_names``
        parameter avoids to spawn  absurd build steps that aren't needed for
        this factory, or even can't actually run, as one would get if we used
        all registered capabilities.

        TODO: adapt this explanations for this standalone version of
        capability system:

        The ``capability`` dict property value is expected to be set by the
        :class:`Worker` instantiation. The build steps set by this method
        will extract them as regular properties, which the returned environ
        dict uses, and can also be used freely in steps added after this point.
        """
        capability_env = {}

        for cap_name in cap_names:
            capability = self.capabilities.get(cap_name)
            if capability is None:
                continue
            factory.addStep(SetCapabilityProperties(
                cap_name,
                description=["Setting", cap_name, "properties"],
                descriptionDone=["Set", cap_name, "properties"],
                name="props_" + cap_name,
                capability_version_prop=capability.get('version_prop'),
            ))
            to_env = capability.get('environ')
            if not to_env:
                continue
            for env_key, interpolation in to_env.items():
                def replace(m):
                    return 'prop:' + CAPABILITY_PROP_FMT % (
                        cap_name, m.group(1))
                var = Interpolate(RE_PROP_CAP_OPT.sub(replace, interpolation))
                if env_key == 'PATH':
                    var = [var, '${PATH}']
                capability_env[env_key] = var

        return capability_env

    def make_builders(self, name, factory, build_for=(), build_requires=(),
                      **kw):
        """Produce the builder configurations for the given build factory.

        :param name: base name for the builders.
        :param factory: :class:`BuildFactory` instance
        :param build_requires: list of capability requirements that the
                               worker must match to run a builder
                               from the factory.
        :param build_for: an iterable of `VersionFilter` instances.
                          They will be used in order to create combinations
                          from the matches they find in :attr:`all_workers`
        :param kw: all remaining keyword arguments are forwarded to
                   :class:`BuilderConfig` instantiation.
        :returns: a list of :class:`BuilderConfig` instances
        """
        workernames = self.filter_workers_by_requires(build_requires)
        if not workernames:
            # buildbot does not allow builder configs with empty list of workers
            return ()

        base_conf = dict(name=name, workernames=list(workernames))

        # forward requirement in the build properties
        if build_requires:
            base_conf['properties'] = dict(
                build_requires=[str(req) for req in build_requires])

        preconfs = [base_conf]
        for version_filter in build_for:
            preconfs = self.dispatch_builders_by_capability(
                preconfs, version_filter)

        builders = []
        for conf in preconfs:
            conf.update(factory=factory, **kw)
            builders.append(util.BuilderConfig(**conf))
        return builders

    def dispatch_builders_by_capability(self, builders, cap_vf):
        """Take a list of builders parameters and redispatch by capability.

        :param builders: iterable of dicts with keywords arguments to create
                         ``BuilderConfig instances. These are not directly
                         ``BuilderConfig`` instances because they are not ready
                          yet to pass the constructor's validation

                          They need to have the ``workernames`` and
                          ``properties`` keys.

        :param cap_vf: capability version filter controlling the dispatching.
                       ``None`` meaning that the capability is ignored
        :param prop: the capability controlling property
                     (e.g., ``'pg_version'`` for the PostgreSQL capability)

        This is meant to refine it by successive iterations.
        Example with two capabilities::
        (b1, b2) ->
        (b1-pg9.1, b2-pg9.2) ->
        (b1-pg9.1-py3.4, b1-pg9.1-py3.5, b2-pg9.2-py3.4, b2-pg9.2-py3.5)

        Of course the list of workers and properties are refined at each
        step. The idea is that only the latest such list will actually
        get registered.
        """
        res = []
        cap = cap_vf.cap
        capdef = self.capabilities[cap]
        prop = capdef['version_prop']
        abbrev = capdef.get('abbrev', cap)
        for builder in builders:
            for cap_version, workernames in self.split_workers_by_capability(
                    cap, builder['workernames']).items():

                if cap_vf is not None and not cap_vf.match(
                        Version.parse(cap_version)):
                    continue

                refined = deepcopy(builder)
                refined['workernames'] = workernames
                refined.setdefault('properties', {})[prop] = cap_version
                refined['name'] = '%s-%s%s' % (
                    builder['name'], abbrev, cap_version)
                res.append(refined)
        return res

    def split_workers_by_capability(self, cap, workernames):
        """Organize an iterable of workernames into a dict capability versions.

        Each available version of the capability among the workers with given
        names is a key of the returned dict, and the corresponding value is the
        list of those that have it.
        """
        res = {}

        for workername in workernames:
            worker = self.all_workers[workername]
            versions = worker.properties['capability'].get(cap)
            if versions is None:
                continue
            for version in versions:
                res.setdefault(version, []).append(workername)
        return res

    def only_if_requires(self, worker):
        """Shorcut for extraction of build-only-if-requires tokens."""
        only = worker.properties.getProperty('build-only-if-requires')
        return set(only.split()) if only is not None else set()

    def filter_workers_by_requires(self, requires):
        """Return an iterable of workernames meeting the requirements.

        The special ``build-only-if-requires`` worker attribute is taken into
        account.
        """

        require_names = set(req.cap for req in requires)
        return [workername
                for workername, worker in self.all_workers.items()
                if does_meet_requirements(
                    worker.properties['capability'], requires) and
                self.only_if_requires(worker).issubset(require_names)]
