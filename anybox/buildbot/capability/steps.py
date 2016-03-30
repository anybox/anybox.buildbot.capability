"""Common build steps."""
import random

from buildbot.process.buildstep import LoggingBuildStep
from buildbot.process.buildstep import SUCCESS
from buildbot.process.buildstep import FAILURE  # NOQA

from .constants import CAPABILITY_PROP_FMT
from .version import Version, VersionFilter


class DescriptionBuildStep(LoggingBuildStep):
    """A base buildstep with description class.


    The goal is to factor out processing of description related kwargs in init.
    """

    def __init__(self, description=None, descriptionDone=None,
                 descriptionSuffix=None, **kw):
        LoggingBuildStep.__init__(self, **kw)

        # GR: taken from master, apparently not handled by base class
        if description:
            self.description = description
        if isinstance(description, basestring):
            self.description = [self.description]
        if descriptionDone:
            self.descriptionDone = descriptionDone
        if isinstance(descriptionDone, basestring):
            self.descriptionDone = [self.descriptionDone]
        if descriptionSuffix:
            self.descriptionSuffix = descriptionSuffix
        if isinstance(descriptionSuffix, basestring):
            self.descriptionSuffix = [self.descriptionSuffix]


class SetCapabilityProperties(DescriptionBuildStep):
    """Set capability related properties.

    Example behaviour::

          capa_name 1.3 port=1234

    will produce a property ``capability_capa_name_port`` with value ``1234``.
    """

    def __init__(self, capability_name,
                 capability_prop='capability',
                 build_requires_prop='build_requires',
                 capability_version_prop=None,
                 **kw):
        """

        capability_prop is the name of the complex worker-level property
        entirely describing the capabilities
        capability_version_prop is the name of the property (builder-level)
        giving the version capability to take into account.
        """
        DescriptionBuildStep.__init__(self, **kw)
        self.capability_name = capability_name
        self.capability_prop = capability_prop
        self.build_requires_prop = build_requires_prop
        self.capability_version_prop = capability_version_prop

    def start(self):
        cap_details = self.getProperty(self.capability_prop)[
            self.capability_name]
        if not cap_details:
            self.finished(SUCCESS)
            return

        logs = []
        # apply build_requires, if submitted
        build_requires = self.getProperty(self.build_requires_prop, {})
        for req in build_requires:
            req = VersionFilter.parse(req)
            if req.cap != self.capability_name:
                continue
            cap_details = dict(
                (v, o) for (v, o) in cap_details.items()
                if req.match(Version.parse(v)))

        options = None
        if self.capability_version_prop:
            cap_version = self.getProperty(self.capability_version_prop)
            if cap_version is not None:
                options = cap_details[cap_version]

        if options is None:
            # either we have no version property or it is not set
            # (can happen if several versions on this worker match the
            # requirement)
            # this is a peculiar case, but it can happen that a build
            # truly does not care about the version of the capability.
            choice = random.choice(cap_details.keys())
            logs.append("On worker %r, the following versions of capability %r "
                        "are applicable for this build: "
                        "%r, picking %r at random" % (
                            self.capability_name,
                            self.getProperty('workername'),
                            cap_details.keys(),
                            choice))
            options = cap_details[choice]

        for opt, value in options.items():
            prop = CAPABILITY_PROP_FMT % (self.capability_name, opt)
            logs.append("%s: %r" % (prop, value))
            self.setProperty(prop, value, 'Capability')

        self.addCompleteLog('property changes', "\n".join(logs))
        self.finished(SUCCESS)
