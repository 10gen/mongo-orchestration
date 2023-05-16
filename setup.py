#!/usr/bin/python

import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

try:
    with open('README.rst', 'r') as fd:
        long_description = fd.read()
except IOError:
        long_description = ''


version_ns = {}
with open("mongo_orchestration/_version.py") as fp:
    exec(fp.read(), version_ns)
version = version_ns["__version__"]

setup(
    name='mongo-orchestration',
    version=version,
    author='MongoDB, Inc.',
    author_email='mongodb-user@googlegroups.com',
    description='Restful service for managing MongoDB servers',
    long_description=long_description,
    keywords=['mongo-orchestration', 'mongodb', 'mongo', 'rest', 'testing'],
    license="http://www.apache.org/licenses/LICENSE-2.0.html",
    platforms=['any'],
    url='https://github.com/10gen/mongo-orchestration',
    install_requires=['pymongo>=4,<5',
                      'bottle>=0.12.7',
                      'cheroot>=5.11',
                      'requests'],
    python_requires=">=3.6",
    extras_require=dict(
        test=['coverage>=3.5', 'pytest', 'pexpect'],
    ),
    packages=find_packages(exclude=('tests',)),
    package_data={
        'mongo_orchestration': [
            os.path.join('configurations', config_dir, '*.json')
            for config_dir in ('servers', 'replica_sets', 'sharded_clusters')
        ] + [os.path.join('lib', '*.pem')]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython"
    ],
    entry_points={
        'console_scripts': [
            'mongo-orchestration = mongo_orchestration.server:main',
            'mongo-launch = mongo_orchestration.launch:main'
        ]
    }
)
