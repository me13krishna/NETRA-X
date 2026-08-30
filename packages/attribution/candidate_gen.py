from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import difflib


def _parse_iso_datetime(ts: str) -> Optional[datetime]:
    """Parse an ISO-8601 string or fallback datetime string into a UTC-aware datetime."""
    if not isinstance(ts, str) or not ts.strip():
        return None
    try:
        clean_ts = ts.strip()
        if clean_ts.endswith("Z") or clean_ts.endswith("z"):
            clean_ts = clean_ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


class CandidateGenerator:
    """Helper methods for generating threat actor candidate pairs."""

    @staticmethod
    def exact_pgp_match(source_pgp: str, target_pgps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Exact PGP fingerprint matching."""
        matches = []
        clean_src = source_pgp.replace(" ", "").upper()
        for item in target_pgps:
            clean_tgt = item.get("fingerprint", "").replace(" ", "").upper()
            if clean_src == clean_tgt and clean_src:
                matches.append({
                    "candidate_id": item.get("actor_id"),
                    "match_type": "EXACT_PGP_MATCH",
                    "score": 1.0,
                    "evidence_family": "EXACT_IDENTITY"
                })
        return matches

    @staticmethod
    def fuzzy_handle_match(handle: str, candidates: List[Dict[str, Any]], threshold: float = 0.70) -> List[Dict[str, Any]]:
        """Fuzzy handle matching using SequenceMatcher (trigram/string similarity)."""
        results = []
        src_lower = handle.lower().strip()
        for cand in candidates:
            tgt_handle = cand.get("handle", "").lower().strip()
            sim = difflib.SequenceMatcher(None, src_lower, tgt_handle).ratio()
            if sim >= threshold:
                results.append({
                    "candidate_id": cand.get("actor_id"),
                    "handle": cand.get("handle"),
                    "match_type": "FUZZY_HANDLE_MATCH",
                    "score": round(sim, 3),
                    "evidence_family": "SEMANTIC_HANDLE"
                })
        return results

    @staticmethod
    def temporal_overlap_score(events_a: List[str], events_b: List[str]) -> Dict[str, Any]:
        """
        Assess temporal alignment / overlap between two activity profiles.

        Parses ISO-8601 timestamps for pairwise time differences in minutes and evaluates
        overlap detection, minimum/mean proximity, and potential large-gap contradictions.
        """
        parsed_a = [dt for dt in (_parse_iso_datetime(ts) for ts in (events_a or [])) if dt is not None]
        parsed_b = [dt for dt in (_parse_iso_datetime(ts) for ts in (events_b or [])) if dt is not None]

        num_a = len(events_a) if events_a else 0
        num_b = len(events_b) if events_b else 0

        if not parsed_a or not parsed_b:
            return {
                "overlap_detected": False,
                "min_proximity_minutes": None,
                "mean_proximity_minutes": None,
                "contradiction": False,
                "num_events_a": num_a,
                "num_events_b": num_b,
            }

        diffs_minutes: List[float] = []
        for dt_a in parsed_a:
            for dt_b in parsed_b:
                diff_sec = abs((dt_a - dt_b).total_seconds())
                diffs_minutes.append(diff_sec / 60.0)

        min_prox = min(diffs_minutes)
        mean_prox = sum(diffs_minutes) / len(diffs_minutes)
        overlap_detected = min_prox <= 60.0
        contradiction = (not overlap_detected) and (min_prox > 30 * 24 * 60)

        return {
            "overlap_detected": overlap_detected,
            "min_proximity_minutes": round(min_prox, 2),
            "mean_proximity_minutes": round(mean_prox, 2),
            "contradiction": contradiction,
            "num_events_a": num_a,
            "num_events_b": num_b,
        }

