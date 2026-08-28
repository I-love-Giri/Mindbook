from typing import Any, Dict


def _extract_section_text(section: Dict[str, Any], max_chars: int = 800) -> str:
    """
    Extract useful explanatory text from an L5 section.

    Prefers paragraph blocks but falls back to other textual blocks.
    """

    blocks = section.get("blocks") or []

    paragraph_parts = []

    for block in blocks:
        if not isinstance(block, dict):
            continue

        if block.get("type") != "paragraph":
            continue

        content = block.get("content", "")

        if content:
            paragraph_parts.append(str(content))

    text = " ".join(paragraph_parts).strip()

    if not text:
        fallback_parts = []

        for block in blocks:
            if not isinstance(block, dict):
                continue

            content = block.get("content", "")

            if content:
                fallback_parts.append(str(content))

        text = " ".join(fallback_parts).strip()

    return text[:max_chars]


def build_sections_context(
    sections: list,
    max_chars: int = 7000,
) -> str:
    """
    Build a compact representation of all L5 sections.

    Includes:
        - section number
        - title
        - timestamps
        - key concepts
        - section explanation
    """

    parts = []
    current_length = 0

    for index, section in enumerate(sections):

        title = section.get("title") or "Untitled Section"

        start = section.get("start", 0) or 0
        end = section.get("end", start) or start

        concepts = section.get("key_concepts") or []

        concepts_text = ", ".join(str(concept) for concept in concepts[:10] if concept)

        explanation = _extract_section_text(
            section,
            max_chars=700,
        )

        block = (
            f"SECTION {index + 1}\n"
            f"TITLE: {title}\n"
            f"TIMESTAMP: {float(start):.1f}s - {float(end):.1f}s\n"
            f"KEY CONCEPTS: {concepts_text or 'None'}\n"
            f"EXPLANATION: {explanation or 'None'}"
        )

        if current_length + len(block) > max_chars:
            break

        parts.append(block)
        current_length += len(block) + 2

    return "\n\n".join(parts)


# ============================================================
# L3 CONTEXT
# ============================================================


def build_dependency_context(kg: Dict[str, Any]) -> str:
    """
    Convert L3 dependency_order into readable concept names.
    """

    nodes = kg.get("nodes") or []

    node_lookup = {
        node.get("id"): node.get("label")
        for node in nodes
        if isinstance(node, dict) and node.get("id") and node.get("label")
    }

    dependency_order = kg.get("dependency_order") or []

    if not dependency_order:
        return "No meaningful dependency order was generated."

    lines = []

    for index, node_id in enumerate(dependency_order, start=1):

        label = node_lookup.get(node_id, node_id)

        lines.append(f"{index}. {label}")

    return "\n".join(lines)


def build_graph_context(kg: Dict[str, Any]) -> str:
    """
    Convert important L3 graph nodes into compact text.
    """

    nodes = kg.get("nodes") or []

    lines = []

    for node in nodes[:14]:

        if not isinstance(node, dict):
            continue

        node_id = node.get("id", "")
        label = node.get("label", "")
        node_type = node.get("type", "")
        level = node.get("level", "")

        if not label:
            continue

        lines.append(f"- {node_id}: {label} " f"(type={node_type}, level={level})")

    return "\n".join(lines)


# ============================================================
# L6 CONTEXT
# ============================================================


def build_key_terms_context(synthesis: Dict[str, Any]) -> str:
    """
    Build readable L6 key-term context.
    """

    terms = synthesis.get("key_terms") or []

    lines = []

    for term in terms[:15]:

        if not isinstance(term, dict):
            continue

        name = term.get("term", "")
        definition = term.get("definition", "")

        if not name:
            continue

        lines.append(f"- {name}: {definition}")

    return "\n".join(lines)


def build_flashcard_context(synthesis: Dict[str, Any]) -> str:
    """
    Build compact context from L6 flashcards.

    These are provided as semantic hints rather than copied directly
    into the final quiz.
    """

    flashcards = synthesis.get("flashcards") or []

    lines = []

    for card in flashcards[:10]:

        if not isinstance(card, dict):
            continue

        front = card.get("front", "")
        back = card.get("back", "")

        if not front:
            continue

        lines.append(f"- Q: {front}\n" f"  A: {back}")

    return "\n".join(lines)
