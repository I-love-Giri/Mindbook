def normalize_deep_dive_result(result: dict) -> dict:
    if not isinstance(result, dict):
        return _default_result()

    if not isinstance(result.get("blocks"), list):
        result["blocks"] = []

    if not isinstance(result.get("key_concepts"), list):
        result["key_concepts"] = []

    if not isinstance(result.get("sketch_note"), dict):
        result["sketch_note"] = {}

    difficulty = result.get("difficulty_rating", 3)

    if not isinstance(difficulty, int):
        difficulty = 3

    result["difficulty_rating"] = max(
        1,
        min(5, difficulty),
    )

    return result


def _default_result() -> dict:
    return {
        "blocks": [],
        "key_concepts": [],
        "sketch_note": {},
        "difficulty_rating": 3,
    }
