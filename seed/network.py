"""
Synthetic actor-network seed for NETRA-X.

`seed/generator.py` builds the hero scenario: one actor, its identifiers, and a
single hypothesis. That is the right shape for the acceptance test but it makes
the Intelligence Graph look like a star with seven points, which is not what an
analyst would actually be staring at.

This module adds a populated network on top of it -- twelve actors in four
loose clusters, joined by scored attribution hypotheses, shared wallet clusters
and shared hosting infrastructure. It is additive and idempotent: it never
touches the hero actor, and re-running it is a no-op.

Everything is deterministic (fixed RNG seed), so the graph looks the same on
every machine and screenshots stay comparable.

    python -m seed.network          # add the network
    python -m seed.network --reset  # drop it and rebuild
"""

import hashlib
import random
import sys
from datetime import datetime, timedelta

from packages.evidence.uuid7 import uuidv7_str
from packages.graph.projection import GraphProjectionService
from apps.api.database.session import SyncSessionLocal, init_db_sync
from apps.api.database.models import (
    Actor, Alias, Account, PGPKey, Wallet, OnionService, Server, Hypothesis,
    HypothesisEvidence, Evidence, Artifact, Source, Observation,
)

RNG_SEED = 26151          # SIH problem statement number, for luck
MARK = "NETWORK_SYNTH"    # tags rows this module owns, so --reset is surgical

BASE = datetime(2026, 8, 1, 12, 0, 0)

# ---------------------------------------------------------------------------
# The cast. Grouped into clusters that the evidence will later justify linking.
# `cluster` is only used here to decide who gets connected to whom -- it is not
# a claim the system makes; the hypotheses carry the actual scores.
# ---------------------------------------------------------------------------
ACTORS = [
    # cluster, primary alias, category, extra aliases, platforms
    ("RANSOM", "NightHalo",   "Ransomware Operator",      ["nh_operator", "HaloLock", "n1ghthalo"]),
    ("RANSOM", "LockJaw",     "Ransomware Operator",      ["lockjaw_ops", "LJ_Recovery"]),
    ("RANSOM", "PaleCipher",  "Ransomware Affiliate",     ["pale_c", "cipherpale"]),

    ("MARKET", "VelvetForge", "Marketplace Vendor",       ["velvet_forge", "VForge", "vf_supply"]),
    ("MARKET", "AtlasKilo",   "Marketplace Vendor",       ["atlas_k", "KiloAtlas"]),
    ("MARKET", "RedMeridian", "Marketplace Vendor",       ["red_meridian", "meridian_rx"]),

    ("LAUNDR", "ObolBroker",  "Money Laundering Broker",  ["obol_swap", "ob_broker"]),
    ("LAUNDR", "TumblerFox",  "Money Laundering Broker",  ["tumbler_fox", "foxmix"]),

    ("DATA",   "GlassRelay",  "Stolen Data Broker",       ["glass_relay", "grelay", "relayglass"]),
    ("DATA",   "SableIndex",  "Stolen Data Broker",       ["sable_index", "s_index"]),
    ("DATA",   "QuietLedger", "Stolen Data Broker",       ["quiet_ledger", "q_ledger"]),

    ("ARMS",   "IronVesper",  "Arms Vendor",              ["iron_vesper", "vesper_ir"]),
]

PLATFORMS = ["DarkForums", "DreadMirror", "EmpireX", "Telegram", "Jabber", "SilkMirror", "AgoraRelic"]
PROVIDERS = ["FlokiNET", "Njalla", "BuyVM", "Shinjiru", "OrangeWebsite"]

# The point of the map: identifiers that several *differently named* personas
# both touch. A shared wallet cluster is what a co-input ownership heuristic
# would have produced -- one operator, several storefronts. A shared handle is
# the same person reusing a name on another board.
SHARED_WALLET_CLUSTERS = [
    ("CLUSTER_XCHG_A", ["NightHalo", "ObolBroker", "VelvetForge"]),
    ("CLUSTER_XCHG_B", ["GlassRelay", "RedMeridian"]),
    ("CLUSTER_XCHG_C", ["PaleCipher", "TumblerFox", "IronVesper"]),
    ("CLUSTER_XCHG_D", ["LockJaw", "AtlasKilo"]),
]

SHARED_HANDLES = [
    ("nightowl99",  ["LockJaw", "SableIndex"]),
    ("zx_reaper",   ["AtlasKilo", "QuietLedger"]),
    ("ghostpay_ru", ["ObolBroker", "GlassRelay", "IronVesper"]),
]

