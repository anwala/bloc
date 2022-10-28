#!/usr/bin/env python

from setuptools import setup, find_packages

desc = """Behavioral Language for Online Classification (BLOC): A General Language for Modeling Social Media Account Behavior."""

__appversion__ = None

#__appversion__, defined here
exec(open('bloc/version.py').read())


setup(
    name='twitterbloc',
    version=__appversion__,
    description=desc,
    long_description='See: https://github.com/anwala/bloc',
    author='Alexander C. Nwala',
    author_email='acnwala@wm.edu',
    url='https://github.com/anwala/bloc',
    packages=find_packages(),
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    package_data={
        'bloc': [
            './symbols.json'
        ]
    },
    install_requires=[
        'numpy',
        'osometweet',
        'requests-oauthlib',
        'sklearn',
        'textblob'
    ],
    scripts=[
        'bin/bloc'
    ]
)
