"""
graph_embedding.py — PyTorch Node2Vec Graph Embedding & Topological Link Prediction Module.

Projects darknet CTI identity graph nodes (Actors, Aliases, Wallets, Favicons, PGP Keys) into
a 64-dimensional latent embedding space using biased random-walk sampling and Skip-Gram neural training,
enabling link prediction scoring for unlinked threat actor pairs.
"""

import math
import random
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Set

from packages.common.types import EvidenceItem, EvidenceFamily


class GraphSkipGramModel(nn.Module):
    """
    PyTorch Skip-Gram neural network for graph node representation learning.
    """

    def __init__(self, num_nodes: int, embed_dim: int = 64):
        super().__init__()
        torch.manual_seed(42)
        self.target_embeds = nn.Embedding(num_nodes, embed_dim)
        self.context_embeds = nn.Embedding(num_nodes, embed_dim)

        nn.init.uniform_(self.target_embeds.weight, -0.5 / embed_dim, 0.5 / embed_dim)
        nn.init.uniform_(self.context_embeds.weight, -0.5 / embed_dim, 0.5 / embed_dim)

    def forward(self, target_ids: torch.Tensor, context_ids: torch.Tensor) -> torch.Tensor:
        """
        Forward pass computing dot product similarity between target and context nodes.
        """
        t_emb = self.target_embeds(target_ids)
        c_emb = self.context_embeds(context_ids)
        dot_prods = torch.sum(t_emb * c_emb, dim=-1)
        return torch.sigmoid(dot_prods)

    def get_normalized_embeddings(self) -> torch.Tensor:
        """
        Returns L2-normalized target node embedding matrix.
        """
        return F.normalize(self.target_embeds.weight, p=2, dim=-1)


class Node2VecGraphEmbedder:
    """
    Node2Vec random walk generator and graph embedding trainer.
    """

    def __init__(self, embed_dim: int = 64, seed: int = 42):
        self.embed_dim = embed_dim
        self.seed = seed

    def generate_random_walks(
        self,
        adjacency_dict: Dict[str, List[str]],
        num_walks: int = 10,
        walk_length: int = 20,
        p: float = 1.0,
        q: float = 1.0,
    ) -> List[List[str]]:
        """
        Generates biased Node2Vec random walks over node adjacency connections.
        
        Args:
            adjacency_dict: Dict mapping node_id to list of connected neighbor node_ids.
            num_walks: Number of random walks per node.
            walk_length: Number of nodes per random walk sequence.
            p: Return parameter (higher p discourages immediate backtracking).
            q: In-out parameter (higher q favors local BFS exploration).
        """
        rng = random.Random(self.seed)
        nodes = sorted(list(adjacency_dict.keys()))
        if not nodes:
            return []

        walks: List[List[str]] = []

        for _ in range(num_walks):
            rng.shuffle(nodes)
            for start_node in nodes:
                walk = [start_node]
                while len(walk) < walk_length:
                    curr_node = walk[-1]
                    neighbors = adjacency_dict.get(curr_node, [])
                    if not neighbors:
                        break

                    if len(walk) == 1:
                        # First step: uniform choice over neighbors
                        next_node = rng.choice(neighbors)
                    else:
                        prev_node = walk[-2]
                        prev_neighbors = set(adjacency_dict.get(prev_node, []))

                        # Calculate Node2Vec transition unnormalized probabilities
                        weights = []
                        for nbr in neighbors:
                            if nbr == prev_node:
                                unnorm_p = 1.0 / p
                            elif nbr in prev_neighbors:
                                unnorm_p = 1.0
                            else:
                                unnorm_p = 1.0 / q
                            weights.append(unnorm_p)

                        total_w = sum(weights)
                        norm_weights = [w / total_w for w in weights]

                        # Sample next node using weighted choice
                        next_node = rng.choices(neighbors, weights=norm_weights, k=1)[0]

                    walk.append(next_node)
                walks.append(walk)

        return walks

    def fit_embeddings(
        self,
        adjacency_dict: Dict[str, List[str]],
        epochs: int = 5,
        lr: float = 0.01,
        window_size: int = 3,
    ) -> Dict[str, np.ndarray]:
        """
        Trains Skip-Gram graph embedding neural model over generated random walks.
        Returns Dict mapping node_id to 64d L2-normalized float32 numpy vector.
        """
        nodes = sorted(list(adjacency_dict.keys()))
        if not nodes:
            return {}

        node_to_idx = {node_id: idx for idx, node_id in enumerate(nodes)}
        idx_to_node = {idx: node_id for node_id, idx in node_to_idx.items()}
        num_nodes = len(nodes)

        walks = self.generate_random_walks(adjacency_dict, num_walks=10, walk_length=20)

        # Build Skip-Gram positive training pairs
        targets: List[int] = []
        contexts: List[int] = []

        for walk in walks:
            w_indices = [node_to_idx[n] for n in walk if n in node_to_idx]
            for i, target in enumerate(w_indices):
                start = max(0, i - window_size)
                end = min(len(w_indices), i + window_size + 1)
                for j in range(start, end):
                    if i != j:
                        targets.append(target)
                        contexts.append(w_indices[j])

        if not targets:
            # Fallback uniform deterministic embeddings
            rng = np.random.RandomState(self.seed)
            raw = rng.randn(num_nodes, self.embed_dim).astype(np.float32)
            norms = np.linalg.norm(raw, axis=1, keepdims=True)
            normed = raw / np.maximum(norms, 1e-12)
            return {node_id: normed[idx] for node_id, idx in node_to_idx.items()}

        target_tensor = torch.tensor(targets, dtype=torch.long)
        context_tensor = torch.tensor(contexts, dtype=torch.long)
        labels_tensor = torch.ones(len(targets), dtype=torch.float32)

        model = GraphSkipGramModel(num_nodes=num_nodes, embed_dim=self.embed_dim)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.BCELoss()

        model.train()
        for _ in range(epochs):
            optimizer.zero_grad()
            preds = model(target_tensor, context_tensor)
            loss = criterion(preds, labels_tensor)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            norm_matrix = model.get_normalized_embeddings().cpu().numpy().astype(np.float32)

        return {node_id: norm_matrix[idx] for node_id, idx in node_to_idx.items()}


