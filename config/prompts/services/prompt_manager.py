import json
from pathlib import Path


class PromptManager:
    """
    Loads raw prompt files from disk.

    Two access modes:
      - load(name): returns raw text, used for Template-based prompts
        that contain ${placeholder} substitutions (chunk_summary,
        section_analysis, chapter_summary, video_summary,
        domain_classifier, grounding_checker, key_concepts).
      - load_json(name): parses the file as JSON, used for structured
        config-style files with no substitution needed (educator).
    """

    def __init__(self, base_path="config/prompts"):
        self.base_path = Path(base_path)

    def load(self, name: str) -> str:
        path = self.base_path / f"{name}.txt"

        if not path.exists():
            raise FileNotFoundError(f"Missing prompt: {path}")

        return path.read_text(encoding="utf-8")

    def load_json(self, name: str) -> dict:
        raw = self.load(name)

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Prompt file '{name}.txt' is not valid JSON: {exc}"
            ) from exc


"""
summary.txt

You are an expert at summarizing YouTube transcripts.

Instructions:

- Do NOT skip important information.
- Preserve all key facts.
- Ignore filler words.
- Keep technical terms.
- Produce a clear summary.
- Use multiple paragraphs.

Transcript:

$transcript

"""

"""
combine_summary.txt

Below are summaries of different parts of the same YouTube video.

Merge them into one coherent summary.

Rules:

- Remove repetition.
- Preserve all important facts.
- Keep the logical flow.
- Produce a readable final summary.

Summaries:

$summaries

"""
