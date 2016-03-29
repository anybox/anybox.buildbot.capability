import unittest
from ..dispatcher import BuilderDispatcher
from ..version import Version, VersionFilter

from buildbot.plugins import util

CAPABILITIES = dict(
    python=dict(version_prop='py_version',
                abbrev='py',
                environ={}),
    postgresql=dict(version_prop='pg_version',
                    abbrev='pg',
                    environ={'PGPORT': '%(cap(port):-)s',
                             'PGHOST': '%(cap(host):-)s',
                             'LD_LIBRARY_PATH': '%(cap(lib):-)s',
                             'PATH': '%(cap(bin):-)s',
                             'PGCLUSTER': '%(prop:pg_version:-)s/main',
                             }),
)


class FakeProperties(dict):

    def getProperty(self, k):
        return self.get(k)


class FakeWorker(object):

    def __init__(self, name, props=None):
        self.workername = name
        self.properties = FakeProperties()
        if props is not None:
            self.properties.update(props)


class TestDispatcher(unittest.TestCase):

    def setUp(self):
        self.factory = util.BuildFactory()
        self.make_workers()
        self.make_dispatcher()

    def make_workers(self):
        self.workers = [
            FakeWorker('w84', props=dict(
                capability={'python': {'2.4': {}},
                            'postgresql': {'8.4': {}}}
                       )),
            FakeWorker('w90-91', props=dict(
                capability={'python': {'2.6': {}},
                            'postgresql': {'9.0': {'port': '5434'},
                                           '9.1-devel': {'port': '5433'}}}
                       )),
            FakeWorker('w83', props=dict(
                capability={'python': {'2.7': {}},
                            'postgresql': {'8.3': {}}}
                       )),
        ]

    def make_dispatcher(self):
        self.dispatcher = BuilderDispatcher(self.workers, CAPABILITIES)

    def dispatch(self, **kw):
        return dict((b.name, b)
                    for b in self.dispatcher.make_builders(
                            'bldr', self.factory, **kw))

    def test_build_for_greater(self):
        builders = self.dispatch(
            build_for=[VersionFilter('postgresql', ('>', Version(9, 0)))])
        self.assertEqual(builders.keys(), ['bldr-pg9.1-devel'])

    def test_build_for_range(self):
        builders = self.dispatch(
            build_for=[VersionFilter('postgresql',
                                     ('AND',
                                      ('>=', Version(8, 4)),
                                      ('<=', Version(9, 1))))])
        self.assertEqual(set(builders),
                         set(('bldr-pg8.4',
                              'bldr-pg9.0',
                              'bldr-pg9.1-devel')))

    def test_build_for_or_statement(self):
        builders = self.dispatch(
            build_for=[VersionFilter('postgresql',
                                     ('OR',
                                      ('>', Version(9, 0)),
                                      ('==', Version(8, 4))))])
        self.assertEqual(set(builders),
                         set(('bldr-pg8.4',
                              'bldr-pg9.1-devel')))

    def test_build_for2cap(self):
        """build_for dispatching for two capabilities."""
        builders = self.dispatch(
            build_for=(VersionFilter('postgresql',
                                     ('AND',
                                      ('>=', Version(8, 4)),
                                      ('<=', Version(9, 1)))),
                       VersionFilter('python', ('>=', Version(2, 6))),
                       ))
        self.assertEqual(set(builders),
                         set(('bldr-pg9.1-devel-py2.6',
                              'bldr-pg9.0-py2.6')))

    def test_build_for2cap_more(self):
        """build_for dispatching for two capabilities, with more combinations"""
        builders = self.dispatch(
            build_for=(VersionFilter('postgresql',
                                     ('AND',
                                      ('>=', Version(8, 4)),
                                      ('<=', Version(9, 1)))),
                       VersionFilter('python', ()),
                       ))
        self.assertEqual(set(builders),
                         set(('bldr-pg9.1-devel-py2.6',
                              'bldr-pg8.4-py2.4',
                              'bldr-pg9.0-py2.6')))
        self.assertEqual(
            builders['bldr-pg9.0-py2.6'].properties,
            dict(pg_version='9.0', py_version='2.6'))
        self.assertEqual(
            builders['bldr-pg8.4-py2.4'].properties,
            dict(pg_version='8.4', py_version='2.4'))
        self.assertEqual(
            builders['bldr-pg9.1-devel-py2.6'].properties,
            dict(pg_version='9.1-devel', py_version='2.6'))

    def test_build_for2cap_or(self):
        """build_for dispatching for two capabilities with OR, one solution"""
        builders = self.dispatch(
            build_for=(VersionFilter('postgresql',
                                     ('OR',
                                      ('>', Version(9, 0)),
                                      ('==', Version(8, 4)))),
                       VersionFilter('python', ('<', Version(2, 6))),
                       ))
        self.assertEqual(builders.keys(), ['bldr-pg8.4-py2.4'])

    def test_build_for_2cap_2(self):
        """build-for dispatching for two capabilities, another conf"""
        del self.workers[0]
        self.workers.append(
            FakeWorker('w90',
                       props=dict(capability={'python': {'2.7': {}},
                                              'postgresql': {'9.0': {}},
                                              })))
        self.make_dispatcher()

        builders = self.dispatch(
            build_for=(VersionFilter('postgresql',
                                     ('AND',
                                      ('>=', Version(8, 4)),
                                      ('<=', Version(9, 1)))),
                       VersionFilter('python', ('>=', Version(2, 6))),
                       ))

        self.assertEqual(set(builders),
                         set(('bldr-pg9.0-py2.6',
                              'bldr-pg9.0-py2.7',
                              'bldr-pg9.1-devel-py2.6',
                              )))

        self.assertEqual(
            self.dispatch(
                build_for=(VersionFilter('postgresql',
                                         ('OR',
                                          ('==', Version(8, 4)),
                                          ('>', Version(9, 0)))),
                           VersionFilter('python', ('<', Version(2, 6))),
                           )),
            {})

        self.assertEqual(
            self.dispatch(
                build_for=(VersionFilter('postgresql', ('>', Version(9, 0))),
                           VersionFilter('python', ('==', Version(2, 7)))),
                           ),
            {})
