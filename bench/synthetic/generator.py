"""
generator.py — Synthetic benchmark dataset generator for NETRA-X Krishna attribution suite.
"""

from typing import List
from bench.synthetic.scenarios import (
    SyntheticBenchmarkCase,
    generate_actor_a_scenario,
    generate_actor_b_scenario,
    generate_actor_c_scenario,
    generate_short_text_abstention_scenario,
)


def generate_benchmark_suite(num_replications: int = 10) -> List[SyntheticBenchmarkCase]:
    """
    Generates a full synthetic benchmark dataset containing replicated cases of:
    - Actor A (True positive match)
    - Actor B (Coincidence non-match)
    - Actor C (Adversarial clone imposter with contradiction)
    - Short text abstention cases
    """
    cases: List[SyntheticBenchmarkCase] = []

    for i in range(num_replications):
        case_a = generate_actor_a_scenario()
        case_a.case_id = f"{case_a.case_id}_{i}"
        cases.append(case_a)

        case_b = generate_actor_b_scenario()
        case_b.case_id = f"{case_b.case_id}_{i}"
        cases.append(case_b)

        case_c = generate_actor_c_scenario()
        case_c.case_id = f"{case_c.case_id}_{i}"
        cases.append(case_c)

    # Add short text abstention test case
    cases.append(generate_short_text_abstention_scenario())

    return cases
