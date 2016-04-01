# This file is part of anybox.buildbot.capability.
# anybox.buildbot.capability is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, If not, see <http://www.gnu.org/licenses/>.
#
# Copyright Georges Racinet <gracinet@anybox.fr>

import unittest
from ..dispatcher import BuilderDispatcher
from ..version import Version, VersionFilter
from ..steps import SetCapabilityProperties

from buildbot.plugins import util

CAPABILITIES = dict(
    python=dict(version_prop='py_version',
                abbrev='py',
                environ={'PYTHONBIN': '%(cap(bin):-python)s'}),
    postgresql=dict(version_prop='pg_version',
                    abbrev='pg',
                    environ={'PGPORT': '%(cap(port):-)s',
                             'PGHOST': '%(cap(host):-)s',
                             'LD_LIBRARY_PATH': '%(cap(lib):-)s',
                             'PATH': '%(cap(bin):-)s',
                             'PGCLUSTER': '%(prop:pg_version:-)s/main',
                             }),
    without_env=dict(version_prop='wev', abbrev='we')
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


class DispatcherTestCase(unittest.TestCase):

    def setUp(self):
        self.factory = util.BuildFactory()
        self.make_workers()
        self.make_dispatcher()

    def make_dispatcher(self):
        self.dispatcher = BuilderDispatcher(self.workers, CAPABILITIES)

    def dispatch(self, **kw):
        return dict((b.name, b)
                    for b in self.dispatcher.make_builders(
                            'bldr', self.factory, **kw))


class TestDispatcherBuildFor(DispatcherTestCase):

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

    def test_build_for_greater(self):
        builders = self.dispatch(
            build_for=[VersionFilter('postgresql', ('>', Version(9, 0)))])
        self.assertEqual(builders.keys(), ['bldr-pg9.1-devel'])

    def test_build_for_unpresent(self):
        """build_for discards workers that don't have the capability at all."""
        self.workers.append(FakeWorker('nopg', props=dict(
            capability={'python': {'2.7': {}}})))
        self.make_dispatcher()
        builders = self.dispatch(
            build_for=[VersionFilter('postgresql', ('>', Version(9, 0)))])
        self.assertEqual(builders.keys(), ['bldr-pg9.1-devel'])
        self.assertEqual(builders['bldr-pg9.1-devel'].workernames,
                         ['w90-91'])

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


class TestDispatcherBuildRequires(DispatcherTestCase):

    def make_workers(self):
        self.workers = [
            FakeWorker('privcode', props=dict(
                capability={'private-code-access': {None: {}},
                            'postgresql': {'8.4': {},
                                           '9.1-devel': {'port': '5433'}},
                            })),
            FakeWorker('privcode-84', props=dict(
                capability={'private-code-access': {None: {}},
                            'postgresql': {'8.4': {}}
                            })),
            FakeWorker('privcode-91', props=dict(
                capability={'private-code-access': None,
                            'postgresql': {'9.1-devel': {}}
                            })),
            FakeWorker('pg90-91', props=dict(
                capability={'postgresql': {'9.0': {'port': '5434'},
                                           '9.1-devel': {'port': '5433'}},
                            })),
            FakeWorker('rabb284', props=dict(
                capability={'rabbitmq': {'2.8.4': {}},
                            'postgresql': {'9.0': {'port': 5434}}
                            })),
            FakeWorker('rabb18', props=dict(
                capability={'rabbitmq': {'1.8': {}},
                            'postgresql': {'9.0': {'port': 5434}}
                            })),
        ]

    def test_build_requires_for_all_versions(self):
        builders = self.dispatch(
            build_requires=[VersionFilter('private-code-access', ())],
            build_for=[VersionFilter('postgresql', ())],
        )
        self.assertEqual(set(builders),
                         set(('bldr-pg8.4',
                              'bldr-pg9.1-devel',)))
        self.assertEqual(builders['bldr-pg8.4'].workernames,
                         ['privcode', 'privcode-84'])
        self.assertEqual(builders['bldr-pg9.1-devel'].workernames,
                         ['privcode', 'privcode-91'])

    def test_build_requires_for_restrictive(self):
        builders = self.dispatch(
            build_requires=[VersionFilter('private-code-access', ())],
            build_for=[VersionFilter('postgresql', ('>', Version(9, 0)))],
        )
        self.assertEqual(builders.keys(), ['bldr-pg9.1-devel'])
        self.assertEqual(builders['bldr-pg9.1-devel'].workernames,
                         ['privcode', 'privcode-91'])

    def test_build_requires_version(self):
        rabbit_vf = VersionFilter('rabbitmq', ('>=', Version(2, 0)))
        builders = self.dispatch(
            build_requires=[rabbit_vf],
            build_for=[VersionFilter('postgresql', ('==', Version(9, 0)))],
        )
        self.assertEqual(builders.keys(), ['bldr-pg9.0'])
        builder = builders['bldr-pg9.0']
        self.assertEqual(builder.workernames, ['rabb284'])

        build_requires = builder.properties['build_requires']
        self.assertEqual(len(build_requires), 1)
        # these tests are written to be independent of actual string
        # representation, hence we reparse from here
        self.assertEqual(VersionFilter.parse(build_requires.pop()),
                         rabbit_vf)

    def test_build_requires_2(self):
        rabbit_vf = VersionFilter('rabbitmq', ('==', Version(1, 8)))
        builders = self.dispatch(
            build_requires=[rabbit_vf],
            build_for=[VersionFilter('postgresql', ('==', Version(9, 0)))],
        )
        self.assertEqual(builders.keys(), ['bldr-pg9.0'])
        self.assertEqual(builders['bldr-pg9.0'].workernames, ['rabb18'])

    def test_build_requires_None_on_worker(self):
        self.workers.append(
            FakeWorker('Nonewk', props=dict(
                capability={'rabbitmq': None,
                            'postgresql': {'9.0': {'port': 5434}}
                            })))
        self.make_dispatcher()
        self.test_build_requires_2()

    def test_build_requires_no_match(self):
        builders = self.dispatch(
            build_requires=[VersionFilter('rabbitmq', ('==', Version(1, 9)))],
        )
        self.assertEqual(builders, {})

    def test_build_requires_only_if(self):
        self.workers[0].properties['build-only-if-requires'] = 'private-code-access'
        builders = self.dispatch(
            build_for=[VersionFilter('postgresql', ('>', Version(9, 0)))],
        )
        self.assertEqual(builders.keys(), ['bldr-pg9.1-devel'])
        # does not run on 'privcode' worker, since the 'private-code-access'
        # is not required
        self.assertEqual(builders['bldr-pg9.1-devel'].workernames,
                         ['privcode-91', 'pg90-91'])


class TestDispatcherEnviron(DispatcherTestCase):

    def make_workers(self):
        self.workers = [
            FakeWorker('two-pg-one-py', props=dict(
                capability={'selenium': {None: {}},  # not registered
                            'without_env': {'1.2': {'port': '5000'}},
                            'python': {'2.6': {'bin': 'python2.6'}},
                            'postgresql': {'9.1': {'port': '5432'},
                                           '9.2': {'port': '5433'}},
                            })),
                        ]

    def test_capability_env(self):
        factory = util.BuildFactory()
        env = self.dispatcher.set_properties_make_environ(
            factory, ('python', 'postgresql', 'selenium', 'without_env'))

        self.assertEqual(env['PGPORT'],
                         util.Interpolate('%(prop:cap_postgresql_port:-)s'))
        self.assertEqual(env['PYTHONBIN'],
                         util.Interpolate('%(prop:cap_python_bin:-python)s'))
        self.assertEqual(env['PATH'],
                         [util.Interpolate('%(prop:cap_postgresql_bin:-)s'),
                          '${PATH}'])

        steps = dict((s.kwargs['name'], s) for s in factory.steps
                     if s.factory is SetCapabilityProperties)

        self.assertTrue('props_python' in steps)
        prop_step = steps['props_python']
        self.assertEquals(prop_step.args, ('python',))
        self.assertEquals(prop_step.kwargs['capability_version_prop'],
                          'py_version')

        self.assertTrue('props_postgresql' in steps)
        prop_step = steps['props_postgresql']
        self.assertEquals(prop_step.args, ('postgresql',))
        self.assertEquals(prop_step.kwargs['capability_version_prop'],
                          'pg_version')

        self.assertTrue('props_without_env' in steps)
        prop_step = steps['props_without_env']
        self.assertEquals(prop_step.args, ('without_env',))
        self.assertEquals(prop_step.kwargs['capability_version_prop'], 'wev')
