from typing import Any, Dict


def normalize_study_assets_result(result: Any) -> Dict[str, Any]:
    """
    Normalize the complete L7 output.

    Ensures that quiz, timeline, and mind_map always exist
    in the expected format.
    """

    if not isinstance(result, dict):
        return default_study_assets_result()

    quiz = result.get("quiz", [])
    timeline = result.get("concept_timeline", [])
    mind_map = result.get("mind_map", {})

    result["quiz"] = validate_quiz(quiz)
    result["concept_timeline"] = validate_timeline(timeline)
    result["mind_map"] = validate_mind_map(mind_map)

    return result


def validate_quiz(quiz: Any) -> list:
    """
    Validate L7 quiz questions.

    Invalid questions are removed instead of allowing
    malformed LLM output to reach the application.
    """

    if not isinstance(quiz, list):
        return []

    valid_questions = []

    for question in quiz:
        if not isinstance(question, dict):
            continue

        question_text = question.get("question")
        options = question.get("options")
        answer = question.get("answer")
        explanation = question.get("explanation")

        if not isinstance(question_text, str) or not question_text.strip():
            continue

        if not isinstance(options, list):
            continue

        if len(options) < 2:
            continue

        if not all(isinstance(option, str) for option in options):
            continue

        if not isinstance(answer, str) or not answer.strip():
            continue

        if not isinstance(explanation, str):
            explanation = ""

        valid_questions.append(
            {
                "question": question_text.strip(),
                "options": options,
                "answer": answer.strip(),
                "explanation": explanation.strip(),
            }
        )

    return valid_questions


def validate_timeline(timeline: Any) -> list:
    """
    Validate concept timeline entries.
    """

    if not isinstance(timeline, list):
        return []

    valid_entries = []

    for item in timeline:
        if not isinstance(item, dict):
            continue

        concept = item.get("concept")
        start = item.get("start")
        end = item.get("end")

        if not isinstance(concept, str) or not concept.strip():
            continue

        if not isinstance(start, (int, float)):
            continue

        if not isinstance(end, (int, float)):
            continue

        if start < 0 or end < start:
            continue

        valid_entries.append(
            {
                "concept": concept.strip(),
                "start": start,
                "end": end,
            }
        )

    return valid_entries


def validate_mind_map(mind_map: Any) -> Dict[str, Any]:
    """
    Validate the L7 mind map.

    The mind map should contain nodes and edges.
    """

    if not isinstance(mind_map, dict):
        return {
            "root": "",
            "nodes": [],
            "edges": [],
        }

    root = mind_map.get("root", "")
    nodes = mind_map.get("nodes", [])
    edges = mind_map.get("edges", [])

    if not isinstance(root, str):
        root = ""

    if not isinstance(nodes, list):
        nodes = []

    if not isinstance(edges, list):
        edges = []

    valid_nodes = []

    for node in nodes:
        if not isinstance(node, dict):
            continue

        node_id = node.get("id")
        label = node.get("label")

        if not isinstance(node_id, str):
            continue

        if not isinstance(label, str) or not label.strip():
            continue

        valid_nodes.append(
            {
                "id": node_id,
                "label": label.strip(),
            }
        )

    valid_edges = []

    for edge in edges:
        if not isinstance(edge, dict):
            continue

        source = edge.get("from")
        target = edge.get("to")

        if not isinstance(source, str):
            continue

        if not isinstance(target, str):
            continue

        valid_edges.append(
            {
                "from": source,
                "to": target,
            }
        )

    return {
        "root": root,
        "nodes": valid_nodes,
        "edges": valid_edges,
    }


def default_study_assets_result() -> Dict[str, Any]:
    """
    Safe fallback returned when the complete L7 result
    is missing or invalid.
    """

    return {
        "quiz": [],
        "concept_timeline": [],
        "mind_map": {
            "root": "",
            "nodes": [],
            "edges": [],
        },
    }
