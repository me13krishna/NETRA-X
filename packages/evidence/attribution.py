"""
NETRA-X Evidence Attribution Bridge

The single import path from application code into the attribution engine.
`apps/api/`, `seed/` and `tests/` import from here and never from
`packages.attribution` directly, so Krishna can restructure the engine without
touching the API.

This module now earns that separation. The promoted engine exposes a different
shape from the one it replaced:

    was                              now
    ---------------------------      ---------------------------------------
    compute_attribution(...)         same name, in decide.py, returns a dict
      -> AttributionResult object       with different key names
    RawEvidenceInput                 EvidenceItem (packages.common.types)
    calibrate_probability            sigmoid_llr_to_prob
    module-level constants           LLRFusionEngine + mu_table.yaml

Rather than rewrite every caller, the adapter below maps the new dict back onto
the attribute access callers already use. Two mappings are worth naming
because they are not obvious:

  final_llr -> raw_log_lr    The engine reports `raw_llr` (pre-cap),
                             `total_capped_llr`, and `final_llr` (capped minus
                             contradictions). The old `raw_log_lr` was always
                             the post-contradiction figure, so `final_llr` is
                             the honest equivalent -- `raw_llr` would silently
                             inflate every score.

  contributions -> split     The engine returns one list; callers expect
                             supporting_items and contradiction_items
                             separately, split on `is_contradiction`.
"""

from typing import Any, Dict, List, Optional, Union

from packages.attribution.calibration import (
    IsotonicCalibrator,
    sigmoid_llr_to_prob,
)
from packages.attribution.decide import compute_attribution as _compute_attribution_dict
from packages.attribution.fusion import LLRFusionEngine, load_mu_table
from packages.common.types import (
    AttributionDecision,
    EvidenceFamily,
    EvidenceItem,
    FAMILY_CAPS,
)

__all__ = [
    "RawEvidenceInput",
    "AttributionResult",
    "compute_attribution",
    "calibrate_probability",
    "determine_confidence_tier",
    "EvidenceFamily",
    "FAMILY_CAPS",
    "AttributionDecision",
    "EvidenceItem",
    "LLRFusionEngine",
    "IsotonicCalibrator",
    "load_mu_table",
]

def RawEvidenceInput(  # noqa: N802 - kept capitalised; callers use it as a constructor
    evidence_id: str = "",
    family: Union[str, EvidenceFamily] = EvidenceFamily.SEMANTIC_HANDLE,
    value: str = "",
    m_prob: float = 0.90,
    u_prob: float = 0.01,
    dependence_group: str = "",
    source_uri: str = "",
    extraction_method: str = "",
    timestamp: str = "",
    sha256: str = "",
    is_contradiction: bool = False,
    contradiction_weight: Optional[float] = None,
    contradiction_type: str = "",
    abstain: bool = False,
    source_reliability: float = 1.0,
    **extra: Any,
) -> EvidenceItem:
    """Build an engine `EvidenceItem` from the legacy call shape.

    An alias would not work: the engine renamed nearly every field
    (`evidence_id` -> `id`, `m_prob` -> `m_i`, `u_prob` -> `u_i`) and dropped
    the provenance fields into `metadata`. Adapting here means call sites in
    `seed/` and `tests/` keep working unchanged, which is the whole point of
    having a bridge.

    Provenance is preserved rather than discarded -- `source_uri`,
    `extraction_method`, `timestamp` and `sha256` move into `metadata`, so the
    evidence waterfall can still show where a contribution came from.
    """
    if isinstance(family, str):
        try:
            family_enum = EvidenceFamily(family)
        except ValueError:
            # Tolerate the old display labels ("Exact Identity", "Content / NLP").
            normalised = family.strip().upper().replace("/", "_").replace(" ", "_")
            normalised = "_".join(p for p in normalised.split("_") if p)
            family_enum = EvidenceFamily(normalised)
    else:
        family_enum = family

    # The old API named a contradiction ("Temporal Impossibility"); the engine
    # wants a numeric weight. Resolve the name to its configured weight rather
    # than dropping it -- silently defaulting to 0.0 turns a contradiction into
    # a no-op, which is exactly the failure mode contradictions exist to catch.
    if contradiction_weight is None:
        contradiction_weight = (
            CONTRADICTION_PENALTIES.get(contradiction_type, 10.0)
            if is_contradiction
            else 0.0
        )

    metadata: Dict[str, Any] = {
        "value": value,
        "source_uri": source_uri,
        "extraction_method": extraction_method,
        "timestamp": timestamp,
        "sha256": sha256,
    }
    if contradiction_type:
        metadata["contradiction_type"] = contradiction_type
    metadata.update(extra)

    return EvidenceItem(
        id=evidence_id,
        feature_name=value or evidence_id,
        family=family_enum,
        dependence_group=dependence_group,
        m_i=m_prob,
        u_i=u_prob,
        is_contradiction=is_contradiction,
        contradiction_weight=contradiction_weight,
        abstain=abstain,
        source_reliability=source_reliability,
        metadata=metadata,
    )

# Some callers pass family keys as plain strings ("EXACT_IDENTITY"), so expose
# caps keyed by string as well as by enum.
FAMILY_CAPS_BY_NAME: Dict[str, float] = {
    family.value: cap for family, cap in FAMILY_CAPS.items()
}

# Legacy contradiction names -> weights, read from the engine's own config so
# there is one source of truth. The engine keys these by identifier
# (`temporal_impossible_overlap`); callers still use the display names, so both
# resolve to the same number.
_CONTRADICTION_CONFIG = (load_mu_table() or {}).get("contradictions", {}) or {}

