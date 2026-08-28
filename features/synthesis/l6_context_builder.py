def section_explanation(section: dict, max_chars: int = 500) -> str:
    """
    Extract a compact explanation from an L5 section.

    L5 currently stores explanations inside paragraph blocks rather
    than using a dedicated 'explanation' field.


                 section mila
                  │
                  ▼
       "explanation" key hai?
             /          \
           YES           NO
            │             │
            ▼             ▼
    explanation return   blocks dekho
                          │
                          ▼
                  sirf paragraphs lo
                          │
                          ▼
                  paragraphs join karo
                          │
                          ▼
                    max 500 chars
                          │
                          ▼
                       return
    """

    explanation = section.get("explanation")

    if explanation:
        return str(explanation)[:max_chars]

    paragraphs = []

    for block in section.get("blocks", []):
        if block.get("type") == "paragraph":
            content = block.get("content", "")

            if content:
                paragraphs.append(content)

    return " ".join(paragraphs)[:max_chars]


def build_sections_text(
    sections: list,
    max_chars_per_section: int = 500,
) -> str:
    """
    Build a compact representation of all L5 sections.

    Keeps section boundaries and timestamps so L6 can cite the
    originating section.
    """

    parts = []

    for index, section in enumerate(sections):

        title = (
            section.get("title")
            or section.get("section_title")
            or f"Section {index + 1}"
        )

        start = section.get("start", 0)

        explanation = section_explanation(
            section,
            max_chars=max_chars_per_section,
        )

        concepts = section.get("key_concepts", [])

        concepts_text = ", ".join(str(concept) for concept in concepts[:10] if concept)

        parts.append(
            f"[SECTION {index + 1}]\n"
            f"TITLE: {title}\n"
            f"START: {float(start):.0f}s\n"
            f"EXPLANATION: {explanation}\n"
            f"KEY CONCEPTS: {concepts_text}"
        )

    return "\n\n".join(parts)


def build_entities_text(parsed: dict) -> str:
    """
    Build compact entity context from L2.
    """

    entities = parsed.get("key_entities", [])

    return ", ".join(
        f"{entity.get('name', '')} " f"({entity.get('type', 'concept')})"
        for entity in entities[:20]
        if entity.get("name")
    )


def build_concepts_text(
    parsed: dict,
    kg: dict,
) -> str:
    """
    Combine L2 topics and L3 graph nodes into a compact
    conceptual representation.
    """

    topics = parsed.get("topics", [])

    topic_lines = [
        f"- {topic.get('title', '')}: {topic.get('summary', '')}"
        for topic in topics[:15]
        if topic.get("title")
    ]

    nodes = kg.get("nodes", [])

    node_lines = [
        f"- {node.get('id')}: {node.get('label')} " f"(level {node.get('level', 0)})"
        for node in nodes[:20]
        if node.get("id") and node.get("label")
    ]

    result = []

    if topic_lines:
        result.append("L2 TOPICS:\n" + "\n".join(topic_lines))

    if node_lines:
        result.append("L3 KNOWLEDGE GRAPH NODES:\n" + "\n".join(node_lines))

    return "\n\n".join(result)
