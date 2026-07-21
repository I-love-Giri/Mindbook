from pathlib import Path

class PromptManager:

    def __init__(self, prompt_folder: str):
        self.prompt_folder = Path(prompt_folder)

    def get(self, name: str) -> str:
        path = self.prompt_folder / f"{name}.txt"

        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")

        return path.read_text(encoding="utf-8")


'''
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

'''

'''
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

'''