"""
test_candidate_gen.py — Unit tests for CandidateGenerator expansion:
vector_similarity_match, graph_topological_similarity, favicon_hash_match, and multi_modal_candidate_search.
"""

import pytest
import numpy as np
from packages.attribution.candidate_gen import CandidateGenerator


def test_vector_similarity_match():
    """
    Test vector_similarity_match cosine ranking and threshold filtering.
    """
    source_vec = [1.0, 0.0, 0.0]
    candidates = [
        {"actor_id": "actor_exact", "embedding": [1.0, 0.0, 0.0]},  # Cosine 1.0
        {"actor_id": "actor_close", "embedding": [0.8, 0.6, 0.0]},  # Cosine 0.8
        {"actor_id": "actor_far", "embedding": [0.0, 1.0, 0.0]},    # Cosine 0.0 (Below 0.65 threshold)
    ]

    matches = CandidateGenerator.vector_similarity_match(source_vec, candidates, threshold=0.65)
    assert len(matches) == 2
    assert matches[0]["candidate_id"] == "actor_exact"
    assert matches[0]["score"] == 1.0
    assert matches[1]["candidate_id"] == "actor_close"
    assert matches[1]["score"] == 0.8


def test_graph_topological_similarity():
    """
    Test graph_topological_similarity Jaccard neighbor similarity calculation.
    """
    neighbors_a = ["node1", "node2", "node3", "node4"]
    neighbors_b = ["node3", "node4", "node5", "node6"]

    res = CandidateGenerator.graph_topological_similarity(neighbors_a, neighbors_b)
    # Intersection = 2 (node3, node4), Union = 6 (node1..6)
    # Jaccard = 2/6 ~ 0.3333
    assert res["shared_neighbor_count"] == 2
    assert res["total_unique_neighbors"] == 6
    assert res["jaccard_similarity"] == 0.3333
    assert res["topological_match"] is True


def test_favicon_hash_match():
    """
    Test favicon_hash_match matching MurmurHash3 string and integer digests.
    """
    source_hash = "-1598234912"
    candidates = [
        {"actor_id": "actor_match_int", "favicon_mmh3": -1598234912},
        {"actor_id": "actor_match_str", "favicon_mmh3": "-1598234912"},
        {"actor_id": "actor_diff", "favicon_mmh3": 12345678},
    ]

    matches = CandidateGenerator.favicon_hash_match(source_hash, candidates)
    assert len(matches) == 2
    match_ids = [m["candidate_id"] for m in matches]
    assert "actor_match_int" in match_ids
    assert "actor_match_str" in match_ids


def test_multi_modal_candidate_search():
    """
    Test multi_modal_candidate_search aggregating PGP, handle, vector, and favicon signals.
    """
    source_profile = {
        "pgp_fingerprint": "4A8F 912C B301 772E B19C 80A5 D810 23EF 44A9 1876",
        "handle": "nstar_7",
        "embedding": [1.0, 0.0, 0.0],
        "favicon_mmh3": -1598234912,
    }

    candidates = [
        {
            "actor_id": "ShadowByte",
            "fingerprint": "4A8F 912C B301 772E B19C 80A5 D810 23EF 44A9 1876",
            "handle": "nstar_7",
            "embedding": [1.0, 0.0, 0.0],
            "favicon_mmh3": -1598234912,
        },
        {
            "actor_id": "coincidence_user",
            "handle": "nstar_7_sub",
            "embedding": [0.0, 1.0, 0.0],
        },
    ]

    results = CandidateGenerator.multi_modal_candidate_search(source_profile, candidates)
    assert len(results) >= 1
    top_lead = results[0]
    assert top_lead["candidate_id"] == "ShadowByte"
    assert top_lead["max_score"] == 1.0
    assert len(top_lead["matches"]) >= 3  # Matches PGP, handle, vector, and favicon!
