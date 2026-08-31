"""
Stylometry package initialization.
"""
from packages.stylometry.features import extract_stylometric_features, extract_word_tokens
from packages.stylometry.episodes import StylometryEpisode, MIN_WORD_COUNT_THRESHOLD
from packages.stylometry.verify import (
    verify_author_stylometry,
    verify_short_text_neural_stylometry,
    compute_burrows_delta,
    compute_cosine_similarity,
)

# corpus_stats needs only numpy, so it stays a hard import.
from packages.stylometry.corpus_stats import BackgroundCorpusStats

# torch is a ~2GB install and is not a runtime dependency of the API, the
# benchmark, or the classical stylometry path -- so the neural encoder is
# optional here rather than mandatory. Importing it eagerly made the whole
# package unimportable without torch, which took down bench.report and every
# module that touches packages.stylometry.
#
# verify.py already imports it lazily inside the function that uses it; this
# keeps the package boundary consistent with that. Calling a neural symbol
# without torch installed still raises, and says how to fix it.
try:
    from packages.stylometry.neural import (
        NeuralStylometryEncoder,
        extract_neural_style_embedding,
    )
    NEURAL_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the install profile
    NEURAL_AVAILABLE = False

    def _neural_unavailable(*_args, **_kwargs):
        raise ImportError(
            "Neural stylometry requires PyTorch, which is an optional extra. "
            "Install it with:  pip install -e .[neural]"
        )

    NeuralStylometryEncoder = _neural_unavailable  # type: ignore[assignment]
    extract_neural_style_embedding = _neural_unavailable  # type: ignore[assignment]

__all__ = [
    "extract_stylometric_features",
    "extract_word_tokens",
    "StylometryEpisode",
    "MIN_WORD_COUNT_THRESHOLD",
    "verify_author_stylometry",
    "verify_short_text_neural_stylometry",
    "compute_burrows_delta",
    "compute_cosine_similarity",
    "BackgroundCorpusStats",
    "NeuralStylometryEncoder",
    "extract_neural_style_embedding",
    "NEURAL_AVAILABLE",
]
