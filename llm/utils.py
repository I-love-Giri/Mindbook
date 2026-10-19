import json
import re
from typing import Any


def clean_json_text(text: str) -> str:
    """
    Sanitize LLM output by removing reasoning tags (<think>...</think>),
    markdown code blocks (```json ... ```), and isolating the JSON payload.
    """
    if not text:
        return ""

    text = text.strip()

    # 1. Strip reasoning blocks like <think>...</think>
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. Extract code block content if markdown-fenced
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    else:
        # 3. Fallback: locate outermost { ... } or [ ... ]
        first_curly = text.find("{")
        last_curly = text.rfind("}")
        first_bracket = text.find("[")
        last_bracket = text.rfind("]")

        if first_curly != -1 and (first_bracket == -1 or first_curly < first_bracket):
            if last_curly != -1:
                text = text[first_curly : last_curly + 1]
        elif first_bracket != -1:
            if last_bracket != -1:
                text = text[first_bracket : last_bracket + 1]

    return text.strip()


def parse_json_safely(text: str) -> Any:
    """
    Attempts to parse text as JSON directly, and if that fails,
    applies clean_json_text before retrying.
    """
    if not text:
        raise ValueError("Cannot parse empty response as JSON.")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = clean_json_text(text)
        return json.loads(cleaned)
