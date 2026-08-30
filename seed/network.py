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

import random
import sys
from datetime import datetime, timedelta

from packages.evidence.uuid7 import uuidv7_str
from packages.graph.projection import GraphProjectionService
from apps.api.database.session import SyncSessionLocal, init_db_sync
from apps.api.database.models import (
    Actor, Alias, Account, PGPKey, Wallet, OnionService, Server, Hypothesis,
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

# (subject alias, object alias, calibrated probability, status)
# Intra-cluster links are strong; the two cross-cluster links are deliberately
# weak, so the review queue has something genuinely ambiguous in it.
HYPOTHESES = [
    ("NightHalo",   "LockJaw",     0.94, "ACCEPTED"),
    ("NightHalo",   "PaleCipher",  0.88, "ACCEPTED"),
    ("LockJaw",     "PaleCipher",  0.71, "PROPOSED"),

    ("VelvetForge", "AtlasKilo",   0.96, "ACCEPTED"),
    ("VelvetForge", "RedMeridian", 0.83, "PROPOSED"),
    ("AtlasKilo",   "RedMeridian", 0.62, "PROPOSED"),

    ("ObolBroker",  "TumblerFox",  0.91, "ACCEPTED"),

    ("GlassRelay",  "SableIndex",  0.89, "ACCEPTED"),
    ("GlassRelay",  "QuietLedger", 0.77, "PROPOSED"),
    ("SableIndex",  "QuietLedger", 0.55, "PROPOSED"),

    # The interesting ones: weak bridges between clusters.
    ("PaleCipher",  "ObolBroker",  0.48, "PROPOSED"),
    ("RedMeridian", "TumblerFox",  0.41, "PROPOSED"),
    ("QuietLedger", "IronVesper",  0.38, "INSUFFICIENT"),
]


def _b58(rng, n):
    return "".join(rng.choice("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz") for _ in range(n))


def _hex(rng, n):
    return "".join(rng.choice("0123456789ABCDEF") for _ in range(n))


def _onion(rng):
    return "".join(rng.choice("abcdefghijklmnopqrstuvwxyz234567") for _ in range(56)) + ".onion"


def already_seeded(session):
    return session.query(Actor).filter(Actor.primary_alias == "NightHalo").first() is not None


def reset(session):
    """Remove only what this module created. The hero scenario is left alone."""
    names = [a[1] for a in ACTORS]
    actors = session.query(Actor).filter(Actor.primary_alias.in_(names)).all()
    ids = [a.id for a in actors]
    if not ids:
        print("[!] Nothing to reset.")
        return
    session.query(Hypothesis).filter(
        Hypothesis.subject_entity_id.in_(ids) | Hypothesis.object_entity_id.in_(ids)
    ).delete(synchronize_session=False)
    for model in (Alias, Account, PGPKey, Wallet):
        session.query(model).filter(model.actor_id.in_(ids)).delete(synchronize_session=False)
    session.query(OnionService).filter(OnionService.title.like(f"%{MARK}%")).delete(synchronize_session=False)
    session.query(Server).filter(Server.provider.like(f"%{MARK}%")).delete(synchronize_session=False)
    session.query(Actor).filter(Actor.id.in_(ids)).delete(synchronize_session=False)
    session.commit()
    print(f"[+] Removed {len(ids)} synthetic network actors and their identifiers.")


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

    # Actor-to-actor attribution links.
    print(f"[+] Linking actors with {len(HYPOTHESES)} attribution hypotheses...")
    import math
    for subj, obj, prob, status in HYPOTHESES:
        if subj not in by_alias or obj not in by_alias:
            continue
        # Invert the sigmoid so raw_log_lr and calibrated_prob stay consistent
        # with what the engine would have produced (prior log-odds -2.0).
        llr = round(math.log(prob / (1 - prob)) + 2.0, 2)
        session.add(Hypothesis(
            id=uuidv7_str(),
            subject_entity_id=by_alias[subj][0],
            object_entity_id=by_alias[obj][0],
            raw_log_lr=llr,
            calibrated_prob=prob,
            status=status,
            model_version="v1.0-LLR",
            calibration_version="v1.0-Sigmoid",
            created_at=BASE - timedelta(days=rng.randint(1, 60)),
        ))

    session.commit()
    print(f"[+] Committed {len(ACTORS)} actors, 7 onion services, 5 servers, {len(HYPOTHESES)} hypotheses.")


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
