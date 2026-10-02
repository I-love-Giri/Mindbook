from typing import List, Dict

from google import genai
from sklearn.metrics.pairwise import cosine_similarity
from google.genai import types

from config.settings import GEMINI_API_KEY


class SemanticSplitter:

    def __init__(
        self,
        model=None,
        threshold: float = 0.55,
        min_words: int = 50,
    ):
        self.model = model or genai.Client(api_key=GEMINI_API_KEY)
        self.threshold = threshold
        self.min_words = min_words

    def split(self, sentences: List[Dict]):

        if not sentences:
            return []

        texts = [x["text"] for x in sentences]

        contents = [
            types.Content(parts=[types.Part.from_text(text=text)]) for text in texts
        ]

        result = self.model.models.embed_content(
            model="gemini-embedding-2",
            contents=contents,
        )

        embeddings = [embedding.values for embedding in result.embeddings]

        print("DEBUG sentences:", len(sentences))
        print("DEBUG embeddings:", len(embeddings))

        groups = []
        current = []
        current_words = 0

        for i, sentence in enumerate(sentences):

            should_split = False

            if i > 0:

                similarity = cosine_similarity(
                    [embeddings[i - 1]],
                    [embeddings[i]],
                )[
                    0
                ][0]

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