CONTRADICTION_PENALTIES: Dict[str, float] = {
    name: float(cfg.get("contradiction_weight", 10.0))
    for name, cfg in _CONTRADICTION_CONFIG.items()
}
CONTRADICTION_PENALTIES.update({
    "Temporal Impossibility": CONTRADICTION_PENALTIES.get("temporal_impossible_overlap", 15.0),
    "PGP Key Identity Conflict": CONTRADICTION_PENALTIES.get("pgp_key_conflict", 20.0),
    "Wallet Conflict": CONTRADICTION_PENALTIES.get("wallet_conflict", 8.0),
})


def determine_confidence_tier(prob: float) -> str:
    """Probability -> analyst-facing tier label.

    The promoted engine reports an `AttributionDecision`
    (HIGH_CONFIDENCE_LINK / LOW_CONFIDENCE_LINK / INSUFFICIENT_EVIDENCE /
    CONTRADICTION_REJECTED) and dropped this function. The tier strings are
    still what the database stores and the UI renders, so the mapping lives
    here rather than forcing a migration of every stored hypothesis.

    Thresholds are unchanged from the previous implementation, so existing
    rows keep the same meaning.
    """
    if prob >= 0.85:
        return "High Confidence"
    if prob >= 0.60:
        return "Medium Confidence"
    if prob >= 0.35:
        return "Low Confidence"
    return "Insufficient Evidence"


def calibrate_probability(raw_llr: float) -> float:
    """Map a log-likelihood ratio to a probability.

    Retains the old name so callers are unaffected. Note this is the *sigmoid*
    path: fitted isotonic calibration requires a trained IsotonicCalibrator,
    which nothing currently supplies. Anything that reports a calibration
    method should say `sigmoid` until a calibrator is actually fitted.
    """
    return sigmoid_llr_to_prob(raw_llr)


def _normalise_contribution(item: Dict[str, Any]) -> Dict[str, Any]:
    """Add the legacy keys that `seed/` and the waterfall persistence expect.

    The engine renamed `contribution` to `llr_contrib` and stopped surfacing
    `reliability` on the contribution row. `seed/generator.py` writes both into
    `hypothesis_evidence`, so without this the seed fails with a bare
    KeyError: 'reliability' -- which the unit tests do not catch, because they
    exercise the engine rather than the persistence path.

    Both new and old keys are kept, so nothing has to be rewritten twice when
    callers migrate.
    """
    normalised = dict(item)
    normalised.setdefault("contribution", item.get("llr_contrib", 0.0))
    if "reliability" not in normalised:
        metadata = item.get("metadata") or {}
        normalised["reliability"] = float(
            metadata.get("source_reliability", item.get("source_reliability", 1.0))
        )
    return normalised


class AttributionResult:
    """Attribute-access view over the engine's result dictionary.

    Exists so `res.raw_log_lr` keeps working across the engine change. Also
    keeps the raw dict on `.as_dict` for callers that would rather serialise
    the engine's own richer output (decision, explanation, family counts,
    abstention count) than the legacy subset.
    """

    __slots__ = (
        "raw_log_lr", "calibrated_prob", "confidence_tier", "family_scores",
        "supporting_items", "contradiction_items", "total_contradiction_penalty",
        "decision", "family_count", "explanation", "abstained_items_count",
        "as_dict",
    )

    def __init__(self, payload: Dict[str, Any]):
        self.as_dict = payload

        # final_llr, not raw_llr -- see the module docstring.
        self.raw_log_lr: float = payload.get("final_llr", 0.0)
        self.calibrated_prob: float = payload.get("calibrated_prob", 0.0)
        self.family_scores: Dict[str, float] = payload.get("family_scores", {})
        self.total_contradiction_penalty: float = payload.get("contradiction_penalty", 0.0)
        self.decision: str = payload.get("decision", AttributionDecision.INSUFFICIENT_EVIDENCE.value)
        self.family_count: int = payload.get("independent_family_count", 0)
        self.explanation: str = payload.get("explanation", "")
        self.abstained_items_count: int = payload.get("abstained_items_count", 0)

        self.confidence_tier: str = determine_confidence_tier(self.calibrated_prob)

        contributions = [
            _normalise_contribution(c) for c in (payload.get("contributions") or [])
        ]
        self.supporting_items = [c for c in contributions if not c.get("is_contradiction")]
        self.contradiction_items = [c for c in contributions if c.get("is_contradiction")]

    def __repr__(self) -> str:
        return (
            f"AttributionResult(llr={self.raw_log_lr:.3f}, "
            f"p={self.calibrated_prob:.4f}, tier={self.confidence_tier!r}, "
            f"contradictions={len(self.contradiction_items)})"
        )


def compute_attribution(
    evidence_items: List[Union[Dict[str, Any], EvidenceItem]],
    calibrator: Optional[IsotonicCalibrator] = None,
    fusion_engine: Optional[LLRFusionEngine] = None,
    **_legacy: Any,
) -> AttributionResult:
    """Score a candidate pair.

    `**_legacy` absorbs the old keyword arguments (`discount_lambda`,
    `custom_family_caps`) without honouring them: λ and the caps now live in
    `packages/attribution/mu_table.yaml`, which is the point of moving them to
    config. Accepting and ignoring them keeps old call sites running; silently
    *applying* a stale λ would be worse than ignoring it, because the score
    would look right and be wrong.
    """
    payload = _compute_attribution_dict(
        evidence_items,
        calibrator=calibrator,
        fusion_engine=fusion_engine,
    )
    return AttributionResult(payload)
