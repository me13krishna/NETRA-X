"""
verify.py — Burrows' Delta & Cosine Distance Same-Author Verification.
"""

import math
import numpy as np
from typing import Tuple, Dict, Any, Optional

from packages.common.types import EvidenceItem, EvidenceFamily
from packages.stylometry.episodes import StylometryEpisode


def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two numpy vectors.
    """
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def compute_burrows_delta(vec1: np.ndarray, vec2: np.ndarray, std_devs: Optional[np.ndarray] = None) -> float:
    """
    Compute Burrows' Delta distance between two function word frequency vectors.
    Delta = (1 / N) * sum( | z_{1,i} - z_{2,i} | )
    """
    if len(vec1) != len(vec2):
        return 2.0  # Max distance fallback

    if std_devs is None or np.any(std_devs == 0):
        # Unstandardized Manhattan distance per feature
        delta = float(np.mean(np.abs(vec1 - vec2)))
    else:
        # Standardized z-score difference
        z1 = vec1 / std_devs
        z2 = vec2 / std_devs
        delta = float(np.mean(np.abs(z1 - z2)))
    return delta


def verify_author_stylometry(
    ep1: StylometryEpisode,
    ep2: StylometryEpisode,
    item_id: str = "stylometry_verification_1",
    background_std_devs: Optional[np.ndarray] = None,
) -> EvidenceItem:
    """
    Verifies same-author hypothesis across two StylometryEpisodes.

    ENFORCES MANDATORY SHORT-TEXT ABSTENTION:
    If either episode has < 50 words (abstain=True), returns EvidenceItem with abstain=True and score=0.0.
    """
    if ep1.abstain or ep2.abstain or ep1.feature_dict is None or ep2.feature_dict is None:
        return EvidenceItem(
            id=item_id,
            feature_name="stylometry_burrows_delta",
            family=EvidenceFamily.STYLOMETRY,
            dependence_group="author_stylometry",
            m_i=0.82,
            u_i=0.01,
            llr=0.0,
            abstain=True,
            metadata={
                "reason": "Short text abstention (<50 words)",
                "ep1_words": ep1.word_count,
                "ep2_words": ep2.word_count,
            },
        )

    fvec1 = ep1.feature_dict["function_word_vector"]
    fvec2 = ep2.feature_dict["function_word_vector"]

    if background_std_devs is None:
        from packages.stylometry.corpus_stats import BackgroundCorpusStats
        background_std_devs = BackgroundCorpusStats.load_default().get_std_devs()

    cos_sim = compute_cosine_similarity(fvec1, fvec2)
    # Supplying corpus-level standard deviations produces the classic Burrows' Delta z-score version, which is preferred for small samples.
    delta_dist = compute_burrows_delta(fvec1, fvec2, std_devs=background_std_devs)


    # Convert similarity metrics into probabilistic m_i and u_i parameters
    # High cosine similarity / low z-score delta distance -> same-author match
    if cos_sim > 0.85 or delta_dist < 0.75:
        m_i, u_i = 0.85, 0.02
    elif cos_sim > 0.65 or delta_dist < 0.95:
        m_i, u_i = 0.70, 0.05
    else:
        m_i, u_i = 0.20, 0.50


    return EvidenceItem(
        id=item_id,
        feature_name="stylometry_burrows_delta",
        family=EvidenceFamily.STYLOMETRY,
        dependence_group="author_stylometry",
        m_i=m_i,
        u_i=u_i,
        abstain=False,
        metadata={
            "cosine_similarity": cos_sim,
            "burrows_delta": delta_dist,
            "ep1_words": ep1.word_count,
            "ep2_words": ep2.word_count,
        },
    )


def verify_short_text_neural_stylometry(
    ep1: StylometryEpisode,
    ep2: StylometryEpisode,
    item_id: str = "neural_stylometry_1",
) -> EvidenceItem:
    """
    Phase 5 Neural Short-Text Stylometry Verifier.

    Extracts 128d PyTorch subword embeddings for short-text episodes (<50 words)
    and computes cosine similarity to produce a calibrated EvidenceItem.
    """
    # torch is an optional extra ([neural]); the deployment target cannot carry
    # a ~2GB dependency. When it is absent the verifier abstains rather than
    # raising -- which is the semantically correct answer anyway: a model that
    # cannot run has no opinion, and abstention is already a first-class
    # outcome here. The reason is recorded so an abstained run is never
    # mistaken for a confident one.
    try:
        from packages.stylometry.neural import extract_neural_style_embedding
    except ImportError:
        return EvidenceItem(
            id=item_id,
            feature_name="stylometry_neural_embedding",
            family=EvidenceFamily.STYLOMETRY,
            dependence_group="author_stylometry_neural",
            m_i=0.80,
            u_i=0.05,
            llr=0.0,
            abstain=True,
            metadata={"reason": "PyTorch not installed; install with pip install -e .[neural]"},
        )

    text1 = " ".join(ep1.texts) if ep1.texts else ""
    text2 = " ".join(ep2.texts) if ep2.texts else ""

    if not text1.strip() or not text2.strip():
        return EvidenceItem(
            id=item_id,
            feature_name="stylometry_neural_embedding",
            family=EvidenceFamily.STYLOMETRY,
            dependence_group="author_stylometry_neural",
            m_i=0.80,
            u_i=0.05,
            llr=0.0,
            abstain=True,
            metadata={"reason": "Empty text observation"},
        )

    emb1 = extract_neural_style_embedding(text1)
    emb2 = extract_neural_style_embedding(text2)

    cos_sim = compute_cosine_similarity(emb1, emb2)

    # Convert neural cosine similarity into likelihood ratio priors
    if cos_sim > 0.85:
        m_i, u_i = 0.85, 0.01
    elif cos_sim > 0.65:
        m_i, u_i = 0.70, 0.05
    else:
        m_i, u_i = 0.30, 0.40

    return EvidenceItem(
        id=item_id,
        feature_name="stylometry_neural_embedding",
        family=EvidenceFamily.STYLOMETRY,
        dependence_group="author_stylometry_neural",
        m_i=m_i,
        u_i=u_i,
        abstain=False,
        metadata={
            "neural_cosine_similarity": round(float(cos_sim), 4),
            "ep1_words": ep1.word_count,
            "ep2_words": ep2.word_count,
            "embedding_dim": len(emb1),
        },
    )


