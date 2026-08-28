from typing import Tuple

CODE_DOMAIN_KEYWORDS = {
    "programming",
    "software",
    "coding",
    "backend",
    "frontend",
    "database",
    "devops",
    "cybersecurity",
    "algorithm",
    "data structures",
    "machine learning",
    "deep learning",
    "data science",
    "artificial intelligence",
}

QUANT_DOMAIN_KEYWORDS = {
    "mathematics",
    "math",
    "statistics",
    "physics",
    "chemistry",
    "biology",
    "engineering",
    "economics",
    "finance",
    "accounting",
    "calculus",
    "algebra",
    "geometry",
    "probability",
}

NARRATIVE_CONTENT_TYPES = {
    "vlog",
    "interview",
    "documentary",
    "news",
    "debate",
    "review",
    "podcast",
    "story",
}


def category_instructions(
    domain: str,
    content_type: str,
) -> Tuple[str, str, str]:

    domain_l = (domain or "").lower()
    content_type_l = (content_type or "").lower()

    if content_type_l in NARRATIVE_CONTENT_TYPES:
        category = "narrative"

    elif any(keyword in domain_l for keyword in CODE_DOMAIN_KEYWORDS):
        category = "code"

    elif any(keyword in domain_l for keyword in QUANT_DOMAIN_KEYWORDS):
        category = "quant"

    else:
        category = "narrative"

    if category == "code":

        guide_instruction = """
        Write a practical technical guide covering:
        1. the central problem,
        2. the important concepts,
        3. how the mechanisms work,
        4. implementation considerations,
        5. practical applications.

        Include code concepts only when supported by the analyzed sections.
        Do not invent APIs, syntax, commands, or implementations.
        """

        next_steps_instruction = (
            "Suggest logical next concepts, tools, projects, "
            "or practice activities based on the material."
        )

        term_instruction = (
            "Define the technical term in plain English and explain "
            "how it is used in the context of this topic."
        )

    elif category == "quant":
        guide_instruction = """
        Write a conceptual guide covering:
        1. the underlying idea,
        2. important definitions or formulas,
        3. how the reasoning works,
        4. why the result matters,
        5. a worked example only when directly supported by the material.

        Do not invent formulas or numerical claims.
        """

        next_steps_instruction = (
            "Suggest related concepts, exercises, problem types, "
            "or subjects to study next."
        )

        term_instruction = (
            "Define the term, formula, or concept clearly and give "
            "a simple example only when supported by the material."
        )

    else:
        guide_instruction = """
        Write a factual briefing covering:
        1. background and context,
        2. the major people, places, events, arguments, or ideas,
        3. relationships between them,
        4. why the subject matters,
        5. important perspectives or unresolved questions.

        Remain factual and balanced.
        """

        next_steps_instruction = (
            "Suggest related topics, events, books, documentaries, "
            "or concepts that logically extend this material."
        )

        term_instruction = (
            "Define the name, place, acronym, policy, or specialized "
            "term and explain its relevance to the subject."
        )

    return (
        category,
        guide_instruction.strip(),
        next_steps_instruction,
        term_instruction,
    )
