#!/usr/bin/python

import os
import sys

extra_deps = []
extra_test_deps = []
if sys.version_info[:2] == (2, 6):
    extra_deps.append('argparse')
    extra_test_deps.append('unittest2')

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

extra_opts = {}
try:
    with open('README.rst', 'r') as fd:
        extra_opts['long_description'] = fd.read()
except IOError:
    pass        # Install without README.rst


setup(
    name='mongo-orchestration',
    version='0.1',
    author='MongoDB, Inc.',
    author_email='mongodb-user@googlegroups.com',
    description='Restful service for managing MongoDB servers',
    keywords=['mongo-orchestration', 'mongodb', 'mongo', 'rest', 'testing'],
    license="http://www.apache.org/licenses/LICENSE-2.0.html",
    platforms=['any'],
    url='https://github.com/mongodb/mongo-orchestration',
    install_requires=['pymongo>=2.7.2',
                      'bottle>=0.12.7',
                      'CherryPy>=3.5.0'] + extra_deps,
    tests_require=['nose>=1.2', 'coverage>=3.5'] + extra_test_deps,
    test_suite='nose.collector',
    packages=find_packages(),
    package_data={
        'mongo_orchestration': [
            os.path.join('configurations', config_dir, '*.json')
            for config_dir in ('servers', 'replica_sets', 'sharded_clusters')]
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
    **extra_opts
)
