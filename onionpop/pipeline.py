#!/usr/bin/env python
"""
    `pipeline.py`

    Implements an API to middle-earth classifiers that infer properties about
    Tor circuits. This API can be exposed to PrivCount in order to gather
    statistics on live circuits. In particular, we use it to collect statistics
    about HS popularity (Facebook vs all).

    As an API, this module is supposed to be imported for use in other modules.
    However, it comes with some tools and a command line interface that can be
    used to train a model to be used by the API.

    To run this script to train the model do:

        ./pipeline.py train config.ini

    The configuration file specified the classifiers in the model. See the
    example in `config.ini` for more instructions.

        ./pipeline.py train -o model.dump config.ini

    will train and dump the model into a file for later use.

    To show the API usage example run:

        ./pipeline.py usage

    For more information run:

        ./pipeline.py --help
        ./pipeline.py train --help
        ./pipeline.py compose model1 model2 new_model

"""
import sys
import json
import dill as pickle
import logging
import argparse
import pandas as pd
import numpy as np
import multiprocessing as mp

from os.path import join, abspath, dirname, pardir, splitext

from sklearn.datasets import load_svmlight_file

import onionpop.classifiers
from onionpop.features import Features, test_circuit

# Global and defaults
NUM_PROCS = int(mp.cpu_count())

# Paths
BASE_DIR = abspath(join(dirname(__file__), pardir))
TEST_DIR = join(BASE_DIR, 'test')
DATA_DIR = join(TEST_DIR, 'data')


def _usage_example():
    """Examples on how to use the API."""

    # instantiate middle earth detector
    model = MiddleEarthModel.load('webfp_fb.model')

    # if circuit is *not* Facebook HS with high confidence:
    features = Features(test_circuit)
    prediction, confidence = model.predict(features)
    assert prediction == False and confidence > 0.5

    log.info("Is the circuit a FB circuit? %s" % prediction)
    log.info("(Confidence (distance to Support Vector) is: %s" % confidence)


def _usage_example_separate_models():
    """Example on how to use the API with single models."""

    # Note that in this case you need to train the models separately
    position_model = MiddleEarthModel.load(join(DATA_DIR, 'position.model'))
    circuit_model = MiddleEarthModel.load(join(DATA_DIR, 'circuit.model'))
    website_model = MiddleEarthModel.load(join(DATA_DIR, 'website.model'))

    features = Features(test_circuit)

    is_mid_pos, mid_confidence =  position_model.predict(features)
    is_hs, hs_confidence = purpose_model.predict(features)
    is_fb, fb_confidence = website_model.predict(features)

    assert all(is_mid_pos, is_hs, is_fb)


def load_data(fpath, sel_feats=None, lab_feat=None):
    """Loads the dataset in LIBSVM format."""
    _, ext = splitext(fpath)
    if ext == '.libsvm' or ext == '.svm':
        return load_svmlight_file(fpath)

    elif ext == '.csv':
        data = pd.read_csv(fpath)
        if sel_feats is not None:
            data = data[sel_feats]
        return data[lab_feat], data[[c for c in data.columns if c != lab_feat]]

    else:
        raise Exception("Unrecognized extension: {}".format(ext))


class Model(object):
    """This class implements a model passed to the API."""

    _clf = None

    def __init__(self, config):
        #log.info("New model: {classifier} with data {dataset}. Params = {params}".format(**config))

        # define path to dataset
        self.data_path = config['dataset']

        # instantiate the classifier
        self._clf = getattr(onionpop.classifiers, config['classifier'])(**config['params'])

    def dump(self, fpath):
        """Dump the model to a file for later use.

        Parameters
        ----------
        fpath : str
            Path to file where model will be dumped.
        """
        with open(fpath, 'wb') as fo:
            pickle.dump(self, fo)

    def predict(self, features):
        if self._clf is None:
            raise Exception("The model has not been trained.")
        return self._clf.predict(features)

    def train(self):
        """Train the model."""
        X, y = load_data(self.data_path)
        X = np.asarray(X.todense())
        self._clf.train(X, y)


