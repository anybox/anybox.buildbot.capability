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

from setuptools import setup, find_packages

version = '0.1'
pkg_name = "anybox.buildbot.capability"


def steps_ep(step_names):
    return ["%s = anybox.buildbot.capability.steps:%s" % (name, name)
            for name in step_names]

setup(
    name=pkg_name,
    version=version,
    author="Anybox SAS",
    author_email="gracinet@anybox.fr",
    description="Static capability system for buildbot",
    license="GPLv2+",
    long_description=open('README.rst').read(),
    url="http://pypi.python.org/pypi/anybox.buildbot.capability",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    namespace_packages=['anybox', 'anybox.buildbot'],
    install_requires=['buildbot',
                      ],
    tests_require=['nose'],
    test_suite='nose.collector',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License v2 '
        'or later (GPLv2+)',
    ],
    entry_points={
        'buildbot.steps': steps_ep(('SetCapabilityProperties', ))
    }
)
