from typing import Any, Dict

"""def normalize_study_assets_result(result: Any) -> Dict[str, Any]:
    ""
    Normalize the complete L7 output.

    Ensures that quiz, timeline, and mind_map always exist
    in the expected format.
    ""

    if not isinstance(result, dict):
        return default_study_assets_result()

    quiz = result.get("quiz", [])
    timeline = result.get("concept_timeline", [])
    mind_map = result.get("mind_map", {})

    result["quiz"] = validate_quiz(quiz)
    result["concept_timeline"] = validate_timeline(timeline)
    result["mind_map"] = validate_mind_map(mind_map)

    return result"""


from typing import Any, Dict

# ============================================================
# DEFAULT RESULT
# ============================================================


def default_study_assets_result() -> Dict[str, Any]:
    """
    Safe fallback returned when the complete L7 result
    is missing or invalid.

    This schema matches the current L7 prompt output.
    """

    return {
        "quiz": [],
        "concept_timeline": [],
        "mind_map_text": "",
    }


# ============================================================
# MAIN NORMALIZER
# ============================================================


def normalize_study_assets_result(
    result: Any,
) -> Dict[str, Any]:
    """
    Normalize and validate the complete L7 study-assets result.

    Expected L7 schema:

    {
        "quiz": [...],
        "concept_timeline": [...],
        "mind_map_text": "..."
    }
    """

    if not isinstance(result, dict):
        return default_study_assets_result()

    return {
        "quiz": validate_quiz(result.get("quiz", [])),
        "concept_timeline": validate_timeline(result.get("concept_timeline", [])),
        "mind_map_text": validate_mind_map_text(result.get("mind_map_text", "")),
    }


# ============================================================
# QUIZ VALIDATION
# ============================================================


def validate_quiz(
    quiz: Any,
) -> list:
    """
    Validate L7 quiz questions.

    Expected question schema:

    {
        "question": "...",
        "options": [
            "A) ...",
            "B) ...",
            "C) ...",
            "D) ..."
        ],
        "correct": "A",
        "explanation": "...",
        "difficulty": "beginner",
        "section_ref": 0
    }

    Invalid questions are removed instead of allowing
    malformed LLM output to reach the application.
    """

    if not isinstance(quiz, list):
        return []

    valid_questions = []

    for question in quiz:

        # ----------------------------------------------------
        # Basic object validation
        # ----------------------------------------------------

        if not isinstance(question, dict):
            continue

        # ----------------------------------------------------
        # Extract fields
        # ----------------------------------------------------

        question_text = question.get("question")

        options = question.get("options")

        correct = question.get("correct")

        explanation = question.get(
            "explanation",
            "",
        )

        difficulty = question.get(
            "difficulty",
            "intermediate",
        )

        section_ref = question.get(
            "section_ref",
            0,
        )

        # ----------------------------------------------------
        # Question text
        # ----------------------------------------------------

        if not isinstance(
            question_text,
            str,
        ):
            continue

        question_text = question_text.strip()

        if not question_text:
            continue

        # ----------------------------------------------------
        # Options
        # ----------------------------------------------------

        if not isinstance(
            options,
            list,
        ):
            continue

        # L7 prompt explicitly requires exactly 4 options.
        if len(options) != 4:
            continue

        if not all(isinstance(option, str) for option in options):
            continue

        cleaned_options = [option.strip() for option in options]

        # No empty options
        if not all(cleaned_options):
            continue

        # ----------------------------------------------------
        # Correct answer
        # ----------------------------------------------------

        if not isinstance(
            correct,
            str,
        ):
            continue

        correct = correct.strip().upper()

        if correct not in {
            "A",
            "B",
            "C",
            "D",
        }:
            continue

        # ----------------------------------------------------
        # Explanation
        # ----------------------------------------------------

        if not isinstance(
            explanation,
            str,
        ):
            explanation = ""

        explanation = explanation.strip()

        # ----------------------------------------------------
        # Difficulty
        # ----------------------------------------------------

        if not isinstance(
            difficulty,
            str,
        ):
            difficulty = "intermediate"

        difficulty = difficulty.strip().lower()

        if difficulty not in {
            "beginner",
            "intermediate",
            "advanced",
        }:
            difficulty = "intermediate"

        # ----------------------------------------------------
        # Section reference
        # ----------------------------------------------------

        if not isinstance(
            section_ref,
            (int, float),
        ):
            section_ref = 0

        if section_ref < 0:
            section_ref = 0

        # ----------------------------------------------------
        # Normalized question
        # ----------------------------------------------------

        valid_questions.append(
            {
                "question": question_text,
                "options": cleaned_options,
                "correct": correct,
                "explanation": explanation,
                "difficulty": difficulty,
                "section_ref": section_ref,
            }
        )

    return valid_questions