class MiddleEarthModel(Model):
    """This class implements a composite model for the pipeline.

    We use the composite pattern so that we abstract from the fact that there
    are several underlying models in the classification. The API only exposes
    one single set of methods for the model so that the model can be managed
    (load, dump) in a more simple manner.
    """
    _models = None

    def __init__(self):
        self._models = []

    def add(self, model):
        """Add a model to the composite."""
        self._models.append(model)

    def pop(self):
        """Return last model in the list."""
        return self._models.pop()

    @staticmethod
    def load(fpath):
        """Load an already-trained model.

        Parameters
        ----------
        fpath : str
            Path to file where model has been dumped.
        """
        with open(fpath, 'rb') as fi:
            return pickle.load(fi)

    @classmethod
    def train(cls, config_file):
        """Return a model trained as specified in the config file.

        """
        comp_model = cls()

        # compose models as specified in the config:
        for line in open(config_file):
            if line.strip().startswith('#') or not line.strip():
                continue
            comp_model.add(Model(json.loads(line.strip())))

        # train models
        map(lambda m: m.train(), comp_model._models)

        return comp_model

    def predict(self, features):
        """Return prediction results for the composite model.

        Run in this order:
            1. Purpose detector: is it a HS circuit?
            2. Position detector: are we the next-to-guard middle?
            3. Website detector: is it a visit to Facebook's HS?

        Output
        ------
            prediction, confidence : tup (bool, float)
                - `prediction` indicates whether the hidden service is Facebook
                or not.
                - `confidence` is the probability that prediction is true
                according to the classifier's estimation.
        """
        overall_confidence = 1.0

        for model in self._models:
            is_detected, confidence = model.predict(features)

            if not is_detected:  # early stop
                return False, overall_confidence

            overall_confidence *= confidence  # error accumulates

        return True, overall_confidence


def main():
    parser = get_parser()
    args = parser.parse_args()

    # logging config
    config_logger(args)

    log.info("Will perform the following action: {}".format(args.action))
    if args.action == 'usage':
        # log debug for usage examples
        _usage_example()

    elif args.action == 'compose':
        new_model = MiddleEarthModel()

        if len(args.models) < 2:
            raise Exception('Not enough models try --h for help.')

        for model_path in args.models[:-1]:
            new_model.add(MiddleEarthModel.load(model_path).pop())

        new_model.dump(args.models[-1])

    elif args.action == 'train':
        # train the model
        model = MiddleEarthModel.train(args.configfile)

        # dump model?
        if args.output:
            model.dump(args.output)


def get_parser():
    """
        Example:

            ./pipeline.py train config.ini -o model.dump
    """
    parser = argparse.ArgumentParser(description="Tools for the classification pipeline.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--log',
                        type=str,
                        dest="log",
                        metavar='<log path>',
                        default='stdout',
                        help='path to the log file. It will print to stdout by default.')

    parser.add_argument('--log-level',
                        type=str,
                        dest="loglevel",
                        metavar='<log level>',
                        choices=[l for l in logging._levelNames if type(l) is str],
                        default=logging.getLevelName(logging.INFO),
                        help='logging verbosity level.')

    subparsers = parser.add_subparsers(dest='action', help="Pipeline action.")
    usage_parser = subparsers.add_parser('usage', help="Demonstrage usage of API.")
    train_parser = subparsers.add_parser('train', help="Train the classification pipeline")

    train_parser.add_argument('configfile',
                              type=str,
                              metavar='<config file>',
                              help='configuration file that specifies the pipeline.')

    train_parser.add_argument('-o', '--output',
                              type=str,
                              metavar='output file',
                              help='path where model should be dumped.')
    comps_parser = subparsers.add_parser('compose', help="Compose multiple models into one single model.")
    comps_parser.add_argument('models',
                              nargs='+',
                              metavar='<model1> <model2> <new model>',
                              help='configuration file that specifies the pipeline.')

    return parser


def config_logger(args):
    LOG_FORMAT = "%(asctime)s %(filename)-12s %(levelname)-8s %(message)s"

    global log
    log = logging.getLogger()

    # Set file
    log_file = sys.stdout
    if args.log != 'stdout':
        log_file = open(args.log, 'w')
    ch = logging.StreamHandler(log_file)

    # Set logging format
    ch.setFormatter(logging.Formatter(LOG_FORMAT))
    log.addHandler(ch)

    # Set level format
    log.setLevel(logging._levelNames[args.loglevel])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
