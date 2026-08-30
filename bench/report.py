"""
report.py — CLI evaluation benchmark reporter script for Krishna's Attribution Engine.

Usage:
    python -m bench.report
"""

import sys
from typing import List, Dict, Any

from bench.synthetic.generator import generate_benchmark_suite
from bench.metrics import calculate_evaluation_report
from packages.attribution.decide import evaluate_attribution
from packages.attribution.calibration import IsotonicCalibrator


def run_benchmark_eval(total_cases: int = 60, seed: int = 42) -> Dict[str, Any]:
    """
    Runs diversified synthetic benchmark suite, fits IsotonicCalibrator on ground truth training split,
    evaluates test cases, and outputs ECE, FAR, Brier Score, Recall@10, and ROC-AUC.
    """
    all_cases = generate_benchmark_suite(num_cases=total_cases, seed=seed)

    # 50/50 Train / Test Split
    split_idx = len(all_cases) // 2
    train_cases = all_cases[:split_idx]
    test_cases = all_cases[split_idx:]

    # 1. Fit Isotonic Calibrator on ground truth training split
    train_scores = []
    train_labels = []
    for c in train_cases:
        res = evaluate_attribution(c.evidence_items)
        train_scores.append(res.final_llr)
        train_labels.append(c.ground_truth_match)

    calibrator = IsotonicCalibrator()
    calibrator.fit(train_scores, train_labels)

    # 2. Evaluate test suite with fitted calibrator
    probabilities = []
    decisions = []
    ground_truths = []
    abstained_total = 0
    short_text_cases = 0

    print("=" * 85)
    print("NETRA-X KRISHNA — BAYESIAN ATTRIBUTION ENGINE BENCHMARK REPORT")
    print("=" * 85)
    print(f"{'Case ID':<35} | {'GT':<3} | {'LLR':<7} | {'P(H1|E)':<7} | {'Decision':<22}")
    print("-" * 85)

    for case in test_cases:
        result = evaluate_attribution(case.evidence_items, calibrator=calibrator)
        probabilities.append(result.posterior_probability)
        decisions.append(result.decision.value)
        ground_truths.append(case.ground_truth_match)
        abstained_total += result.abstained_items_count
        if "short_text" in case.case_id:
            short_text_cases += 1

        print(
            f"{case.case_id:<35} | {case.ground_truth_match:<3} | {result.final_llr:<7.2f} | "
            f"{result.posterior_probability:<7.4f} | {result.decision.value:<22}"
        )

    print("-" * 85)
    report = calculate_evaluation_report(
        probabilities=probabilities,
        decisions=decisions,
        ground_truths=ground_truths,
        abstained_count=abstained_total,
        total_short_text_items=short_text_cases,
        k_recall=10,
    )

    print("\n" + "=" * 55)
    print("BENCHMARK EVALUATION METRICS SUMMARY")
    print("=" * 55)
    print(f"Total Test Cases Evaluated:       {report['total_cases_evaluated']}")
    print(f"Brier Score:                       {report['brier_score']:.4f}")
    print(f"Expected Calibration Error (ECE):  {report['expected_calibration_error']:.4f} (Target < 0.15 -> {'PASSED' if report['ece_target_passed'] else 'FAILED'})")
    print(f"False-Attribution Rate (FAR):      {report['false_attribution_rate_percent']:.2f}% (Target == 0.0% -> {'PASSED' if report['far_target_passed'] else 'FAILED'})")
    print(f"Recall@10:                         {report['recall_at_10_percent']:.2f}% (Target == 100.0% -> {'PASSED' if report['recall_target_passed'] else 'FAILED'})")
    print(f"ROC-AUC Score:                     {report['roc_auc']:.4f} (Target > 0.90 -> {'PASSED' if report['roc_auc_target_passed'] else 'FAILED'})")
    print(f"Short-Text Abstention Rate:        {report['short_text_abstention_rate_percent']:.2f}%")
    print("=" * 55)

    return report


if __name__ == "__main__":
    rep = run_benchmark_eval(total_cases=60, seed=42)
    if not rep["ece_target_passed"] or not rep["far_target_passed"] or not rep["recall_target_passed"] or not rep["roc_auc_target_passed"]:
        print("\n[WARNING] Benchmark failed quality bar requirements!")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All benchmark quality metrics passed cleanly!")
        sys.exit(0)

