import json


def build_study_assets_prompt(
    domain,
    content_type,
    difficulty,
    overall_topic,
    learning_objectives,
    graph_context,
    dependency_context,
    key_terms_context,
    flashcards_context,
    sections_context,
    executive_summary,
):
    return f"""
        You are generating study materials for a video-based learning system.

        The material has already been analyzed through multiple semantic layers.

        Use ONLY the supplied information.

        Do NOT invent facts, examples, people, events, statistics,
        technical details, formulas, or relationships that are not supported
        by the supplied material.

        IMPORTANT:

        The fact that a concept appears in multiple generated layers does NOT
        mean it has been independently verified.

        Treat the supplied material as the source representation of the video.

        When generating questions, make sure the answer can be supported by
        the supplied material.

        ============================================================
        VIDEO CONTEXT
        ============================================================

        DOMAIN:
        {domain}

        CONTENT TYPE:
        {content_type}

        DIFFICULTY:
        {difficulty}

        OVERALL TOPIC:
        {overall_topic}

        EXECUTIVE SUMMARY:
        {executive_summary}

        LEARNING OBJECTIVES:
        {json.dumps(
            learning_objectives,
            ensure_ascii=False,
        )}

        ============================================================
        L3 KNOWLEDGE GRAPH
        ============================================================

        IMPORTANT NODES:
        {graph_context or "No graph nodes available."}

        DEPENDENCY ORDER:
        {dependency_context}

        The dependency order represents the conceptual learning sequence.

        Use it when deciding which concepts should appear in easier versus
        more advanced questions.

        ============================================================
        L6 KEY TERMS
        ============================================================

        {key_terms_context or "No key terms available."}

        ============================================================
        L6 FLASHCARDS
        ============================================================

        These are existing study hints.

        Do NOT simply copy them.

        Improve or transform them into useful quiz questions.

        {flashcards_context or "No flashcards available."}

        ============================================================
        L5 ANALYZED SECTIONS
        ============================================================

        {sections_context or "No analyzed sections available."}


        ============================================================
        TASK 1 — QUIZ
        ============================================================

        Generate 5-10 multiple-choice questions.

        The questions should test actual understanding.

        Prefer questions involving:

        - definitions
        - conceptual distinctions
        - cause and effect
        - mechanisms
        - relationships between concepts
        - applications supported by the source
        - prerequisite understanding
        - important details that affect understanding

        Avoid:

        - trivial wording questions
        - questions about tiny incidental details
        - ambiguous questions
        - trick questions
        - facts not present in the supplied material
        - questions where multiple answers could reasonably be correct

        Each question MUST contain exactly four options.

        Only ONE option may be correct.

        Options MUST be labeled:

        A) ...
        B) ...
        C) ...
        D) ...

        The correct field must contain only:

        A
        B
        C
        or
        D

        Each question must include:

        - question
        - options
        - correct
        - explanation
        - difficulty
        - section_ref

        section_ref must contain the START TIMESTAMP in seconds of the
        section that best supports the answer.

        Difficulty distribution:

        - approximately 40% beginner
        - approximately 40% intermediate
        - approximately 20% advanced

        For beginner questions, focus on foundational concepts.

        For intermediate questions, test relationships and mechanisms.

        For advanced questions, test deeper reasoning or connections between
        concepts that are explicitly supported by the material.


        ============================================================
        TASK 2 — CONCEPT TIMELINE
        ============================================================

        Create a chronological conceptual timeline.

        Use the actual timestamps from the analyzed sections.

        Each entry should represent a meaningful concept introduced,
        developed, explained, or demonstrated.

        Do NOT create an entry for every tiny topic change.

        Prefer approximately 5-12 timeline entries depending on the length
        and complexity of the video.

        Each entry must contain:

        timestamp:
            approximate timestamp in seconds

        concept:
            meaningful concept being introduced or developed

        importance:
            high | medium | low

        The timeline must be sorted chronologically.


        ============================================================
        TASK 3 — MIND MAP
        ============================================================

        Create a compact text-based mind map.

        The root should represent the central topic.

        Use the L3 knowledge graph and dependency order to determine the
        major branches.

        Use indentation to represent hierarchy.

        Example:

        Central Topic
        Foundation
            Concept A
            Concept B
        Main Mechanism
            Concept C
            Concept D
        Application
            Example A

        Do NOT include every graph node.

        Keep the mind map focused on the most important concepts.

        Maximum recommended depth: 4 levels.


        ============================================================
        QUALITY RULES
        ============================================================

        - Do not hallucinate.
        - Do not add external knowledge.
        - Do not create unsupported examples.
        - Do not create unsupported historical claims.
        - Do not create unsupported formulas.
        - Do not create unsupported programming code.
        - Do not turn a minor mention into a major concept.
        - Prefer concepts supported by L5 sections.
        - Prefer foundational concepts from the L3 dependency order.
        - Use timestamps from the actual sections.
        - Keep quiz questions unambiguous.
        - Ensure exactly one correct answer per question.
        - Make distractors plausible but clearly incorrect according to the
        supplied material.
        - Explanations should explain WHY the correct answer is correct.

        ============================================================
        OUTPUT
        ============================================================

        Return ONLY valid JSON.

        {{
            "quiz": [
                {{
                    "question": "Question text",
                    "options": [
                        "A) Option A",
                        "B) Option B",
                        "C) Option C",
                        "D) Option D"
                    ],
                    "correct": "A",
                    "explanation": "Why this answer is correct.",
                    "difficulty": "beginner",
                    "section_ref": 0
                }}
            ],

            "concept_timeline": [
                {{
                    "timestamp": 0,
                    "concept": "Concept introduced",
                    "importance": "high"
                }}
            ],

            "mind_map_text": "Central Topic\\n  Major Concept\\n    Supporting Concept"
        }}

        Raw JSON only.
        """
