def normalize_synthesis_result(result: dict) -> dict:
    if not isinstance(result, dict):
        return default_synthesis_result()

    result.setdefault("complete_guide", "")
    result.setdefault("executive_summary", "")
    result.setdefault("faq", [])
    result.setdefault("gaps", "")
    result.setdefault("related_concepts", [])
    result.setdefault("next_steps", [])
    result.setdefault("flashcards", [])
    result.setdefault("key_terms", [])
    result.setdefault("difficulty_progression", [])

    return result


def default_synthesis_result() -> dict:
    return {
        "complete_guide": "",
        "executive_summary": "",
        "faq": [],
        "gaps": "",
        "related_concepts": [],
        "next_steps": [],
        "flashcards": [],
        "key_terms": [],
        "difficulty_progression": [],
    }
