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
from buildbot.process.buildstep import SUCCESS
from buildbot.process.properties import Properties
from ..steps import SetCapabilityProperties
from ..constants import CAPABILITY_PROP_FMT


class TestSetCapabilityProperties(unittest.TestCase):

    def setUp(self):
        self.step = SetCapabilityProperties(
            'zecap',
            capability_version_prop='zecap_version')

        def fakelog(*a):
            self.log = a
        self.step.addCompleteLog = fakelog
        # step.build is necessary only to be adapted to IProperties.
        # For testing, let's just provide IProperties directly
        self.step.build = Properties()

        self.step_status = None

        def finished(status):
            self.step_status = status
        self.step.finished = finished

    def test_description(self):
        step = SetCapabilityProperties('somecap',
                                       description='abc',
                                       descriptionDone=u'def',
                                       descriptionSuffix='ghi')
        self.assertEqual(step.description, ['abc'])
        self.assertEqual(step.descriptionDone, [u'def'])
        self.assertEqual(step.descriptionSuffix, ['ghi'])

    def test_one_avail_version(self):
        step = self.step
        step.setProperty('capability',
                         dict(zecap={'1.0': dict(bin='/usr/bin/zecap'),
                                     },
                              ), 'BuildSlave')
        step.start()
        self.assertEqual(self.step_status, SUCCESS)
        self.assertEqual(
            step.getProperty(CAPABILITY_PROP_FMT % ('zecap', 'bin')),
            '/usr/bin/zecap')

    def test_no_details(self):
        step = self.step
        step.setProperty('capability', dict(zecap={}), 'BuildSlave')
        step.start()
        self.assertEqual(self.step_status, SUCCESS)

    def test_requirement_other_cap(self):
        step = self.step
        step.setProperty('capability',
                         dict(zecap={'1.0': dict(bin='/usr/bin/zecap')},
                              othercap={'1.0': dict(bin='other')}),
                         'BuildSlave')
        step.setProperty('build_requires', ["othercap < 2"])
        step.start()
        self.assertEqual(self.step_status, SUCCESS)
        self.assertEqual(
            step.getProperty(CAPABILITY_PROP_FMT % ('zecap', 'bin')),
            '/usr/bin/zecap')

    def test_one_dispatched_version(self):
        step = self.step
        step.setProperty('capability',
                         dict(zecap={'1.0': dict(bin='/usr/bin/zecap1'),
                                     '2.0': dict(bin='/usr/bin/zecap2'),
                                     },
                              ), 'BuildSlave')
        step.setProperty('zecap_version', '2.0')
        step.start()
        self.assertEqual(self.step_status, SUCCESS)
        self.assertEqual(
            step.getProperty(CAPABILITY_PROP_FMT % ('zecap', 'bin')),
            '/usr/bin/zecap2')

    def test_one_meeting_requirements(self):
        step = self.step
        step.setProperty('capability',
                         dict(zecap={'1.0': dict(bin='/usr/bin/zecap1'),
                                     '2.0': dict(bin='/usr/bin/zecap2'),
                                     },
                              ), 'BuildSlave')
        step.setProperty('build_requires', ["zecap < 2"])
        step.start()
        self.assertEqual(self.step_status, SUCCESS)
        self.assertEqual(
            step.getProperty(CAPABILITY_PROP_FMT % ('zecap', 'bin')),
            '/usr/bin/zecap1')

    def test_several_meeting_requirements(self):
        step = self.step
        step.setProperty('capability',
                         dict(zecap={'1.0': dict(bin='/usr/bin/zecap1'),
                                     '2.0': dict(bin='/usr/bin/zecap2'),
                                     },
                              ), 'BuildSlave')
        step.setProperty('build_requires', ["zecap"])
        step.start()
        self.assertEqual(self.step_status, SUCCESS)
        prop_val = step.getProperty(CAPABILITY_PROP_FMT % ('zecap', 'bin'))
        self.assertTrue(prop_val in ('/usr/bin/zecap1', '/usr/bin/zecap2'))
