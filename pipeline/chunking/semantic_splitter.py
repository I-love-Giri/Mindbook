from typing import List, Dict

import torch
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticSplitter:

    def __init__(
        self, model_name="Qwen/Qwen3-Embedding-0.6B", threshold=0.55, min_words=50
    ):

        device = "mps" if torch.backends.mps.is_available() else "cpu"

        self.model = SentenceTransformer(model_name, device=device)

        self.threshold = threshold
        self.min_words = min_words

    def split(self, sentences: List[Dict]):

        if not sentences:
            return []

        texts = [x["text"] for x in sentences]

        embeddings = self.model.encode(texts, batch_size=8, normalize_embeddings=True)

        groups = []

        current = []

        current_words = 0

        for i, sentence in enumerate(sentences):

            should_split = False

            if i > 0:

                similarity = cosine_similarity([embeddings[i - 1]], [embeddings[i]])[0][
                    0
                ]

                if similarity < self.threshold and current_words >= self.min_words:
                    should_split = True

            if should_split:

                groups.append(current)

                current = []

                current_words = 0

            current.append(sentence)

            current_words += sentence["words"]

        if current:

            groups.append(current)

        return groups
