#!/usr/bin/env python

from setuptools import setup, find_packages

desc = """Behavioral Language for Online Classification (BLOC): A general language for modeling the behavior of social media users."""

__appversion__ = None

#__appversion__, defined here
exec(open('bloc/version.py').read())


setup(
    name='bloc',
    version=__appversion__,
    description=desc,
    long_description='See: https://github.iu.edu/anwala/bloc',
    author='Alexander C. Nwala',
    author_email='anwala@iu.edu',
    url='https://github.iu.edu/anwala/bloc',
    packages=find_packages(),
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
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
