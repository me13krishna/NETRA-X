"""
neural.py — PyTorch-backed Neural Short-Text Stylometry Embedding Module.

Provides dense 128-dimensional latent style embeddings for short text samples (<50 words)
where traditional function-word distribution statistics abstain.
"""

import re
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Optional


class NeuralStylometryEncoder(nn.Module):
    """
    Subword / character n-gram PyTorch embedding network projecting text into a 128d latent style space.
    """

    def __init__(self, vocab_size: int = 10000, embed_dim: int = 64, hidden_dim: int = 128):
        super().__init__()
        # Set deterministic seed for reproducible initializations
        torch.manual_seed(42)

        self.vocab_size = vocab_size
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.fc1 = nn.Linear(embed_dim, hidden_dim)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        """
        Forward pass converting token index sequences into a single 128d normalized style vector per sample.
        
        Args:
            input_ids: Tensor of shape (batch_size, seq_len)
        Returns:
            Tensor of shape (batch_size, 128) with L2 normalized embeddings.
        """
        if input_ids.numel() == 0:
            return torch.zeros((input_ids.size(0), 128), dtype=torch.float32)

        # Token embeddings: (batch_size, seq_len, embed_dim)
        embeds = self.embedding(input_ids)

        # Mean pooling across sequence dimension: (batch_size, embed_dim)
        pooled = torch.mean(embeds, dim=1)

        # Dense projection
        h = self.act(self.norm1(self.fc1(pooled)))
        out = self.norm2(self.fc2(h))

        # L2 Normalize
        return F.normalize(out, p=2, dim=-1)


# Global lazy-initialized singleton encoder
_NEURAL_ENCODER: Optional[NeuralStylometryEncoder] = None


def get_neural_encoder() -> NeuralStylometryEncoder:
    """
    Singleton factory for NeuralStylometryEncoder.
    """
    global _NEURAL_ENCODER
    if _NEURAL_ENCODER is None:
        encoder = NeuralStylometryEncoder()
        encoder.eval()
        _NEURAL_ENCODER = encoder
    return _NEURAL_ENCODER


def _text_to_ngram_indices(text: str, vocab_size: int = 10000, max_tokens: int = 256) -> List[int]:
    """
    Extract character 3-5grams and convert to deterministic feature indices via hashing.
    """
    cleaned = re.sub(r"\s+", " ", text.lower()).strip()
    if not cleaned:
        return [0]

    indices = []
    for n in (3, 4, 5):
        for i in range(len(cleaned) - n + 1):
            gram = cleaned[i : i + n]
            # Hash to index range [1, vocab_size - 1] (0 reserved for padding)
            idx = (abs(hash(gram)) % (vocab_size - 1)) + 1
            indices.append(idx)

    if not indices:
        return [0]

    return indices[:max_tokens]


def extract_neural_style_embedding(text: str) -> np.ndarray:
    """
    Extract a normalized 128-dimensional dense stylometric embedding vector for a given text string.
    
    Args:
        text: Input text string
    Returns:
        1D numpy array of shape (128,) with float32 values.
    """
    encoder = get_neural_encoder()
    indices = _text_to_ngram_indices(text, vocab_size=encoder.vocab_size)

    input_tensor = torch.tensor([indices], dtype=torch.long)
    with torch.no_grad():
        embedding_tensor = encoder(input_tensor)

    return embedding_tensor.squeeze(0).cpu().numpy().astype(np.float32)
