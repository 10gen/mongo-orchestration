#!/usr/bin/python

try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup  # NOQA

setup(
    name='pymongo-orchestration',
    version='0.1',
    author='Mikhail Mamrouski',
    author_email='mmamrouski@gmail.com',
    install_requires=('pymongo>=2.7.2', 'bottle>=0.12.7', 'requests>=1.1'),
    tests_require=('nose>=1.2', 'coverage>=3.5'),
    test_suite='nose.collector'
)
