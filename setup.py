#!/usr/bin/env python

from setuptools import setup

setup(
    name="onionpop",
    author="mjuarezm",
    author_email="marc.juarez@kuleuven.be",
    description=("onionpop API to gather statistics in PrivCount."),
    keywords=['tor', 'privacy', 'measurements', 'website fingerprinting'],
    version=1.0,
    packages=['onionpop'],
    setup_requires=['numpy', 'scipy'],
    install_requires=[
        'numpy',
        'scipy',
        'pandas',
        'dill',
		'cython>=0.24',
        'scikit-learn',
    ]
)
