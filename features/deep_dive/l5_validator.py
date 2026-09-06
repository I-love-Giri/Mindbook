# from typing import Any


def _default_result() -> dict:
    return {
        "blocks": [],
        "key_concepts": [],
        "sketch_note": {},
        "difficulty_rating": 3,
    }


def _normalize_single_result(result: dict) -> dict:
    if not isinstance(result, dict):
        return _default_result()

    normalized = {
        "blocks": (
            result.get("blocks") if isinstance(result.get("blocks"), list) else []
        ),
        "key_concepts": (
            result.get("key_concepts")
            if isinstance(result.get("key_concepts"), list)
            else []
        ),
        "sketch_note": (
            result.get("sketch_note")
            if isinstance(result.get("sketch_note"), dict)
            else {}
        ),
        "difficulty_rating": 3,
    }

    difficulty = result.get("difficulty_rating", 3)

    if isinstance(difficulty, int):
        normalized["difficulty_rating"] = max(
            1,
            min(5, difficulty),
        )

    return normalized


def normalize_deep_dive_result(result: dict) -> list[dict]:
    if not isinstance(result, dict):
        return []

    raw_results = result.get("results")

    if not isinstance(raw_results, list):
        return []

    normalized_results = []

    for item in raw_results:
        if not isinstance(item, dict):
            continue

        chunk_id = item.get("chunk_id")

        # chunk_id 0 is valid, so don't use: if not chunk_id
        if chunk_id is None:
            continue

        normalized_results.append(
            {
                "chunk_id": chunk_id,
                "result": _normalize_single_result(item),
            }
        )

    return normalized_results
