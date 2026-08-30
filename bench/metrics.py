"""
metrics.py — Quantitative evaluation metrics for NETRA-X Attribution Engine.

Calculates:
- Brier Score
- Expected Calibration Error (ECE)
- False-Attribution Rate (FAR)
- Recall@10
- Stylometry Short-Text Abstention Rate
"""

import numpy as np
from typing import List, Dict, Any, Tuple


def calculate_brier_score(posterior_probabilities: List[float], ground_truths: List[int]) -> float:
    """
    Brier Score = (1 / N) * sum((P_i - y_i)^2)
    Lower is better.
    """
    probs = np.array(posterior_probabilities, dtype=np.float64)
    targets = np.array(ground_truths, dtype=np.float64)
    if len(probs) == 0:
        return 0.0
    return float(np.mean((probs - targets) ** 2))


def calculate_expected_calibration_error(
    posterior_probabilities: List[float],
    ground_truths: List[int],
    n_bins: int = 10,
) -> float:
    """
    Expected Calibration Error (ECE):
    Bins predictions into n_bins, computes weighted average of |acc(b) - conf(b)|.
    Target: ECE < 0.15.
    """
    probs = np.array(posterior_probabilities, dtype=np.float64)
    targets = np.array(ground_truths, dtype=np.float64)

    if len(probs) == 0:
        return 0.0

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(probs)

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        # Samples in this bin
        if i == n_bins - 1:
            in_bin = (probs >= bin_lower) & (probs <= bin_upper)
        else:
            in_bin = (probs >= bin_lower) & (probs < bin_upper)

        bin_size = np.sum(in_bin)
        if bin_size > 0:
            bin_acc = np.mean(targets[in_bin])
            bin_conf = np.mean(probs[in_bin])
            ece += (bin_size / n) * abs(bin_acc - bin_conf)

    return float(ece)


def calculate_false_attribution_rate(
    decisions: List[str], ground_truths: List[int]
) -> float:
    """
    False-Attribution Rate (FAR):
    Ratio of ground truth non-matches (y=0) incorrectly attributed as HIGH_CONFIDENCE_LINK.
    Target: 0.0%
    """
    false_positives = 0
    total_negatives = 0

    for dec, gt in zip(decisions, ground_truths):
        if gt == 0:
            total_negatives += 1
            if dec == "HIGH_CONFIDENCE_LINK":
                false_positives += 1

    if total_negatives == 0:
        return 0.0
    return (false_positives / total_negatives) * 100.0


def calculate_recall_at_k(
    probabilities: List[float], ground_truths: List[int], k: int = 10
) -> float:
    """
    Recall@K: Ratio of ground-truth positive cases (y=1) retrieved in top-K predictions.
    Target: 100.0%
    """
    if not probabilities or not ground_truths or len(probabilities) != len(ground_truths):
        return 0.0

    total_positives = sum(1 for gt in ground_truths if gt == 1)
    if total_positives == 0:
        return 100.0

    # Cap denominator at min(k, total_positives) for top-K slot capacity
    k_effective = min(k, total_positives)

    paired = sorted(zip(probabilities, ground_truths), key=lambda x: x[0], reverse=True)
    top_k_pairs = paired[:k]

    positives_retrieved = sum(1 for p, gt in top_k_pairs if gt == 1)
    return (positives_retrieved / k_effective) * 100.0



def calculate_roc_auc(
    probabilities: List[float], ground_truths: List[int]
) -> float:
    """
    ROC-AUC Score: Area under Receiver Operating Characteristic curve.
    Target: > 0.90
    """
    if len(set(ground_truths)) < 2:
        return 1.0 if any(gt == 1 for gt in ground_truths) else 0.5

    try:
        from sklearn.metrics import roc_auc_score
        return float(roc_auc_score(ground_truths, probabilities))
    except Exception:
        probs = np.array(probabilities, dtype=np.float64)
        targets = np.array(ground_truths, dtype=np.int32)
        pos_scores = probs[targets == 1]
        neg_scores = probs[targets == 0]
        if len(pos_scores) == 0 or len(neg_scores) == 0:
            return 1.0

        num_pairs = len(pos_scores) * len(neg_scores)
        concordant = sum(
            (1.0 if p > n else 0.5 if p == n else 0.0)
            for p in pos_scores
            for n in neg_scores
        )
        return float(concordant / num_pairs)


def calculate_evaluation_report(
    probabilities: List[float],
    decisions: List[str],
    ground_truths: List[int],
    abstained_count: int,
    total_short_text_items: int,
    k_recall: int = 10,
) -> Dict[str, Any]:
    """
    Generates a full summary evaluation report dictionary.
    """
    brier = calculate_brier_score(probabilities, ground_truths)
    ece = calculate_expected_calibration_error(probabilities, ground_truths)
    far = calculate_false_attribution_rate(decisions, ground_truths)
    recall_at_10 = calculate_recall_at_k(probabilities, ground_truths, k=k_recall)
    roc_auc = calculate_roc_auc(probabilities, ground_truths)

    abstain_rate = (abstained_count / total_short_text_items * 100.0) if total_short_text_items > 0 else 100.0

    return {
        "brier_score": round(brier, 4),
        "expected_calibration_error": round(ece, 4),
        "false_attribution_rate_percent": round(far, 2),
        "recall_at_10_percent": round(recall_at_10, 2),
        "roc_auc": round(roc_auc, 4),
        "short_text_abstention_rate_percent": round(abstain_rate, 2),
        "total_cases_evaluated": len(ground_truths),
        "ece_target_passed": bool(ece < 0.15),
        "far_target_passed": bool(far == 0.0),
        "recall_target_passed": bool(recall_at_10 == 100.0),
        "roc_auc_target_passed": bool(roc_auc > 0.90),
    }

