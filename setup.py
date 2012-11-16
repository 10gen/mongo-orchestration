try:
    from setuptools import setup
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

import sys

if not sys.platform.startswith('java'):
    if sys.version_info < (2, 7):
        requiredPacks = ['nose-testconfig==0.6', 'simplejson==2.1.0', 'multiprocessing==2.6.2.1', 'unittest2']
    elif sys.version_info >= (3,):
        requiredPacks = ['nose-testconfig==0.9']
    else:
        requiredPacks = ['nose-testconfig==0.8']
else:
    requiredPacks = ['nose-testconfig==0.6', 'simplejson==2.1.0', 'unittest2']

setup(
    name='pymongo-orchestration',
    version='0.1',
    author='Mikhail Mamrouski',
    author_email='mmamrouski@gmail.com',
    setup_requires=[
        'pymongo>=2.3',
        'nose-benchmark>=0.9',
    ] + requiredPacks,
    dependency_links=[
        'http://github.com/mongodb/mongo-python-driver/tarball/master#egg=pymongo-2.3rc1',
        'http://github.com/MblKiTA/nose-benchmark/tarball/master#egg=nose-benchmark-0.9',
        'http://github.com/MblKiTA/nose-testconfig/tarball/master#egg=nose-testconfig-0.9'
    ]
)
