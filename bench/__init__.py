"""
Bench package initialization.
"""
from bench.metrics import (
    calculate_brier_score,
    calculate_expected_calibration_error,
    calculate_false_attribution_rate,
    calculate_evaluation_report,
)

__all__ = [
    "calculate_brier_score",
    "calculate_expected_calibration_error",
    "calculate_false_attribution_rate",
    "calculate_evaluation_report",
]