# ============================================================
# TIMELINE VALIDATION
# ============================================================


def validate_timeline(
    timeline: Any,
) -> list:
    """
    Validate L7 concept timeline entries.

    Expected schema:

    {
        "timestamp": 0,
        "concept": "Concept introduced",
        "importance": "high"
    }

    The timeline is sorted chronologically.
    """

    if not isinstance(
        timeline,
        list,
    ):
        return []

    valid_entries = []

    for item in timeline:

        # ----------------------------------------------------
        # Basic object validation
        # ----------------------------------------------------

        if not isinstance(
            item,
            dict,
        ):
            continue

        # ----------------------------------------------------
        # Extract fields
        # ----------------------------------------------------

        timestamp = item.get("timestamp")

        concept = item.get("concept")

        importance = item.get(
            "importance",
            "medium",
        )

        # ----------------------------------------------------
        # Timestamp
        # ----------------------------------------------------

        if not isinstance(
            timestamp,
            (int, float),
        ):
            continue

        if timestamp < 0:
            continue

        # ----------------------------------------------------
        # Concept
        # ----------------------------------------------------

        if not isinstance(
            concept,
            str,
        ):
            continue

        concept = concept.strip()

        if not concept:
            continue

        # ----------------------------------------------------
        # Importance
        # ----------------------------------------------------

        if not isinstance(
            importance,
            str,
        ):
            importance = "medium"

        importance = importance.strip().lower()

        if importance not in {
            "high",
            "medium",
            "low",
        }:
            importance = "medium"

        # ----------------------------------------------------
        # Normalized entry
        # ----------------------------------------------------

        valid_entries.append(
            {
                "timestamp": timestamp,
                "concept": concept,
                "importance": importance,
            }
        )

    # --------------------------------------------------------
    # Chronological order
    # --------------------------------------------------------

    valid_entries.sort(key=lambda item: item["timestamp"])

    return valid_entries


# ============================================================
# MIND MAP TEXT VALIDATION
# ============================================================


def validate_mind_map_text(
    value: Any,
) -> str:
    """
    Validate the text-based L7 mind map.

    The current L7 prompt generates only `mind_map_text`,
    not a structured `mind_map` object.
    """

    if not isinstance(
        value,
        str,
    ):
        return ""

    return value.strip()


# ============================================================
# OPTIONAL STRUCTURED MIND MAP VALIDATION
# ============================================================


def validate_mind_map(
    mind_map: Any,
) -> Dict[str, Any]:
    """
    Validate a structured mind map if one is supplied.

    This is kept for compatibility with future L7 versions
    that may generate:

    {
        "root": "...",
        "nodes": [...],
        "edges": [...]
    }

    NOTE:
    The current L7 prompt does NOT request this field.
    """

    if not isinstance(
        mind_map,
        dict,
    ):
        return {
            "root": "",
            "nodes": [],
            "edges": [],
        }

    # --------------------------------------------------------
    # Root
    # --------------------------------------------------------

    root = mind_map.get(
        "root",
        "",
    )

    if not isinstance(
        root,
        str,
    ):
        root = ""

    root = root.strip()

    # --------------------------------------------------------
    # Nodes
    # --------------------------------------------------------

    nodes = mind_map.get(
        "nodes",
        [],
    )

    if not isinstance(
        nodes,
        list,
    ):
        nodes = []

    valid_nodes = []

    for node in nodes:

        if not isinstance(
            node,
            dict,
        ):
            continue

        node_id = node.get("id")

        label = node.get("label")

        if not isinstance(
            node_id,
            str,
        ):
            continue

        if not isinstance(
            label,
            str,
        ):
            continue

        node_id = node_id.strip()
        label = label.strip()

        if not node_id:
            continue

        if not label:
            continue

        valid_nodes.append(
            {
                "id": node_id,
                "label": label,
            }
        )

    # --------------------------------------------------------
    # Edges
    # --------------------------------------------------------

    edges = mind_map.get(
        "edges",
        [],
    )

    if not isinstance(
        edges,
        list,
    ):
        edges = []

    valid_edges = []

    for edge in edges:

        if not isinstance(
            edge,
            dict,
        ):
            continue

        source = edge.get("from")

        target = edge.get("to")

        if not isinstance(
            source,
            str,
        ):
            continue

        if not isinstance(
            target,
            str,
        ):
            continue

        source = source.strip()
        target = target.strip()

        if not source:
            continue

        if not target:
            continue

        valid_edges.append(
            {
                "from": source,
                "to": target,
            }
        )

    # --------------------------------------------------------
    # Final structured mind map
    # --------------------------------------------------------

    return {
        "root": root,
        "nodes": valid_nodes,
        "edges": valid_edges,
    }
