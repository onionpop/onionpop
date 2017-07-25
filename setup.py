#!/usr/bin/env python

from distutils.core import setup

setup(
    name="onionpop",
    version=1.0,
    description=("onionpop API to gather statistics in PrivCount."),
    url='https://github.com/onionpop',
    author="mjuarezm",
    author_email="marc.juarez@kuleuven.be",
    keywords=['tor', 'privacy', 'measurements', 'website fingerprinting'],
    packages=['onionpop'],
    #setup_requires=['numpy', 'scipy'],
    #install_requires=[
    #    'numpy',
    #    'scipy',
    #    'pandas',
    #    'dill',
	#	'cython>=0.24',
    #    'scikit-learn',
    #]
)
