"""
    `classifiers.py`

    This module implements the classifiers to be used in the pipeline.
"""

# classifiers
import numpy as np
from sklearn import svm
from sklearn.preprocessing import scale
from pyborist import PyboristClassifier
from sklearn.preprocessing import StandardScaler
from onionpop.features import Features


class ClassifierInterface(object):

    _clf = None

    def predict(self, features):
        feature_vector = self.extract_features(features)
        return self.predict_with_confidence(feature_vector)

    def extract_features(self, features):
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
        self.scaler = StandardScaler()
        self._clf = svm.OneClassSVM(**params)
        super(OneClassCUMUL, self).__init__()

    def extract_features(self, features):
        return features.extract_webfp_features()

    def train(self, features, labels):
        """One-class learning: ignores features."""
        features = self.scaler.fit_transform(features)
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
        fv = np.asarray(feature_vector)
        fv = fv.reshape(1, -1) # we have a single sample
        fv = self.scaler.transform(fv)
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

    def extract_features(self, features):
        return features.extract_position_features()

    def predict_with_confidence(self, feature_vector):
        fv = np.asarray(feature_vector)
        fv = fv.reshape(1, -1) # we have a single sample
        fv = fv.astype(np.float)

        prediction = self._clf.predict(fv)

        is_cgm_pos = True if np.asscalar(prediction) == 1 else False
        confidence = 1.0 # TODO this needs updating, but its not currently used by PrivCount

        return (is_cgm_pos, confidence)


class PurposeClassifier(ClassifierInterface):
    def __init__(self, *args, **params):
        self._clf = PyboristClassifier(**params)
        super(PurposeClassifier, self).__init__()

    def extract_features(self, features):
        return features.extract_purpose_features()

    def predict_with_confidence(self, feature_vector):
        fv = np.asarray(feature_vector)
        fv = fv.reshape(1, -1) # we have a single sample
        fv = fv.astype(np.float)

        prediction = self._clf.predict(fv)

        is_rend_purp = True if np.asscalar(prediction) == 1 else False
        confidence = 1.0 # TODO this needs updating, but its not currently used by PrivCount

        return (is_rend_purp, confidence)
