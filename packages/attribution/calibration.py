"""
Isotonic Calibration & Confidence Tier Assignment Module
Maps raw Log-Likelihood Ratio (LLR) scores to empirical posterior probabilities P(H1 | E) in [0, 1].
"""

import math
from typing import List, Tuple
import numpy as np

try:
    from sklearn.isotonic import IsotonicRegression
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class IsotonicCalibrator:
    """Wrapper for Isotonic Regression calibration on LLR scores."""

    def __init__(self):
        self.is_fitted = False
        if HAS_SKLEARN:
            self.model = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        else:
            self.model = None

    def fit(self, raw_llrs: List[float], labels: List[int]):
        """Fit isotonic model on ground truth synthetic benchmark labels."""
        if not raw_llrs or not labels:
            return self
        
        X = np.array(raw_llrs, dtype=float)
        y = np.array(labels, dtype=float)

        if HAS_SKLEARN:
            self.model.fit(X, y)
            self.is_fitted = True
        return self

    def predict_proba(self, raw_llr: float) -> float:
        """Predict calibrated probability for a raw LLR score."""
        if self.is_fitted and HAS_SKLEARN:
            pred = float(self.model.predict([raw_llr])[0])
            return round(max(0.0, min(1.0, pred)), 4)
        
        # Sigmoid fallback calibration if not fitted or sklearn missing
        return calibrate_probability(raw_llr)


def calibrate_probability(raw_llr: float, beta0: float = -0.5, beta1: float = 0.35) -> float:
    """Parametric Sigmoid calibration fallback mapping LLR -> P(H1 | E)."""
    exponent = -(beta0 + beta1 * raw_llr)
    exponent = max(-50.0, min(50.0, exponent))
    prob = 1.0 / (1.0 + math.exp(exponent))
    return round(prob, 4)


def determine_confidence_tier(prob: float) -> str:
    """Map calibrated probability to NETRA-X decision tier."""
    if prob >= 0.85:
        return "High Confidence"
    elif prob >= 0.60:
        return "Medium Confidence"
    elif prob >= 0.35:
        return "Low Confidence"
    else:
        return "Insufficient Evidence"
