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

    @staticmethod
    def vector_similarity_match(
        source_vector: Any,
        candidates: List[Dict[str, Any]],
        top_k: int = 10,
        threshold: float = 0.65,
    ) -> List[Dict[str, Any]]:
        """
        Cosine similarity vector matching over dense profile/bio embeddings (pgvector).
        """
        import numpy as np

        if source_vector is None:
            return []

        src_vec = np.array(source_vector, dtype=np.float64)
        src_norm = np.linalg.norm(src_vec)
        if src_norm == 0.0:
            return []

        results = []
        for cand in candidates:
            cand_vec_raw = cand.get("embedding") if cand.get("embedding") is not None else cand.get("vector")
            if cand_vec_raw is None:
                continue

            tgt_vec = np.array(cand_vec_raw, dtype=np.float64)
            tgt_norm = np.linalg.norm(tgt_vec)
            if tgt_norm == 0.0 or len(tgt_vec) != len(src_vec):
                continue

            cos_sim = float(np.dot(src_vec, tgt_vec) / (src_norm * tgt_norm))
            if cos_sim >= threshold:
                results.append({
                    "candidate_id": cand.get("actor_id") or cand.get("id"),
                    "handle": cand.get("handle"),
                    "match_type": "VECTOR_SIMILARITY_MATCH",
                    "score": round(cos_sim, 4),
                    "evidence_family": "CONTENT_NLP",
                })

        # Sort descending by score and take top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def graph_topological_similarity(neighbors_a: Any, neighbors_b: Any) -> Dict[str, Any]:
        """
        Jaccard neighbor similarity coefficient over identity graph connections.
        Jaccard = |A ∩ B| / |A ∪ B|
        """
        set_a = set(neighbors_a) if neighbors_a else set()
        set_b = set(neighbors_b) if neighbors_b else set()

        intersection = set_a & set_b
        union = set_a | set_b

        jaccard = (len(intersection) / len(union)) if union else 0.0

        return {
            "jaccard_similarity": round(jaccard, 4),
            "shared_neighbor_count": len(intersection),
            "total_unique_neighbors": len(union),
            "topological_match": jaccard >= 0.20,
        }

    @staticmethod
    def favicon_hash_match(source_mmh3: Any, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Favicon MurmurHash3 digest matching across target infrastructure endpoints.
        """
        if source_mmh3 is None:
            return []

        src_str = str(source_mmh3).strip()
        if not src_str:
            return []

        matches = []
        for cand in candidates:
            raw_hash = cand.get("favicon_mmh3") if cand.get("favicon_mmh3") is not None else cand.get("mmh3_hash")
            if raw_hash is None:
                continue

            tgt_str = str(raw_hash).strip()
            if src_str == tgt_str:
                matches.append({
                    "candidate_id": cand.get("actor_id") or cand.get("id"),
                    "favicon_mmh3": raw_hash,
                    "match_type": "FAVICON_MMH3_MATCH",
                    "score": 1.0,
                    "evidence_family": "INFRASTRUCTURE",
                })
        return matches

    @staticmethod
    def multi_modal_candidate_search(
        source_profile: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Unified multi-modal candidate discovery pipeline combining exact PGP,
        fuzzy handle, vector similarity, favicon hash, and graph topology.
        """
        results_by_actor: Dict[str, Dict[str, Any]] = {}

        # 1. PGP Fingerprint Match
        if source_profile.get("pgp_fingerprint"):
            pgp_matches = CandidateGenerator.exact_pgp_match(source_profile["pgp_fingerprint"], candidates)
            for m in pgp_matches:
                aid = m["candidate_id"]
                results_by_actor.setdefault(aid, {"candidate_id": aid, "matches": [], "max_score": 0.0})
                results_by_actor[aid]["matches"].append(m)
                results_by_actor[aid]["max_score"] = max(results_by_actor[aid]["max_score"], m["score"])

        # 2. Fuzzy Handle Match
        if source_profile.get("handle"):
            handle_matches = CandidateGenerator.fuzzy_handle_match(source_profile["handle"], candidates)
            for m in handle_matches:
                aid = m["candidate_id"]
                results_by_actor.setdefault(aid, {"candidate_id": aid, "matches": [], "max_score": 0.0})
                results_by_actor[aid]["matches"].append(m)
                results_by_actor[aid]["max_score"] = max(results_by_actor[aid]["max_score"], m["score"])

        # 3. Vector Similarity Match
        if source_profile.get("embedding"):
            vec_matches = CandidateGenerator.vector_similarity_match(source_profile["embedding"], candidates)
            for m in vec_matches:
                aid = m["candidate_id"]
                results_by_actor.setdefault(aid, {"candidate_id": aid, "matches": [], "max_score": 0.0})
                results_by_actor[aid]["matches"].append(m)
                results_by_actor[aid]["max_score"] = max(results_by_actor[aid]["max_score"], m["score"])

        # 4. Favicon Hash Match
        if source_profile.get("favicon_mmh3"):
            fav_matches = CandidateGenerator.favicon_hash_match(source_profile["favicon_mmh3"], candidates)
            for m in fav_matches:
                aid = m["candidate_id"]
                results_by_actor.setdefault(aid, {"candidate_id": aid, "matches": [], "max_score": 0.0})
                results_by_actor[aid]["matches"].append(m)
                results_by_actor[aid]["max_score"] = max(results_by_actor[aid]["max_score"], m["score"])

        # Convert to list sorted by max_score descending
        ranked = list(results_by_actor.values())
        ranked.sort(key=lambda x: x["max_score"], reverse=True)
        return ranked


