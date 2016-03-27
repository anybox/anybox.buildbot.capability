from setuptools import setup, find_packages

version = '0.1'
pkg_name = "anybox.buildbot.capability"

setup(
    name=pkg_name,
    version=version,
    author="Anybox SAS",
    author_email="gracinet@anybox.fr",
    description="Static capability system for buildbot",
    license="GPLv2+",
    long_description=open('README.rst').read(),
    url="http://pypi.python.org/pypi/anybox.buildbot.odoo",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    namespace_packages=['anybox', 'anybox.buildbot'],
    install_requires=['buildbot >= 0.9.0b1',
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
    entry_points="""
    [console_scripts]
    """
)
