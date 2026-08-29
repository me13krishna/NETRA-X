"""
Synthetic benchmark package initialization.
"""
from bench.synthetic.scenarios import (
    SyntheticBenchmarkCase,
    generate_actor_a_scenario,
    generate_actor_b_scenario,
    generate_actor_c_scenario,
    generate_short_text_abstention_scenario,
)
from bench.synthetic.generator import generate_benchmark_suite

__all__ = [
    "SyntheticBenchmarkCase",
    "generate_actor_a_scenario",
    "generate_actor_b_scenario",
    "generate_actor_c_scenario",
    "generate_short_text_abstention_scenario",
    "generate_benchmark_suite",
]
