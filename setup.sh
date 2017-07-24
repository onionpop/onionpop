#!/bin/bash

# install pipeline requirements
pip install -r requirements.txt

# install Arborist (Random Forest API)
git clone git@github.com:mjuarezm/Arborist.git
cd Arborist/ArboristBridgePy/
pip install -r requirements.txt  # Arborist requirements
python setup.py install
