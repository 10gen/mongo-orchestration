#!/usr/bin/python

import os
import sys

from distutils.cmd import Command
from distutils.errors import DistutilsOptionError

extra_opts = {'test_suite': 'tests'}
extra_deps = []
extra_test_deps = []
if sys.version_info[:2] == (2, 6):
    extra_deps.append('argparse')
    extra_deps.append('simplejson')
    extra_test_deps.append('unittest2')
    extra_opts['test_suite'] = 'unittest2.collector'

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

try:
    with open('README.rst', 'r') as fd:
        extra_opts['long_description'] = fd.read()
except IOError:
    pass        # Install without README.rst


class test(Command):
    description = "run the tests"

    user_options = [
        ("test-module=", "m", "Discover tests in specified module"),
        ("test-suite=", "s",
         "Test suite to run (e.g. 'some_module.test_suite')"),
        ("failfast", "f", "Stop running tests on first failure or error")
    ]

    def initialize_options(self):
        self.test_module = None
        self.test_suite = None
        self.failfast = False

    def finalize_options(self):
        if self.test_suite is None and self.test_module is None:
            self.test_module = 'tests'
        elif self.test_module is not None and self.test_suite is not None:
            raise DistutilsOptionError(
                "You may specify a module or suite, but not both"
            )

    def run(self):
        # Installing required packages and running egg_info and are
        # part of normal operation for setuptools.command.test.test
        if self.distribution.install_requires:
            self.distribution.fetch_build_eggs(
                self.distribution.install_requires)
        if self.distribution.tests_require:
            self.distribution.fetch_build_eggs(self.distribution.tests_require)
        self.run_command('egg_info')

        # Construct a TextTestRunner directly from the unittest imported from
        # test (this will be unittest2 under Python 2.6), which creates a
        # TestResult that supports the 'addSkip' method. setuptools will by
        # default create a TextTestRunner that uses the old TestResult class,
        # resulting in DeprecationWarnings instead of skipping tests under 2.6.
        from tests import unittest
        if self.test_suite is None:
            all_tests = unittest.defaultTestLoader.discover(self.test_module)
            suite = unittest.TestSuite(tests=all_tests)
        else:
            suite = unittest.defaultTestLoader.loadTestsFromName(
                self.test_suite)
        result = unittest.TextTestRunner(verbosity=2,
                                         failfast=self.failfast).run(suite)
        sys.exit(not result.wasSuccessful())


setup(
    name='mongo-orchestration',
    version='0.6.7',
    author='MongoDB, Inc.',
    author_email='mongodb-user@googlegroups.com',
    description='Restful service for managing MongoDB servers',
    keywords=['mongo-orchestration', 'mongodb', 'mongo', 'rest', 'testing'],
    license="http://www.apache.org/licenses/LICENSE-2.0.html",
    platforms=['any'],
    url='https://github.com/10gen/mongo-orchestration',
    install_requires=['pymongo>=3.0.2',
                      'bottle>=0.12.7',
                      'CherryPy>=3.5.0,<7.1'] + extra_deps,
    tests_require=['coverage>=3.5'] + extra_test_deps,
    packages=find_packages(exclude=('tests',)),
    package_data={
        'mongo_orchestration': [
            os.path.join('configurations', config_dir, '*.json')
            for config_dir in ('servers', 'replica_sets', 'sharded_clusters')
        ] + [os.path.join('lib', 'client.pem')]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: Implementation :: CPython"
    ],
    entry_points={
        'console_scripts': [
            'mongo-orchestration = mongo_orchestration.server:main'
        ]
    },
    cmdclass={'test': test},
    **extra_opts
)
