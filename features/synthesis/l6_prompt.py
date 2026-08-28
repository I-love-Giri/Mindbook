import json


def build_synthesis_prompt(
    title,
    duration,
    domain,
    content_type,
    difficulty,
    category,
    parsed,
    entities_text,
    concepts_text,
    sections_text,
    dependency_order,
    guide_instruction,
    next_steps_instruction,
    term_instruction,
):
    return f"""
    
        You are performing the final synthesis stage of a grounded
        knowledge extraction pipeline.

        You have NOT been given the entire original transcript.

        You must therefore use ONLY the information contained in:

        1. Layer 2 semantic metadata
        2. Layer 3 knowledge graph
        3. Layer 5 section analyses

        Do not invent information that is not supported by those sources.

        ==================================================
        VIDEO
        ==================================================

        TITLE:
        {title}

        DURATION:
        {float(duration or 0):.0f} seconds

        DOMAIN:
        {domain}

        CONTENT TYPE:
        {content_type}

        DIFFICULTY:
        {difficulty}

        CONTENT CATEGORY:
        {category}

        ==================================================
        LAYER 2
        ==================================================

        OVERALL TOPIC:
        {parsed.get("overall_topic", "")}

        PREREQUISITES:
        {json.dumps(
            parsed.get("prerequisites", []),
            ensure_ascii=False,
        )}

        LEARNING OBJECTIVES:
        {json.dumps(
            parsed.get("learning_objectives", []),
            ensure_ascii=False,
        )}

        KEY ENTITIES:
        {entities_text}

        ==================================================
        CONCEPT STRUCTURE
        ==================================================

        {concepts_text}

        DEPENDENCY ORDER:
        {json.dumps(
            dependency_order,
            ensure_ascii=False,
        )}

        ==================================================
        ANALYZED SECTIONS
        ==================================================

        {sections_text}

        ==================================================
        SYNTHESIS RULES
        ==================================================

        The analyzed sections are the primary evidence.

        Do not:

        - invent facts
        - invent statistics
        - invent quotations
        - invent citations
        - invent historical events
        - invent APIs
        - invent code
        - invent formulas
        - claim that something is missing merely because it was not present
        in the supplied summaries
        - present speculation as fact

        If there is insufficient evidence to determine whether something
        was omitted or outdated, explicitly say so.

        For "gaps":

        Distinguish between:

        1. Explicit omission:
        A relevant issue clearly expected from the subject but absent
        from the analyzed material.

        2. Possible limitation:
        The available section analyses do not provide enough evidence
        to determine whether the subject was adequately covered.

        3. Potential outdatedness:
        Only mention this when the supplied material itself provides
        evidence that something may have changed.

        Do not perform external fact checking.

        ==================================================
        CONTENT-SPECIFIC INSTRUCTIONS
        ==================================================

        {guide_instruction}

        ==================================================
        OUTPUT
        ==================================================

        Return ONLY valid JSON.

        {{
            "complete_guide": "...",

            "executive_summary": "...",

            "faq": [
                {{
                    "q": "...",
                    "a": "...",
                    "source_section": null
                }}
            ],

            "gaps": "...",

            "related_concepts": [
                "...",
                "...",
                "...",
                "..."
            ],

            "next_steps": [
                "..."
            ],

            "flashcards": [
                {{
                    "front": "...",
                    "back": "..."
                }}
            ],

            "key_terms": [
                {{
                    "term": "...",
                    "definition": "...",
                    "example": "..."
                }}
            ],

            "difficulty_progression": [
                {{
                    "level": "beginner",
                    "description": "...",
                    "concepts": []
                }},
                {{
                    "level": "intermediate",
                    "description": "...",
                    "concepts": []
                }},
                {{
                    "level": "advanced",
                    "description": "...",
                    "concepts": []
                }}
            ]
        }}

        ==================================================
        FIELD RULES
        ==================================================

        complete_guide:
        {guide_instruction}

        Write 4-6 substantial paragraphs.

        executive_summary:
        Write 2-3 sentences explaining what the material is about
        and why it matters.

        faq:
        Create 3-6 high-value questions.

        Every factual answer must be grounded in the supplied sections.

        source_section:
        Use the section number containing the strongest evidence.

        Use null when the answer synthesizes multiple sections.

        gaps:
        Be conservative and evidence-aware.

        related_concepts:
        Return 3-6 concepts that logically extend the subject.

        next_steps:
        Return 3-5 useful learning activities or subjects.

        {next_steps_instruction}

        flashcards:
        Return 5-10 concise cards.

        key_terms:
        Return 5-10 important terms.

        {term_instruction}

        difficulty_progression:
        Explain how the concepts can be learned from foundational
        to advanced level.

        Use concept names from the supplied L2/L3 data whenever possible.

        Raw JSON only.
        """
