"""
NETRA-X Evidence Attribution Compatibility Module
Bridge layer forwarding to packages.attribution.fusion and packages.attribution.calibration.
"""

from packages.attribution.fusion import (
    RawEvidenceInput,
    AttributionResult,
    compute_attribution,
    decide,
    FAMILY_CAPS,
    CONTRADICTION_PENALTIES,
    DEFAULT_LAMBDA
)
from packages.attribution.calibration import (
    calibrate_probability,
    determine_confidence_tier
)
from packages.schemas.models import EvidenceFamily

__all__ = [
    "RawEvidenceInput",
    "AttributionResult",
    "compute_attribution",
    "decide",
    "calibrate_probability",
    "determine_confidence_tier",
    "FAMILY_CAPS",
    "CONTRADICTION_PENALTIES",
    "DEFAULT_LAMBDA",
    "EvidenceFamily"
]
