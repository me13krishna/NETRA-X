"""
calibration.py — Isotonic Regression & Sigmoid Posterior Probability Calibrator.

Maps raw/capped Log-Likelihood Ratio (LLR) scores to calibrated posterior probabilities P(H_1 | E) in [0, 1].
"""

import math
import numpy as np
from typing import List, Union, Optional
from sklearn.isotonic import IsotonicRegression


def sigmoid_llr_to_prob(llr: float, prior_odds_log: float = -2.0) -> float:
    """
    Standard Bayesian log-odds to probability conversion:
    P(H_1 | E) = 1 / (1 + exp(-(LLR + prior_odds_log)))
    """
    try:
        val = llr + prior_odds_log
        # Clip val to prevent overflow
        val_clipped = max(-50.0, min(50.0, val))
        return 1.0 / (1.0 + math.exp(-val_clipped))
    except OverflowError:
        return 1.0 if llr > 0 else 0.0


class IsotonicCalibrator:
    """
    Isotonic regression probability calibrator for LLR scores.
    """

    def __init__(self, prior_odds_log: float = -2.0):
        self.prior_odds_log = prior_odds_log
        self.iso_reg: Optional[IsotonicRegression] = None
        self.is_fitted: bool = False

    def fit(self, llr_scores: List[float], labels: List[int]) -> "IsotonicCalibrator":
        """
        Fit Isotonic Regression model on LLR scores and binary ground truth labels (0 or 1).
        """
        if len(llr_scores) < 5:
            # Not enough samples to fit monotonic curve reliably
            self.is_fitted = False
            return self

        X = np.array(llr_scores, dtype=np.float64)
        y = np.array(labels, dtype=np.float64)

        # Fit isotonic regression with clipping to [0, 1]
        self.iso_reg = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.iso_reg.fit(X, y)
        self.is_fitted = True
        return self

    def predict_proba(self, llr_score: float) -> float:
        """
        Predict calibrated posterior probability P(H_1 | E) in [0, 1].
        """
        if self.is_fitted and self.iso_reg is not None:
            proba = float(self.iso_reg.predict([llr_score])[0])
            # Ensure probability bounds
            return max(0.0, min(1.0, proba))
        else:
            # Fallback to sigmoid transformation
            return sigmoid_llr_to_prob(llr_score, self.prior_odds_log)
