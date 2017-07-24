# onionpop

A PrivCount module to gather HS stats. It implements the circuit, position, and website fingerprinting pipeline.

## setup

### setup or activate your PrivCount virtual environment

```
pip install virtualenv
virtualenv venv
source venv/bin/activate
```

### install Arborist (Random Forest API required by onionpop)

```
git clone https://github.com/onionpop/Arborist
cd Arborist/ArboristBridgePy/
pip install -r requirements.txt
python setup.py install
cd -
```

### install onionpop

```
git clone git@github.com:robgjansen/onionpop.git
cd onionpop
pip install -r requirements.txt
```
