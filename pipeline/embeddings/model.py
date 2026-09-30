import torch
from sentence_transformers import SentenceTransformer


def create_embedding_model(
    model_name: str = "all-MiniLM-L6-v2",
) -> SentenceTransformer:

    device = "mps" if torch.backends.mps.is_available() else "cpu"

    return SentenceTransformer(
        model_name,
        device=device,
    )
