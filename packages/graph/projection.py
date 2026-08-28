"""
Neo4j Property Graph Projection Engine for NETRA-X
Provides asynchronous projection workers, Cypher query helpers, and full graph rebuild capability.
"""

import os
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.database.models import Actor, Alias, Account, PGPKey, Wallet, OnionService, Server, Hypothesis

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "netra_neo4j_pass")


class GraphProjectionService:
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver: Optional[Driver] = None

    def get_driver(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def close(self):
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def clear_database(self):
        """Drop all nodes and relationships in Neo4j."""
        driver = self.get_driver()
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def rebuild_graph_from_postgres(self, db_session: Session) -> Dict[str, int]:
        """
        Drop Neo4j graph and project complete knowledge graph directly from PostgreSQL authoritative ledger.
        """
        try:
            self.clear_database()
        except Exception:
            # If Neo4j is offline or unavailable during offline dev, handle gracefully
            return {"actors": 0, "aliases": 0, "pgp_keys": 0, "wallets": 0, "onion_services": 0, "edges": 0}

        driver = self.get_driver()
        counts = {"actors": 0, "aliases": 0, "pgp_keys": 0, "wallets": 0, "onion_services": 0, "edges": 0}

        with driver.session() as session:
            # 1. Project Actors
            actors = db_session.execute(select(Actor)).scalars().all()
            for actor in actors:
                session.run(
                    """
                    MERGE (a:Actor {id: $id})
                    SET a.primary_alias = $primary_alias,
                        a.category = $category,
                        a.confidence = $confidence,
                        a.is_synthetic = $is_synthetic
                    """,
                    id=actor.id,
                    primary_alias=actor.primary_alias,
                    category=actor.category,
                    confidence=actor.confidence,
                    is_synthetic=actor.is_synthetic
                )
                counts["actors"] += 1

            # 2. Project Aliases
            aliases = db_session.execute(select(Alias)).scalars().all()
            for alias in aliases:
                session.run(
                    """
                    MATCH (a:Actor {id: $actor_id})
                    MERGE (al:Alias {id: $id})
                    SET al.value = $value, al.platform = $platform
                    MERGE (a)-[r:ACTOR_USES_ALIAS]->(al)
                    SET r.confidence = $confidence, r.source = $source
                    """,
                    id=alias.id,
                    actor_id=alias.actor_id,
                    value=alias.value,
                    platform=alias.platform or "Unknown",
                    confidence=alias.confidence,
                    source=alias.source
                )
                counts["aliases"] += 1
                counts["edges"] += 1

            # 3. Project PGP Keys
            pgp_keys = db_session.execute(select(PGPKey)).scalars().all()
            for key in pgp_keys:
                session.run(
                    """
                    MERGE (k:PGPKey {id: $id})
                    SET k.fingerprint = $fingerprint, k.key_id = $key_id
                    """,
                    id=key.id,
                    fingerprint=key.fingerprint,
                    key_id=key.key_id
                )
                counts["pgp_keys"] += 1
                if key.actor_id:
                    session.run(
                        """
                        MATCH (a:Actor {id: $actor_id}), (k:PGPKey {id: $key_id})
                        MERGE (a)-[r:ACCOUNT_USES_PGP]->(k)
                        SET r.confidence = 0.99
                        """,
                        actor_id=key.actor_id,
                        key_id=key.id
                    )
                    counts["edges"] += 1

            # 4. Project Wallets
            wallets = db_session.execute(select(Wallet)).scalars().all()
            for w in wallets:
                session.run(
                    """
                    MERGE (w:Wallet {id: $id})
                    SET w.address = $address, w.chain = $chain, w.cluster_id = $cluster_id
                    """,
                    id=w.id,
                    address=w.address,
                    chain=w.chain,
                    cluster_id=w.cluster_id or "Unclustered"
                )
                counts["wallets"] += 1
                if w.actor_id:
                    session.run(
                        """
                        MATCH (a:Actor {id: $actor_id}), (w:Wallet {id: $wallet_id})
                        MERGE (a)-[r:ACCOUNT_USES_WALLET]->(w)
                        SET r.confidence = 0.90
                        """,
                        actor_id=w.actor_id,
                        wallet_id=w.id
                    )
                    counts["edges"] += 1

            # 5. Project Onion Services & Infrastructure
            onions = db_session.execute(select(OnionService)).scalars().all()
            for onion in onions:
                session.run(
                    """
                    MERGE (o:OnionService {id: $id})
                    SET o.onion_address = $address, o.title = $title, o.favicon_mmh3 = $favicon
                    """,
                    id=onion.id,
                    address=onion.onion_address,
                    title=onion.title or "Onion Service",
                    favicon=onion.favicon_mmh3 or 0
                )
                counts["onion_services"] += 1

            # 6. Project Hypotheses (Actor to Actor linkages)
            hypotheses = db_session.execute(select(Hypothesis)).scalars().all()
            for h in hypotheses:
                session.run(
                    """
                    MATCH (a1:Actor {id: $subj}), (a2:Actor {id: $obj})
                    MERGE (a1)-[r:ACTOR_POSSIBLY_SAME_AS_ACTOR]->(a2)
                    SET r.calibrated_prob = $prob, r.status = $status, r.hypothesis_id = $id
                    """,
                    subj=h.subject_entity_id,
                    obj=h.object_entity_id,
                    prob=h.calibrated_prob,
                    status=h.status,
                    id=h.id
                )
                counts["edges"] += 1

        return counts

    def fetch_actor_subgraph(self, actor_id: str) -> Dict[str, Any]:
        """Fetch network subgraph for Cytoscape.js visualization."""
        try:
            driver = self.get_driver()
            nodes: List[Dict] = []
            edges: List[Dict] = []

            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (a:Actor {id: $actor_id})-[r]-(n)
                    RETURN a, r, n LIMIT 50
                    """,
                    actor_id=actor_id
                )
                seen_nodes = set()
                for record in result:
                    a = record["a"]
                    r = record["r"]
                    n = record["n"]

                    if a.element_id not in seen_nodes:
                        nodes.append({
                            "id": a["id"],
                            "label": a.get("primary_alias", "Actor"),
                            "type": "Actor"
                        })
                        seen_nodes.add(a.element_id)

                    node_type = list(n.labels)[0] if n.labels else "Entity"
                    node_label = n.get("value") or n.get("primary_alias") or n.get("address") or n.get("fingerprint") or n.get("onion_address") or n.get("id")
                    if n.element_id not in seen_nodes:
                        nodes.append({
                            "id": n["id"],
                            "label": str(node_label),
                            "type": node_type
                        })
                        seen_nodes.add(n.element_id)

                    edges.append({
                        "id": f"{r.type}_{a['id']}_{n['id']}",
                        "source": a["id"],
                        "target": n["id"],
                        "label": r.type,
                        "confidence": r.get("confidence", 0.9)
                    })

            return {"nodes": nodes, "edges": edges}
        except Exception:
            # Fallback if Neo4j is offline or not installed
            return {"nodes": [], "edges": []}
