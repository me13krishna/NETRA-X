"""
NETRA-X Multi-Modal Candidate Generation Helpers
Discovers target candidate entities via exact match, fuzzy trigram handle similarity,
graph topology distance, and temporal activity overlap.
"""

from typing import List, Dict, Any, Tuple
import difflib

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
        """Assess temporal alignment / overlap between two activity profiles."""
        if not events_a or not events_b:
            return {"overlap_detected": False, "contradiction": False}
        
        # Simple overlap assessment stub
        return {
            "overlap_detected": True,
            "temporal_proximity_minutes": 15,
            "contradiction": False
        }
