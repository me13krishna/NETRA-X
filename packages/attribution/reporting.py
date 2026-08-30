"""
reporting.py — Automated Evidence Waterfall & Attribution Report Formatting Module.

Renders step-by-step LLR evidence waterfall contribution breakdowns, ASCII visual diagrams,
and GitHub-flavored Markdown reports for NETRA-X Attribution Results.
"""

from typing import List, Dict, Any, Optional
from packages.common.types import AttributionResult, EvidenceFamily, FAMILY_CAPS


class AttributionReportFormatter:
    """
    Formatter for Bayesian Evidence Fusion waterfall breakdowns and markdown reports.
    """

    @staticmethod
    def build_waterfall_breakdown(attribution_result: AttributionResult) -> Dict[str, Any]:
        """
        Computes step-by-step mathematical waterfall accounting across evidence families.
        
        Returns:
            Dict containing initial prior, per-family raw/discounted/capped sums, contradiction penalty,
            final net LLR, and posterior probability.
        """
        family_breakdowns: Dict[str, Dict[str, Any]] = {}
        contradiction_summary = []

        # Iterate over item contributions recorded in AttributionResult
        contributions = getattr(attribution_result, "contributions", [])
        for item in contributions:
            if item.get("abstain"):
                continue

            if item.get("is_contradiction"):
                contradiction_summary.append({
                    "id": item.get("evidence_id"),
                    "feature_name": item.get("feature_name"),
                    "contradiction_weight": abs(round(item.get("llr_contrib", 0.0), 4)),
                    "metadata": item.get("metadata", {}),
                })
                continue

            fam_name = str(item.get("family", "OTHER"))
            if fam_name not in family_breakdowns:
                # Find matching enum cap if applicable
                fam_enum = EvidenceFamily(fam_name) if fam_name in EvidenceFamily.__members__ else None
                cap_limit = FAMILY_CAPS.get(fam_enum, 5.0) if fam_enum else 5.0

                family_breakdowns[fam_name] = {
                    "family": fam_name,
                    "items": [],
                    "raw_sum": 0.0,
                    "contrib_sum": 0.0,
                    "cap_limit": cap_limit,
                }

            raw_val = item.get("raw_llr", 0.0)
            contrib_val = item.get("llr_contrib", 0.0)
            family_breakdowns[fam_name]["raw_sum"] += raw_val
            family_breakdowns[fam_name]["contrib_sum"] += contrib_val
            family_breakdowns[fam_name]["items"].append({
                "id": item.get("evidence_id"),
                "feature_name": item.get("feature_name"),
                "raw_llr": round(raw_val, 4),
                "llr_contrib": round(contrib_val, 4),
                "dependence_group": item.get("dependence_group"),
            })

        # Calculate summary per family using AttributionResult family_scores
        family_summary_list = []
        total_positive_capped = 0.0

        for fam_name, data in family_breakdowns.items():
            raw_sum = data["raw_sum"]
            cap_limit = data["cap_limit"]
            # Check family score from result or fallback to data["contrib_sum"]
            capped_sum = attribution_result.family_scores.get(fam_name, min(data["contrib_sum"], cap_limit))
            total_positive_capped += capped_sum

            family_summary_list.append({
                "family": fam_name,
                "item_count": len(data["items"]),
                "raw_llr_sum": round(raw_sum, 4),
                "cap_limit": cap_limit,
                "capped_llr_contribution": round(capped_sum, 4),
                "is_capped": raw_sum > cap_limit or data["contrib_sum"] > cap_limit,
                "items": data["items"],
            })


        return {
            "base_prior_llr": 0.0,
            "family_contributions": family_summary_list,
            "total_positive_capped_llr": round(total_positive_capped, 4),
            "contradiction_penalty": round(attribution_result.contradiction_penalty, 4),
            "contradictions": contradiction_summary,
            "final_net_llr": round(attribution_result.final_llr, 4),
            "posterior_probability": round(attribution_result.posterior_probability, 4),
            "decision": attribution_result.decision.value,
        }

    @staticmethod
    def format_ascii_waterfall(attribution_result: AttributionResult) -> str:
        """
        Renders a clean ASCII CLI visual waterfall chart showing LLR additions/deductions.
        """
        breakdown = AttributionReportFormatter.build_waterfall_breakdown(attribution_result)
        lines = []
        lines.append("=" * 70)
        lines.append("NETRA-X EVIDENCE WATERFALL LLR CONTRIBUTION DIAGRAM")
        lines.append("=" * 70)
        lines.append(f"{'Step / Evidence Family':<25} | {'LLR Contrib':<11} | Visual LLR Bar")
        lines.append("-" * 70)

        lines.append(f"{'[Base Prior H1]':<25} | {0.00:<+11.2f} | ")

        for fam in breakdown["family_contributions"]:
            contrib = fam["capped_llr_contribution"]
            bar_len = int(min(contrib * 2, 20))
            bar_str = "█" * bar_len
            cap_note = f" (Capped at {fam['cap_limit']:.1f})" if fam["is_capped"] else ""
            fam_label = f"[{fam['family']}]"
            lines.append(f"{fam_label:<25} | {contrib:<+11.2f} | {bar_str}{cap_note}")


        if breakdown["contradictions"]:
            c_pen = breakdown["contradiction_penalty"]
            bar_len = int(min(c_pen * 2, 20))
            bar_str = "░" * bar_len
            lines.append(f"{'[Contradictions]':<25} | {-c_pen:<+11.2f} | {bar_str} (Penalty)")

        lines.append("-" * 70)
        lines.append(
            f"{'[Final Net LLR]':<25} | {breakdown['final_net_llr']:<+11.2f} | "
            f"P(H1|E) = {breakdown['posterior_probability']:.4f} ({breakdown['decision']})"
        )
        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def format_markdown_report(
        target_actor: str, candidate_actor: str, attribution_result: AttributionResult
    ) -> str:
        """
        Formats a complete GitHub-flavored Markdown Attribution Report.
        """
        breakdown = AttributionReportFormatter.build_waterfall_breakdown(attribution_result)
        lines = []
        lines.append(f"# NETRA-X Attribution Report — {target_actor} &harr; {candidate_actor}\n")
        lines.append("## Executive Summary\n")
        lines.append(f"- **Target Actor**: `{target_actor}`")
        lines.append(f"- **Candidate Actor**: `{candidate_actor}`")
        lines.append(f"- **Attribution Decision**: **`{breakdown['decision']}`**")
        lines.append(f"- **Posterior Probability P(H1|E)**: `{breakdown['posterior_probability'] * 100:.2f}%` (`{breakdown['posterior_probability']:.4f}`)")
        lines.append(f"- **Final Net LLR**: `{breakdown['final_net_llr']:+.2f}`")
        lines.append(f"- **Total Contradiction Penalty W_c**: `{breakdown['contradiction_penalty']:.2f}`\n")

        lines.append("## Evidence Waterfall Family Breakdown\n")
        lines.append("| Evidence Family | Item Count | Raw LLR Sum | Cap Limit | Net LLR Contribution | Status |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :--- |")

        for fam in breakdown["family_contributions"]:
            status_str = f"Cap Reached ({fam['cap_limit']:.1f})" if fam["is_capped"] else "Uncapped"
            lines.append(
                f"| `{fam['family']}` | {fam['item_count']} | `{fam['raw_llr_sum']:+.2f}` | `{fam['cap_limit']:.1f}` | `{fam['capped_llr_contribution']:+.2f}` | {status_str} |"
            )

        lines.append("\n## Contradiction Audit\n")
        if breakdown["contradictions"]:
            lines.append("| Feature Name | Contradiction Weight W_c | Feature ID |")
            lines.append("| :--- | :---: | :--- |")
            for c in breakdown["contradictions"]:
                lines.append(f"| `{c['feature_name']}` | `- {c['contradiction_weight']:.2f}` | `{c['id']}` |")
        else:
            lines.append("No adverse or conflicting contradiction penalties detected.\n")

        lines.append("\n---\n*Report generated by NETRA-X Krishna Bayesian Attribution Engine v1.0*")
        return "\n".join(lines)

    @staticmethod
    def export_summary_json(
        target_actor: str, candidate_actor: str, attribution_result: AttributionResult
    ) -> Dict[str, Any]:
        """
        Exports a structured JSON summary payload for API responses.
        """
        breakdown = AttributionReportFormatter.build_waterfall_breakdown(attribution_result)
        return {
            "target_actor": target_actor,
            "candidate_actor": candidate_actor,
            "decision": breakdown["decision"],
            "posterior_probability": breakdown["posterior_probability"],
            "final_net_llr": breakdown["final_net_llr"],
            "waterfall": breakdown,
        }


def build_waterfall_breakdown(attribution_result: AttributionResult) -> Dict[str, Any]:
    """
    Helper function to build structured waterfall breakdown.
    """
    return AttributionReportFormatter.build_waterfall_breakdown(attribution_result)


def format_ascii_waterfall(attribution_result: AttributionResult) -> str:
    """
    Helper function to format CLI ASCII waterfall diagram.
    """
    return AttributionReportFormatter.format_ascii_waterfall(attribution_result)


def format_markdown_report(
    target_actor: str, candidate_actor: str, attribution_result: AttributionResult
) -> str:
    """
    Helper function to format GitHub Markdown report.
    """
    return AttributionReportFormatter.format_markdown_report(target_actor, candidate_actor, attribution_result)
