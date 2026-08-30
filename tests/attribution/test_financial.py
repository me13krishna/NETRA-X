"""
test_financial.py — Unit tests for Cryptocurrency UTXO Co-Spending & Financial Evidence module.
"""

import pytest
from packages.attribution.financial import (
    UTXOCoSpendingClusterer,
    FinancialAttributionEvaluator,
    build_utxo_clusters,
    evaluate_wallet_evidence,
)
from packages.common.types import EvidenceFamily


SAMPLE_BITCOIN_TRANSACTIONS = [
    {
        "txid": "tx01",
        "inputs": ["1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "132F25uv17spT6UXvuPvyVSp2wN7G4NKTq"],
        "outputs": ["1LN6K1sS1rK8g78xJaNVN2"],
    },
    {
        "txid": "tx02",
        "inputs": ["132F25uv17spT6UXvuPvyVSp2wN7G4NKTq", "17V2J31v17spT6UXvuPvyVSp2wN7G4NKTq"],
        "outputs": ["19N6K1sS1rK8g78xJaNVN2"],
    },
    {
        "txid": "tx03",
        "inputs": ["1UnconnectedAddr99"],
        "outputs": ["1UnconnectedAddr100"],
    },
]


def test_utxo_co_spending_cluster_building():
    """
    Test multi-input transaction co-spending heuristic merging input addresses into a single cluster ID.
    """
    cluster_map = build_utxo_clusters(SAMPLE_BITCOIN_TRANSACTIONS)

    addr1 = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
    addr2 = "132F25uv17spT6UXvuPvyVSp2wN7G4NKTq"
    addr3 = "17V2J31v17spT6UXvuPvyVSp2wN7G4NKTq"
    addr_unconnected = "1UnconnectedAddr99"

    assert addr1 in cluster_map
    assert addr2 in cluster_map
    assert addr3 in cluster_map

    # Addresses 1, 2, and 3 must belong to the exact same cluster ID
    assert cluster_map[addr1] == cluster_map[addr2]
    assert cluster_map[addr2] == cluster_map[addr3]

    # Unconnected address must have a distinct cluster ID
    assert cluster_map[addr_unconnected] != cluster_map[addr1]


def test_monero_privacy_classification():
    """
    Test Monero stealth address validation and RingCT privacy level scoring.
    """
    xmr_tx_standard = {
        "address": "4" + "a" * 94,
        "ring_size": 16,
        "key_image": "abc123keyimage",
    }
    res_std = UTXOCoSpendingClusterer.classify_monero_privacy_tx(xmr_tx_standard)
    assert res_std["valid_stealth_address"] is True
    assert res_std["is_subaddress"] is False
    assert res_std["privacy_score"] == 0.95
    assert res_std["decoy_risk_level"] == "LOW"

    xmr_tx_subaddress = {
        "address": "8" + "b" * 94,
        "ring_size": 11,
        "key_image": "def456keyimage",
    }
    res_sub = UTXOCoSpendingClusterer.classify_monero_privacy_tx(xmr_tx_subaddress)
    assert res_sub["valid_stealth_address"] is True
    assert res_sub["is_subaddress"] is True
    assert res_sub["privacy_score"] == 0.85
    assert res_sub["decoy_risk_level"] == "MEDIUM"


def test_evaluate_wallet_evidence():
    """
    Test direct address reuse vs UTXO cluster co-spending match EvidenceItem generation.
    """
    cluster_map = build_utxo_clusters(SAMPLE_BITCOIN_TRANSACTIONS)
    addr1 = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
    addr3 = "17V2J31v17spT6UXvuPvyVSp2wN7G4NKTq"
    addr_other = "1UnconnectedAddr99"

    # 1. Direct address reuse
    item_direct = evaluate_wallet_evidence(addr1, addr1, cluster_map, item_id="ev_direct")
    assert item_direct.family == EvidenceFamily.FINANCIAL
    assert item_direct.feature_name == "btc_address_reuse"
    assert item_direct.abstain is False
    assert item_direct.metadata["match_type"] == "DIRECT_ADDRESS_REUSE"

    # 2. UTXO co-spending cluster match
    item_cluster = evaluate_wallet_evidence(addr1, addr3, cluster_map, item_id="ev_cluster")
    assert item_cluster.family == EvidenceFamily.FINANCIAL
    assert item_cluster.feature_name == "btc_co_input_clustering"
    assert item_cluster.abstain is False
    assert item_cluster.metadata["match_type"] == "UTXO_CO_INPUT_CLUSTER_MATCH"

    # 3. No match -> Abstain
    item_none = evaluate_wallet_evidence(addr1, addr_other, cluster_map, item_id="ev_none")
    assert item_none.abstain is True
    assert item_none.get_effective_llr() == 0.0