class LinkPredictor:
    """
    Topological link predictor for unlinked identity graph nodes.
    """

    @staticmethod
    def predict_link_score(emb_a: np.ndarray, emb_b: np.ndarray) -> Dict[str, Any]:
        """
        Computes cosine similarity, Hadamard product norm, Euclidean distance, and link probability.
        """
        norm_a = np.linalg.norm(emb_a)
        norm_b = np.linalg.norm(emb_b)

        if norm_a == 0.0 or norm_b == 0.0 or len(emb_a) != len(emb_b):
            return {
                "cosine_similarity": 0.0,
                "euclidean_distance": 2.0,
                "link_probability": 0.50,
                "topological_link_detected": False,
            }

        cos_sim = float(np.dot(emb_a, emb_b) / (norm_a * norm_b))
        euc_dist = float(np.linalg.norm(emb_a - emb_b))
        link_prob = max(0.0, min(1.0, (cos_sim + 1.0) / 2.0))

        return {
            "cosine_similarity": round(cos_sim, 4),
            "euclidean_distance": round(euc_dist, 4),
            "link_probability": round(link_prob, 4),
            "topological_link_detected": cos_sim >= 0.70,
        }

    @staticmethod
    def evaluate_graph_link(
        node_id_a: str,
        node_id_b: str,
        embedding_dict: Dict[str, np.ndarray],
        item_id: str = "graph_link_1",
    ) -> EvidenceItem:
        """
        Evaluates graph link prediction score and outputs a calibrated EvidenceItem for Bayesian Evidence Fusion.
        """
        emb_a = embedding_dict.get(node_id_a)
        emb_b = embedding_dict.get(node_id_b)

        if emb_a is None or emb_b is None:
            return EvidenceItem(
                id=item_id,
                feature_name="graph_topological_distance",
                family=EvidenceFamily.INFRASTRUCTURE,
                dependence_group="graph_topology",
                m_i=0.80,
                u_i=0.10,
                llr=0.0,
                abstain=True,
                metadata={"reason": "Missing node embedding in topological graph dictionary"},
            )

        pred = LinkPredictor.predict_link_score(emb_a, emb_b)
        cos_sim = pred["cosine_similarity"]

        # Convert cosine similarity into likelihood ratio priors
        if cos_sim >= 0.85:
            m_i, u_i = 0.90, 0.005
        elif cos_sim >= 0.65:
            m_i, u_i = 0.75, 0.05
        else:
            m_i, u_i = 0.20, 0.40

        return EvidenceItem(
            id=item_id,
            feature_name="graph_topological_distance",
            family=EvidenceFamily.INFRASTRUCTURE,
            dependence_group="graph_topology",
            m_i=m_i,
            u_i=u_i,
            abstain=False,
            metadata={
                "node_id_a": node_id_a,
                "node_id_b": node_id_b,
                "cosine_similarity": cos_sim,
                "link_probability": pred["link_probability"],
                "euclidean_distance": pred["euclidean_distance"],
            },
        )


def fit_graph_embeddings(
    adjacency_dict: Dict[str, List[str]], embed_dim: int = 64, epochs: int = 5, seed: int = 42
) -> Dict[str, np.ndarray]:
    """
    Helper function to fit Node2Vec graph embeddings over node adjacency connections.
    """
    embedder = Node2VecGraphEmbedder(embed_dim=embed_dim, seed=seed)
    return embedder.fit_embeddings(adjacency_dict, epochs=epochs)


def evaluate_graph_link(
    node_id_a: str, node_id_b: str, embedding_dict: Dict[str, np.ndarray], item_id: str = "graph_link_1"
) -> EvidenceItem:
    """
    Helper function to evaluate graph link topological similarity and emit an EvidenceItem.
    """
    return LinkPredictor.evaluate_graph_link(node_id_a, node_id_b, embedding_dict, item_id=item_id)
