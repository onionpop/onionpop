"""
    `classifiers.py`

    This module implements the classifiers to be used in the pipeline.
"""

# classifiers
import numpy as np
import cumul, kfp
from sklearn import svm
from sklearn.preprocessing import scale
from pyborist import PyboristClassifier
from features import Features


class ClassifierInterface(object):

    _clf = None

    def predict(self, circuit):
        feature_vector = self.extract_features(circuit)
        return self.predict_with_confidence(feature_vector)

    def extract_features(self, circuit):
        """Template method that must be implemented in each specific
        classifier.
        """
        pass

    def train(self, features, labels):
        """Train the model.

        Parameters
        ----------
        features :
            Feature set used to train the model.
        labels :
            Ground truth for the `features`.
        """
        self._clf.fit(features, labels)


class OneClassCUMUL(ClassifierInterface):
    def __init__(self, *args, **params):
        self._clf = svm.OneClassSVM(**params)
        super(OneClassCUMUL, self).__init__()

    def extract_features(self, circuit):
        cells = Features(circuit).get_cell_sequence()
        return cumul.extract(cells)

    def train(self, features, labels):
        self._clf.fit(features)

    def predict_with_confidence(self, feature_vector):
        '''
        Instead of a probability, the confidence is measured as the distance
        of the test sample to the Support Vector:
            http://scikit-learn.org/stable/modules/generated/sklearn.svm.OneClassSVM.html#sklearn.svm.OneClassSVM.decision_function

        There is no way to get the probabilities using the one-class
        classifier. See:

            http://scikit-learn-general.narkive.com/zcMWz5LV/one-class-svm-probability
            https://stackoverflow.com/questions/15111408/how-does-sklearn-svm-svcs-function-predict-proba-work-internally

        '''
        fv = scale(feature_vector)
        sv_dist = np.asscalar(self._clf.decision_function(fv))
        prediction = np.asscalar(self._clf.predict(fv))
        is_fb = False
        if prediction == 1:
            is_fb = True
        return (is_fb, sv_dist)


class PositionClassifier(ClassifierInterface):
    def __init__(self, *args, **params):
        self._clf = PyboristClassifier(**params)
        super(PositionClassifier, self).__init__()

    def extract_features(self, circuit):
        return Features(circuit).extract_position_features()


class CircuitClassifier(ClassifierInterface):
    def __init__(self, *args, **params):
        self._clf = PyboristClassifier(**params)
        super(CircuitClassifier, self).__init__()

    def extract_features(self, circuit):
        return Features(circuit).extract_purpose_features()
