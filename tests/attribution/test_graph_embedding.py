"""
test_graph_embedding.py — Unit tests for PyTorch Node2Vec Graph Embedding & Link Prediction module.
"""

import math
import numpy as np
import pytest

from packages.attribution.graph_embedding import (
    Node2VecGraphEmbedder,
    LinkPredictor,
    fit_graph_embeddings,
    evaluate_graph_link,
)
from packages.common.types import EvidenceFamily


SAMPLE_ADJACENCY = {
    "actor_nstar7": ["alias_shadowbyte", "pgp_key_01", "wallet_btc_01"],
    "alias_shadowbyte": ["actor_nstar7", "forum_dread"],
    "pgp_key_01": ["actor_nstar7", "server_onion_01"],
    "wallet_btc_01": ["actor_nstar7", "wallet_btc_02"],
    "wallet_btc_02": ["wallet_btc_01"],
    "server_onion_01": ["pgp_key_01", "favicon_mmh3_101"],
    "favicon_mmh3_101": ["server_onion_01"],
    "forum_dread": ["alias_shadowbyte"],
    "unconnected_actor": ["unconnected_wallet"],
    "unconnected_wallet": ["unconnected_actor"],
}


def test_random_walk_generation():
    """
    Test Node2Vec random walk sequence generation bounds and node coverage.
    """
    embedder = Node2VecGraphEmbedder(embed_dim=64, seed=42)
    walks = embedder.generate_random_walks(SAMPLE_ADJACENCY, num_walks=5, walk_length=10)

    assert len(walks) == 5 * len(SAMPLE_ADJACENCY)
    for walk in walks:
        assert len(walk) <= 10
        assert walk[0] in SAMPLE_ADJACENCY


def test_graph_embedding_fitting():
    """
    Test fit_embeddings training 64d L2-normalized numpy vectors.
    """
    embeddings = fit_graph_embeddings(SAMPLE_ADJACENCY, embed_dim=64, epochs=3, seed=42)
    assert len(embeddings) == len(SAMPLE_ADJACENCY)

    for node_id, vec in embeddings.items():
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (64,)
        assert vec.dtype == np.float32
        norm = float(np.linalg.norm(vec))
        assert math.isclose(norm, 1.0, rel_tol=1e-3)


def test_link_predictor_scores():
    """
    Test LinkPredictor score computation between node embeddings.
    """
    emb_a = np.array([1.0] + [0.0] * 63, dtype=np.float32)
    emb_b = np.array([1.0] + [0.0] * 63, dtype=np.float32)
    emb_c = np.array([0.0] * 63 + [1.0], dtype=np.float32)

    pred_same = LinkPredictor.predict_link_score(emb_a, emb_b)
    assert pred_same["cosine_similarity"] == 1.0
    assert pred_same["link_probability"] == 1.0
    assert pred_same["topological_link_detected"] is True

    pred_diff = LinkPredictor.predict_link_score(emb_a, emb_c)
    assert pred_diff["cosine_similarity"] == 0.0
    assert pred_diff["link_probability"] == 0.50
    assert pred_diff["topological_link_detected"] is False


def test_evaluate_graph_link_evidence_item():
    """
    Test evaluate_graph_link emitting valid EvidenceItem for Bayesian Engine.
    """
    embeddings = fit_graph_embeddings(SAMPLE_ADJACENCY, embed_dim=64, epochs=3, seed=42)

    item = evaluate_graph_link("actor_nstar7", "alias_shadowbyte", embeddings, item_id="test_link_1")
    assert item.family == EvidenceFamily.INFRASTRUCTURE
    assert item.feature_name == "graph_topological_distance"
    assert item.abstain is False
    assert "cosine_similarity" in item.metadata

    # Test fallback on missing node
    item_missing = evaluate_graph_link("actor_nstar7", "non_existent_node", embeddings, item_id="test_missing")
    assert item_missing.abstain is True
    assert item_missing.get_effective_llr() == 0.0
