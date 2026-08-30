"""
generator.py — Synthetic benchmark dataset generator for NETRA-X Krishna attribution suite.
"""

from typing import List
from bench.synthetic.scenarios import (
    SyntheticBenchmarkCase,
    generate_diverse_benchmark_cases,
)


def generate_benchmark_suite(num_cases: int = 60, seed: int = 42) -> List[SyntheticBenchmarkCase]:
    """
    Generates a full, diversified synthetic benchmark dataset containing:
    - Actor A (True positive hero match)
    - Actor B (Coincidence non-match)
    - Actor C (Adversarial clone imposter with contradiction)
    - Short text abstention cases
    - Multi-family true matches & weak coincidences across continuous LLR spectrum
    - Neural short-text stylometry leads
    """
    return generate_diverse_benchmark_cases(num_cases=num_cases, seed=seed)

