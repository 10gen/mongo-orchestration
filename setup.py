#!/usr/bin/python

import os
import sys

extra_opts = {'test_suite': 'tests'}
extra_deps = []
extra_test_deps = []
if sys.version_info[:2] == (2, 6):
    extra_deps.append('argparse')
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


setup(
    name='mongo-orchestration',
    version='0.2',
    author='MongoDB, Inc.',
    author_email='mongodb-user@googlegroups.com',
    description='Restful service for managing MongoDB servers',
    keywords=['mongo-orchestration', 'mongodb', 'mongo', 'rest', 'testing'],
    license="http://www.apache.org/licenses/LICENSE-2.0.html",
    platforms=['any'],
    url='https://github.com/10gen/mongo-orchestration',
    install_requires=['pymongo>=2.8',
                      'bottle>=0.12.7',
                      'CherryPy>=3.5.0'] + extra_deps,
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
    **extra_opts
)
