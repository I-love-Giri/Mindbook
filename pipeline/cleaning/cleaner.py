import re
import html


class TranscriptCleaner:

    @staticmethod
    def clean(text: str) -> str:

        if not text:
            return ""

        # Decode HTML entities
        text = html.unescape(text)


        # Normalize quotes
        text = (
            text.replace("“", '"')
                .replace("”", '"')
                .replace("’", "'")
                .replace("‘", "'")
        )


        # Normalize dashes
        text = (
            text.replace("–", "-")
                .replace("—", "-")
        )


        # Remove common transcript noise
        text = re.sub(
            r"\[(.*?)\]",
            "",
            text
        )


        # Remove excessive punctuation
        text = re.sub(
            r"\.{2,}",
            ".",
            text
        )

        text = re.sub(
            r"!{2,}",
            "!",
            text
        )

        text = re.sub(
            r"\?{2,}",
            "?",
            text
        )


        # Collapse whitespace
        text = re.sub(
            r"\s+",
            " ",
            text
        )


        return text.strip()
