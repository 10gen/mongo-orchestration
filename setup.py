#!/usr/bin/python

try:
    from setuptools import setup
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup  # NOQA

import sys

if not sys.platform.startswith('java'):
    if sys.version_info < (2, 7):
        REQUIRED_PACKS = ['nose-testconfig==0.6', 'simplejson==2.1.0', 'multiprocessing==2.6.2.1', 'unittest2']
    elif sys.version_info >= (3,):
        REQUIRED_PACKS = ['nose-testconfig==0.9']
    else:
        REQUIRED_PACKS = ['nose-testconfig==0.8']
else:
    REQUIRED_PACKS = ['nose-testconfig==0.6', 'simplejson==2.1.0', 'unittest2']

setup(
    name='pymongo-orchestration',
    version='0.1',
    author='Mikhail Mamrouski',
    author_email='mmamrouski@gmail.com',
    setup_requires=[
        'pymongo>=2.5.2',
        'nose>=1.2'
    ] + REQUIRED_PACKS
)