# (subject alias, object alias, [feature names], [contradiction names])
#
# These are the *observations* behind each link, not the answer. The previous
# version listed a hand-picked calibrated probability per pair and then
# back-solved raw_log_lr by inverting the sigmoid, so every number in the demo
# was a literal wearing the costume of a computed score -- the waterfall had
# nothing to draw, and the review queue asked analysts to adjudicate figures no
# engine had produced.
#
# Now the seed states which features were observed and the real fusion engine
# decides what that is worth. Change a cap or a prior and these scores move.
LINK_EVIDENCE = [
    # (subject, object, observed features, contradictions, abstained features)
    #
    # Strong links: an exact identity match or independent infrastructure and
    # financial reuse. These clear the 0.85 band on their own evidence.
    ("NightHalo",   "LockJaw",
     ["pgp_fingerprint_exact", "btc_co_input_clustering", "stylometry_burrows_delta"], [], []),
    ("VelvetForge", "AtlasKilo",
     ["ssh_host_key_fingerprint", "favicon_mmh3_hash", "simhash_clone_95",
      "btc_co_input_clustering"], [], []),
    ("ObolBroker",  "TumblerFox",
     ["btc_co_input_clustering", "btc_address_reuse", "handle_trigram_fuzzy"], [], []),
    ("GlassRelay",  "SableIndex",
     ["favicon_mmh3_hash", "stylometry_burrows_delta"], [], []),
    ("NightHalo",   "PaleCipher",
     ["favicon_mmh3_hash", "temporal_diurnal_fit"], [], []),

    # Ambiguous links: one weak family carries them, so they land in the
    # 0.50-0.85 band and stay in the review queue. This is the interesting
    # case -- a demo where everything is certain proves nothing.
    ("LockJaw",     "PaleCipher",
     ["stylometry_burrows_delta"], [], ["temporal_diurnal_fit"]),
    ("AtlasKilo",   "RedMeridian",
     ["stylometry_burrows_delta"], [], []),
    ("PaleCipher",  "ObolBroker",
     ["stylometry_burrows_delta"], [], ["btc_address_reuse"]),
    ("VelvetForge", "RedMeridian",
     ["handle_trigram_fuzzy"], [], ["stylometry_burrows_delta"]),
    ("GlassRelay",  "QuietLedger",
     ["handle_trigram_fuzzy"], [], []),

    # Below threshold: the engine declines to link these at all.
    ("SableIndex",  "QuietLedger",
     ["temporal_diurnal_fit"], [], ["stylometry_burrows_delta"]),
    ("RedMeridian", "TumblerFox",
     ["temporal_diurnal_fit"], [], []),

    # A hard contradiction: two conflicting PGP keys published for the same
    # profile. The penalty is uncapped, so this goes negative however much
    # circumstantial evidence supports it -- the property that stops the
    # system talking itself into a wrong identification.
    ("QuietLedger", "IronVesper",
     ["handle_trigram_fuzzy", "stylometry_burrows_delta"], ["pgp_key_conflict"], []),
]


# The engine speaks in decisions; the ledger stores review statuses.
DECISION_TO_STATUS = {
    "HIGH_CONFIDENCE_LINK": "ACCEPTED",
    "LOW_CONFIDENCE_LINK": "PROPOSED",
    "INSUFFICIENT_EVIDENCE": "INSUFFICIENT",
    "CONTRADICTION_REJECTED": "INSUFFICIENT",
}


def _b58(rng, n):
    return "".join(rng.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for _ in range(n))


def _hex(rng, n):
    return "".join(rng.choice("0123456789ABCDEF") for _ in range(n))


def _onion(rng):
    return "".join(rng.choice("abcdefghijklmnopqrstuvwxyz234567") for _ in range(56)) + ".onion"


def already_seeded(session):
    return session.query(Actor).filter(Actor.primary_alias == "NightHalo").first() is not None


