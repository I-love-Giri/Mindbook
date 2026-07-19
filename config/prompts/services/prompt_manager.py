from pathlib import Path

class PromptManager:

    def __init__(self, prompt_folder: str):
        self.prompt_folder = Path(prompt_folder)

    def get(self, name: str) -> str:
        path = self.prompt_folder / f"{name}.txt"

        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")

        return path.read_text(encoding="utf-8")
