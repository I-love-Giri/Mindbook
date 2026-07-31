import re

class TranscriptCleaner:
    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""

        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text)

        # Collapse repeated punctuation
        text = re.sub(r"\.{2,}", ".", text)
        text = re.sub(r"!{2,}", "!", text)
        text = re.sub(r"\?{2,}", "?", text)

        # Normalize quotation marks
        text = (
            text.replace("“", '"')
                .replace("”", '"')
                .replace("’", "'")
                .replace("‘", "'")
        )

        return text.strip()