def reset(session):
    """Remove only what this module created. The hero scenario is left alone.

    This deleted actors and hypotheses but not the evidence rows behind them,
    which was harmless while the seed wrote no evidence. Now that it writes
    Source/Artifact/Observation/Evidence per link, a partial run left orphaned
    artifacts whose sha256 collided on the next attempt -- so the seed could
    fail once and then never succeed again. Cleanup has to cover everything
    the build writes.
    """
    removed_actors = 0
    names = [a[1] for a in ACTORS]
    actors = session.query(Actor).filter(Actor.primary_alias.in_(names)).all()
    ids = [a.id for a in actors]

    if ids:
        hyp_ids = [h.id for h in session.query(Hypothesis).filter(
            Hypothesis.subject_entity_id.in_(ids) | Hypothesis.object_entity_id.in_(ids)
        ).all()]
        if hyp_ids:
            session.query(HypothesisEvidence).filter(
                HypothesisEvidence.hypothesis_id.in_(hyp_ids)
            ).delete(synchronize_session=False)
            session.query(Hypothesis).filter(
                Hypothesis.id.in_(hyp_ids)).delete(synchronize_session=False)
        for model in (Alias, Account, PGPKey, Wallet):
            session.query(model).filter(model.actor_id.in_(ids)).delete(synchronize_session=False)
        session.query(Actor).filter(Actor.id.in_(ids)).delete(synchronize_session=False)
        removed_actors = len(ids)

    session.query(OnionService).filter(
        OnionService.title.like(f"%{MARK}%")).delete(synchronize_session=False)
    session.query(Server).filter(
        Server.provider.like(f"%{MARK}%")).delete(synchronize_session=False)

    # Evidence chain, keyed by the URI prefix this module owns.
    prefix = "netra-x://seed/network%"
    session.query(Evidence).filter(
        Evidence.source_uri.like(prefix)).delete(synchronize_session=False)
    artifacts = session.query(Artifact).filter(Artifact.storage_uri.like(prefix)).all()
    art_hashes = [a.sha256 for a in artifacts]
    if art_hashes:
        session.query(Observation).filter(
            Observation.content_hash.in_(art_hashes)).delete(synchronize_session=False)
    session.query(Artifact).filter(
        Artifact.storage_uri.like(prefix)).delete(synchronize_session=False)
    session.query(Source).filter(
        Source.base_uri.like(prefix)).delete(synchronize_session=False)

    session.commit()
    if removed_actors:
        print(f"[+] Removed {removed_actors} synthetic network actors, their identifiers "
              f"and {len(artifacts)} evidence artifacts.")
    else:
        print(f"[+] No seed actors present; cleared {len(artifacts)} orphaned artifacts.")


