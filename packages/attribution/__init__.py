"""
Attribution package initialization.
"""
from packages.attribution.fusion import LLRFusionEngine, load_mu_table
from packages.attribution.calibration import IsotonicCalibrator, sigmoid_llr_to_prob
from packages.attribution.decide import evaluate_attribution, compute_attribution, parse_evidence_row
from packages.attribution.graph_embedding import (
    Node2VecGraphEmbedder,
    LinkPredictor,
    fit_graph_embeddings,
    evaluate_graph_link,
)
from packages.attribution.financial import (
    UTXOCoSpendingClusterer,
    FinancialAttributionEvaluator,
    build_utxo_clusters,
    evaluate_wallet_evidence,
)
from packages.attribution.reporting import (
    AttributionReportFormatter,
    build_waterfall_breakdown,
    format_ascii_waterfall,
    format_markdown_report,
)

__all__ = [
    "LLRFusionEngine",
    "load_mu_table",
    "IsotonicCalibrator",
    "sigmoid_llr_to_prob",
    "evaluate_attribution",
    "compute_attribution",
    "parse_evidence_row",
    "Node2VecGraphEmbedder",
    "LinkPredictor",
    "fit_graph_embeddings",
    "evaluate_graph_link",
    "UTXOCoSpendingClusterer",
    "FinancialAttributionEvaluator",
    "build_utxo_clusters",
    "evaluate_wallet_evidence",
    "AttributionReportFormatter",
    "build_waterfall_breakdown",
    "format_ascii_waterfall",
    "format_markdown_report",
]



