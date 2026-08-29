"""
NETRA-X Attribution Engine Package
Includes Bayesian LLR evidence fusion, isotonic probability calibration, and candidate generation.
"""

from .fusion import (
    RawEvidenceInput,
    AttributionResult,
    compute_attribution,
    decide,
    DEFAULT_LAMBDA,
    FAMILY_CAPS,
    CONTRADICTION_PENALTIES
)
from .calibration import IsotonicCalibrator, calibrate_probability, determine_confidence_tier
from .candidate_gen import CandidateGenerator
from packages.schemas.models import EvidenceFamily

__all__ = [
    "RawEvidenceInput",
    "AttributionResult",
    "compute_attribution",
    "decide",
    "DEFAULT_LAMBDA",
    "FAMILY_CAPS",
    "CONTRADICTION_PENALTIES",
    "IsotonicCalibrator",
    "calibrate_probability",
    "determine_confidence_tier",
    "CandidateGenerator",
    "EvidenceFamily"
]