def build(session):
    rng = random.Random(RNG_SEED)
    by_alias = {}

    print(f"[+] Creating {len(ACTORS)} synthetic actors...")
    for idx, (cluster, primary, category, extra) in enumerate(ACTORS):
        actor_id = uuidv7_str()
        actor = Actor(
            id=actor_id,
            primary_alias=primary,
            category=category,
            confidence=round(rng.uniform(0.62, 0.97), 2),
            last_seen=BASE - timedelta(days=rng.randint(0, 120), hours=rng.randint(0, 23)),
            is_synthetic=True,
        )
        session.add(actor)
        by_alias[primary] = (actor_id, cluster)

        # The primary handle is itself an alias observation, plus the others.
        for value in [primary] + extra:
            session.add(Alias(
                id=uuidv7_str(), actor_id=actor_id, value=value,
                platform=rng.choice(PLATFORMS),
                source=rng.choice(["forum_post", "profile_bio", "chat_dump", "marketplace_seller", "vendor_page"]),
                confidence=round(rng.uniform(0.68, 0.99), 2),
            ))

        for _ in range(rng.randint(1, 2)):
            session.add(Account(
                id=uuidv7_str(), actor_id=actor_id,
                platform=rng.choice(PLATFORMS),
                handle=f"{primary.lower()}_{_hex(rng, 3)}",
            ))

        # Not every actor exposes a key -- absence is a real signal too.
        if rng.random() < 0.75:
            session.add(PGPKey(
                id=uuidv7_str(), fingerprint=_hex(rng, 40), key_id=_hex(rng, 8),
                actor_id=actor_id, key_body=None,
            ))

        # Wallets share a cluster_id within an actor group: this is what a
        # co-input clustering heuristic would have produced.
        for _ in range(rng.randint(1, 3)):
            chain = rng.choices(["BTC", "ETH", "XMR"], weights=[6, 3, 1])[0]
            if chain == "BTC":
                address = rng.choice(["bc1q", "1", "3"]) + _b58(rng, rng.choice([33, 38]))
            elif chain == "ETH":
                address = "0x" + _hex(rng, 40).lower()
            else:
                address = "4" + _b58(rng, 94)
            session.add(Wallet(
                id=uuidv7_str(), address=address, chain=chain,
                cluster_id=f"CLUSTER_{cluster}_{idx % 3:02d}", actor_id=actor_id,
            ))

    session.flush()

    print(f"[+] Wiring {len(SHARED_WALLET_CLUSTERS)} shared wallet clusters across actors...")
    for cluster_id, members in SHARED_WALLET_CLUSTERS:
        for name in members:
            if name not in by_alias:
                continue
            actor_id = by_alias[name][0]
            chain = rng.choices(["BTC", "ETH"], weights=[7, 3])[0]
            address = ("bc1q" + _b58(rng, 34)) if chain == "BTC" else ("0x" + _hex(rng, 40).lower())
            session.add(Wallet(
                id=uuidv7_str(), address=address, chain=chain,
                cluster_id=cluster_id, actor_id=actor_id,
            ))

    print(f"[+] Wiring {len(SHARED_HANDLES)} handles reused across actors...")
    for handle, members in SHARED_HANDLES:
        for name in members:
            if name not in by_alias:
                continue
            session.add(Alias(
                id=uuidv7_str(), actor_id=by_alias[name][0], value=handle,
                platform=rng.choice(PLATFORMS), source="handle_reuse",
                confidence=round(rng.uniform(0.72, 0.95), 2),
            ))

    session.flush()

    # Infrastructure. Two services deliberately share a favicon hash and a TLS
    # fingerprint -- the misconfiguration pivot the whole product is premised on.
    print("[+] Creating onion services and hosting infrastructure...")
    shared_favicon = rng.randint(-2 ** 31, 2 ** 31 - 1)
    shared_tls = _hex(rng, 64)
    for i in range(7):
        share = i in (1, 4)
        session.add(OnionService(
            id=uuidv7_str(), onion_address=_onion(rng),
            title=f"{rng.choice(['Vault', 'Bazaar', 'Exchange', 'Relay', 'Depot'])} [{MARK}]",
            favicon_mmh3=shared_favicon if share else rng.randint(-2 ** 31, 2 ** 31 - 1),
            tls_cert_fingerprint=shared_tls if share else _hex(rng, 64),
            first_seen=BASE - timedelta(days=rng.randint(60, 400)),
            last_seen=BASE - timedelta(days=rng.randint(0, 40)),
        ))

    for i in range(5):
        session.add(Server(
            id=uuidv7_str(),
            ip_address=f"{rng.randint(11, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
            asn=f"AS{rng.randint(12000, 65000)}",
            provider=f"{rng.choice(PROVIDERS)} [{MARK}]",
        ))

    # Actor-to-actor attribution links, scored by the real engine.
    print(f"[+] Scoring {len(LINK_EVIDENCE)} links through the fusion engine...")

    from packages.attribution.decide import evaluate_attribution
    from packages.attribution.fusion import load_mu_table
    from packages.common.types import EvidenceItem, EvidenceFamily

    mu = load_mu_table()
    features = mu.get("features", {})
    contradiction_defs = mu.get("contradictions", {})

    # One source and artifact per link, so every evidence row has a real
    # provenance chain: Source -> Artifact(sha256) -> Evidence.
    seed_source = Source(
        id=uuidv7_str(),
        name=f"NETRA-X synthetic network seed [{MARK}]",
        source_type="SYNTHETIC",
        lawful_basis="synthetic_seed",
        base_uri="netra-x://seed/network",
        is_active=True,
    )
    session.add(seed_source)

    for subj, obj, feature_names, contradiction_names, abstained_names in LINK_EVIDENCE:
        if subj not in by_alias or obj not in by_alias:
            continue

        payload = f"{subj}::{obj}::{','.join(feature_names)}".encode()
        artifact = Artifact(
            id=uuidv7_str(),
            sha256=hashlib.sha256(payload).hexdigest(),
            storage_uri=f"netra-x://seed/network/{subj}-{obj}",
            content_type="application/json",
            size=len(payload),
        )
        session.add(artifact)

        observation = Observation(
            id=uuidv7_str(),
            source_id=seed_source.id,
            raw_content=payload.decode(),
            content_hash=artifact.sha256,
        )
        session.add(observation)

        items, ev_rows = [], []
        for name in feature_names:
            spec = features.get(name)
            if spec is None:
                continue
            item_id = uuidv7_str()
            items.append(EvidenceItem(
                id=item_id,
                feature_name=name,
                family=EvidenceFamily(spec["family"]),
                dependence_group=spec["dependence_group"],
                m_i=spec["m_i"],
                u_i=spec["u_i"],
            ))
            ev_rows.append(Evidence(
                id=item_id,
                artifact_id=artifact.id,
                source_uri=f"netra-x://seed/network/{subj}-{obj}",
                collector_version="seed-network-1.0",
                extraction_method=name,
                value=f"{spec.get('description', name)} :: {subj} <-> {obj}",
                confidence=1.0,
                dependence_group=spec["dependence_group"],
                created_at=BASE - timedelta(days=rng.randint(1, 60)),
            ))

        for name in contradiction_names:
            spec = contradiction_defs.get(name)
            if spec is None:
                continue
            item_id = uuidv7_str()
            items.append(EvidenceItem(
                id=item_id,
                feature_name=name,
                family=EvidenceFamily.EXACT_IDENTITY,
                dependence_group=f"contradiction_{name}",
                is_contradiction=True,
                contradiction_weight=spec["contradiction_weight"],
            ))
            ev_rows.append(Evidence(
                id=item_id,
                artifact_id=artifact.id,
                source_uri=f"netra-x://seed/network/{subj}-{obj}",
                collector_version="seed-network-1.0",
                extraction_method=name,
                value=f"{spec.get('description', name)} :: {subj} <-> {obj}",
                confidence=1.0,
                dependence_group=f"contradiction_{name}",
                created_at=BASE - timedelta(days=rng.randint(1, 60)),
            ))

        # Abstentions are recorded, not silently dropped. A stylometry sample
        # under the minimum word count contributes exactly zero, and the
        # waterfall shows it as abstained rather than omitting it -- an analyst
        # needs to see that the test ran and declined to answer.
        for name in abstained_names:
            spec = features.get(name)
            if spec is None:
                continue
            item_id = uuidv7_str()
            items.append(EvidenceItem(
                id=item_id,
                feature_name=name,
                family=EvidenceFamily(spec["family"]),
                dependence_group=spec["dependence_group"],
                m_i=spec["m_i"],
                u_i=spec["u_i"],
                abstain=True,
            ))
            ev_rows.append(Evidence(
                id=item_id,
                artifact_id=artifact.id,
                source_uri=f"netra-x://seed/network/{subj}-{obj}",
                collector_version="seed-network-1.0",
                extraction_method=name,
                value=f"ABSTAINED (insufficient sample) :: {subj} <-> {obj}",
                confidence=0.0,
                dependence_group=spec["dependence_group"],
                created_at=BASE - timedelta(days=rng.randint(1, 60)),
            ))

        if not items:
            continue
        for row in ev_rows:
            session.add(row)

        result = evaluate_attribution(items)

        hyp_id = uuidv7_str()
        session.add(Hypothesis(
            id=hyp_id,
            subject_entity_id=by_alias[subj][0],
            object_entity_id=by_alias[obj][0],
            raw_log_lr=round(result.final_llr, 4),
            calibrated_prob=round(result.posterior_probability, 4),
            status=DECISION_TO_STATUS.get(result.decision.value, "PROPOSED"),
            model_version="v1.0-LLR",
            calibration_version="v1.0-Sigmoid",
            created_at=BASE - timedelta(days=rng.randint(1, 60)),
        ))

        # The waterfall the UI draws: one row per contributing item, carrying
        # the engine's own post-discount contribution.
        # ItemContributionBreakdown.to_dict() keys on `evidence_id` and
        # `llr_contrib`. This looked up "id" and "contribution" -- neither key
        # exists, so every lookup missed and every contribution silently
        # defaulted to 0.0. The waterfall then displayed a stored LLR of 20.50
        # above evidence rows summing to zero, on 13 of 14 links.
        by_id = {c.get("evidence_id"): c for c in result.contributions}
        for it in items:
            c = by_id.get(it.id, {})
            session.add(HypothesisEvidence(
                id=uuidv7_str(),
                hypothesis_id=hyp_id,
                evidence_id=it.id,
                family=it.family.value,
                raw_llr=round(float(c.get("raw_llr", it.get_effective_llr())), 4),
                contribution=round(float(c.get("llr_contrib", 0.0)), 4),
                reliability_weight=1.0,
                is_contradiction=it.is_contradiction,
            ))

    session.commit()
    print(f"[+] Committed {len(ACTORS)} actors, 7 onion services, 5 servers, "
          f"{len(LINK_EVIDENCE)} engine-scored hypotheses.")


def main():
    init_db_sync()
    session = SyncSessionLocal()
    try:
        if "--reset" in sys.argv:
            reset(session)
        if already_seeded(session):
            print("[!] Network already present. Use --reset to rebuild.")
        else:
            build(session)

        print("[+] Re-projecting graph...")
        counts = GraphProjectionService().rebuild_graph_from_postgres(session)
        print(f"[+] Projection: {counts}")

        total = session.query(Actor).count()
        print(f"[+] Done. {total} actors in the ledger.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
