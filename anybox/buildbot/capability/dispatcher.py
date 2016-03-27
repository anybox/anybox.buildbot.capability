"""Core functionnality to manipulate capabilities."""

import re
from copy import deepcopy

from buildbot.plugins import util

from .version import Version
from .version import NOT_USED


RE_PROP_CAP_OPT = re.compile(r'cap\((\w*)\)')


def does_meet_requirements(caps, requirements):
    """True if a worker capabilities fulfills all requirements.

    :param caps: the capabilities to check (a :class:`dict` whose keys
                 are capability names, and values an iterable of version
                 options
    :param requirements: a :class:`VersionFilter` instance
    """
    for req in requirements:
        version_options = caps.get(req.cap)
        if version_options is None:
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

    """
    def __init__(self, workers, capabilities):
        self.all_workers = workers
        self.capabilities = capabilities

    def make_builders(self, name, factory, build_for=None, build_requires=(),
                      **kw):
        """Produce the builder configurations for the given build factory.

        :param name: base name for the builders.
        :param factory: :class:`BuildFactory` instance
        :param build_requires: list of capability requirements that the
                               worker must match to run a builder
                               from the factory.
        :param build_for: a dict whose keys are capability names and values are
                          corresponding :class:`VersionFilter` instances.
        :param kw: all remaining keyword arguments are forwarded to
                   :class:`BuilderConfig` instantiation.
        :returns: a list of :class:`BuilderConfig` instances
        """
        workernames = self.filter_workers_by_requires(build_requires)
        if not workernames:
            # buildbot does not allow builder configs with empty list of workers
            return ()

        base_conf = dict(name=name,
                         factory=factory,
                         workernames=list(workernames))
        base_conf.update(kw)

        # forward requirement in the build properties
        if build_requires:
            base_conf['properties'] = dict(
                build_requires=[str(req) for req in build_requires])

        preconfs = [base_conf]
        for cap_name, cap_vf in build_for.items():
            preconfs = self.dispatch_builders_by_capability(
                preconfs, cap_name, cap_vf)

        return [util.BuilderConfig(**conf) for conf in preconfs]

    def dispatch_builders_by_capability(self, builders, cap, cap_vf):
        """Take a list of builders parameters and redispatch by capability.

        :param builders: iterable of dicts with keywords arguments to create
                         ``BuilderConfig instances. These are not directly
                         ``BuilderConfig`` instances because they are not ready
                          yet to pass the constructor's validation

                          They need to have the ``workernames`` and
                          ``properties`` keys.

        :param cap: capability name
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
        capdef = self.capabilities[cap]
        prop = capdef['version_prop']
        if cap_vf is not None and cap_vf.criteria == (NOT_USED, ):
            # This is a marker to explicitely say that the capability does not
            # matter. For instance, in the case of PostgreSQL, this helps
            # spawning builds that ignore it entirely
            for builder in builders:
                builder.setdefault('properties', {})[prop] = 'not-used'
            return builders

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
