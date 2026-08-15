import asyncio
import json
import logging
from typing import Any, Dict

from l6_layer import layer6_synthesis
from llm.groq_service import LLMService
from l2_layer import layer2_content_parse
from l3_layer import layer3_knowledge_graph
from l5_layer import layer5_deep_dive

logger = logging.getLogger(__name__)


# ============================================================
# JSON HELPERS
# ============================================================


def _extract_json(raw: Any) -> dict:
    """
    Extract a JSON object from an LLM response.

    Handles:
        - dict responses
        - plain JSON strings
        - ```json ... ``` fenced responses
    """

    if not raw:
        return {}

    if isinstance(raw, dict):
        return raw

    if not isinstance(raw, str):
        return {}

    raw = raw.strip()

    if not raw:
        return {}

    # --------------------------------------------------------
    # Remove markdown code fences
    # --------------------------------------------------------

    if raw.startswith("```"):
        lines = raw.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        raw = "\n".join(lines).strip()

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    try:
        result = json.loads(raw)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        logger.warning("Failed to parse L7 JSON response")

    return {}


# ============================================================
# SECTION HELPERS
# ============================================================


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


def _build_sections_context(
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


def _build_dependency_context(kg: Dict[str, Any]) -> str:
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


def _build_graph_context(kg: Dict[str, Any]) -> str:
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


def _build_key_terms_context(synthesis: Dict[str, Any]) -> str:
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


def _build_flashcard_context(synthesis: Dict[str, Any]) -> str:
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


# ============================================================
# QUIZ VALIDATION
# ============================================================


def _validate_quiz(quiz: Any) -> list:
    """
    Validate and clean L7 quiz questions.
    """

    if not isinstance(quiz, list):
        return []

    valid_answers = {"A", "B", "C", "D"}
    valid_difficulties = {
        "beginner",
        "intermediate",
        "advanced",
    }

    cleaned = []

    for question in quiz:

        if not isinstance(question, dict):
            continue

        question_text = question.get("question")

        if not isinstance(question_text, str):
            continue

        question_text = question_text.strip()

        if not question_text:
            continue

        options = question.get("options")

        if not isinstance(options, list):
            continue

        if len(options) != 4:
            continue

        cleaned_options = []

        for option in options:

            if not isinstance(option, str):
                continue

            option = option.strip()

            if option:
                cleaned_options.append(option)

        if len(cleaned_options) != 4:
            continue

        correct = str(question.get("correct", "")).strip().upper()

        if correct not in valid_answers:
            continue

        explanation = question.get(
            "explanation",
            "",
        )

        if not isinstance(explanation, str):
            explanation = str(explanation)

        difficulty = str(
            question.get(
                "difficulty",
                "intermediate",
            )
        ).lower()

        if difficulty not in valid_difficulties:
            difficulty = "intermediate"

        section_ref = question.get(
            "section_ref",
            0,
        )

        try:
            section_ref = float(section_ref)
        except (TypeError, ValueError):
            section_ref = 0

        cleaned.append(
            {
                "question": question_text,
                "options": cleaned_options,
                "correct": correct,
                "explanation": explanation.strip(),
                "difficulty": difficulty,
                "section_ref": section_ref,
            }
        )

    return cleaned


# ============================================================
# TIMELINE VALIDATION
# ============================================================


def _validate_timeline(timeline: Any) -> list:
    """
    Validate concept timeline entries.
    """

    if not isinstance(timeline, list):
        return []

    valid_importance = {
        "high",
        "medium",
        "low",
    }

    cleaned = []

    for item in timeline:

        if not isinstance(item, dict):
            continue

        concept = item.get("concept", "")

        if not isinstance(concept, str):
            continue

        concept = concept.strip()

        if not concept:
            continue

        try:
            timestamp = float(item.get("timestamp", 0))
        except (TypeError, ValueError):
            timestamp = 0

        importance = str(
            item.get(
                "importance",
                "medium",
            )
        ).lower()

        if importance not in valid_importance:
            importance = "medium"

        cleaned.append(
            {
                "timestamp": timestamp,
                "concept": concept,
                "importance": importance,
            }
        )

    # --------------------------------------------------------
    # Timeline should be chronological
    # --------------------------------------------------------

    cleaned.sort(key=lambda item: item["timestamp"])

    return cleaned


# ============================================================
# MIND MAP VALIDATION
# ============================================================


def _validate_mind_map(value: Any) -> str:
    """
    Basic validation for text-based mind map.
    """

    if not isinstance(value, str):
        return ""

    value = value.strip()

    if not value:
        return ""

    # Prevent markdown code fences from leaking into UI.
    if value.startswith("```"):
        lines = value.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        value = "\n".join(lines).strip()

    return value


# ============================================================
# L7
# ============================================================


async def layer7_study_assets(
    sections: list,
    synthesis: Dict[str, Any],
    kg: Dict[str, Any],
    parsed: Dict[str, Any],
    llm_service: LLMService,
) -> Dict[str, Any]:
    """
    Generate study assets from the previously processed video layers.

    Inputs
    ------

    sections:
        L5 section analysis results.

    synthesis:
        L6 synthesis result.

    kg:
        L3 knowledge graph result.

    parsed:
        L2 semantic metadata.

    llm_service:
        Existing LLMService instance.

    Returns
    -------

    {
        "quiz": [...],
        "concept_timeline": [...],
        "mind_map_text": "..."
    }
    """

    # ========================================================
    # Basic metadata
    # ========================================================

    domain = parsed.get(
        "domain",
        "",
    )

    content_type = parsed.get(
        "content_type",
        "tutorial",
    )

    difficulty = parsed.get(
        "difficulty",
        "intermediate",
    )

    overall_topic = parsed.get(
        "overall_topic",
        "",
    )

    learning_objectives = parsed.get(
        "learning_objectives",
        [],
    )

    # ========================================================
    # Sections
    # ========================================================

    sections_context = _build_sections_context(
        sections,
        max_chars=7000,
    )

    # ========================================================
    # L3 graph
    # ========================================================

    dependency_context = _build_dependency_context(kg)

    graph_context = _build_graph_context(kg)

    # ========================================================
    # L6 synthesis
    # ========================================================

    key_terms_context = _build_key_terms_context(synthesis)

    flashcards_context = _build_flashcard_context(synthesis)

    executive_summary = synthesis.get(
        "executive_summary",
        "",
    )

    # ========================================================
    # Prompt
    # ========================================================

    prompt = f"""
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

    # ========================================================
    # LLM CALL
    # ========================================================

    try:

        result = await llm_service.generate(
            prompt=prompt,
            max_tokens=2200,
            temperature=0.2,
            json_output=True,
        )

    except Exception as exc:

        logger.exception(
            "L7 study asset generation failed: %s",
            exc,
        )

        return {
            "quiz": [],
            "concept_timeline": [],
            "mind_map_text": "",
        }

    # ========================================================
    # Parse
    # ========================================================

    if isinstance(result, str):
        result = _extract_json(result)

    if not isinstance(result, dict):

        return {
            "quiz": [],
            "concept_timeline": [],
            "mind_map_text": "",
        }

    # ========================================================
    # Defensive defaults
    # ========================================================

    result.setdefault(
        "quiz",
        [],
    )

    result.setdefault(
        "concept_timeline",
        [],
    )

    result.setdefault(
        "mind_map_text",
        "",
    )

    # ========================================================
    # Validate
    # ========================================================

    result["quiz"] = _validate_quiz(result.get("quiz"))

    result["concept_timeline"] = _validate_timeline(result.get("concept_timeline"))

    result["mind_map_text"] = _validate_mind_map(result.get("mind_map_text"))

    return result


# ============================================================
# TEST / CLI
# ============================================================


if __name__ == "__main__":

    import json

    from storage.services.transcript_service import TranscriptService
    from video_processor.services.parser import extract_video_id
    from pipeline.chunking.chunker import TranscriptChunker

    url = input("Enter YouTube URL: ").strip()

    if not url:
        print("URL cannot be empty")
        exit(1)

    video_id = extract_video_id(url)

    print(f"\nVideo ID: {video_id}")

    # ========================================================
    # LOAD TRANSCRIPT
    # ========================================================

    transcript_service = TranscriptService()

    transcript = transcript_service.get(video_id)

    print(f"Transcript segments: " f"{len(transcript.segments)}")

    # ========================================================
    # VIDEO INFO
    # ========================================================

    video_info = transcript.video_info

    print("\nVIDEO INFO")
    print("=" * 80)

    print(
        json.dumps(
            video_info,
            indent=2,
            ensure_ascii=False,
        )
    )

    # ========================================================
    # LLM SERVICE
    # ========================================================

    llm_service = LLMService()

    # ========================================================
    # L2
    # ========================================================

    print("\n")
    print("=" * 80)
    print("RUNNING L2")
    print("=" * 80)

    l2_result = asyncio.run(
        layer2_content_parse(
            transcript=transcript,
            video_info=video_info,
            llm_service=llm_service,
        )
    )

    print(
        json.dumps(
            l2_result,
            indent=2,
            ensure_ascii=False,
        )
    )

    # ========================================================
    # L3
    # ========================================================

    print("\n")
    print("=" * 80)
    print("RUNNING L3")
    print("=" * 80)

    l3_result = asyncio.run(
        layer3_knowledge_graph(
            layer2_result=l2_result,
            transcript=transcript.segments,
            video_info=video_info,
            llm_service=llm_service,
        )
    )

    print(
        json.dumps(
            l3_result,
            indent=2,
            ensure_ascii=False,
        )
    )

    # ========================================================
    # CHUNKING
    # ========================================================

    print("\n")
    print("=" * 80)
    print("CHUNKING TRANSCRIPT")
    print("=" * 80)

    chunker = TranscriptChunker(
        version=TranscriptChunker.VERSION_SEMANTIC,
        max_words=300,
        overlap_words=50,
    )

    chunks = chunker.chunk(
        segments=transcript.segments,
        video_id=video_id,
        chapters=video_info.get("chapters"),
        duration=video_info.get("duration"),
    )

    print(f"Generated {len(chunks)} chunks")

    # ========================================================
    # L5
    # ========================================================

    print("\n")
    print("=" * 80)
    print("RUNNING L5")
    print("=" * 80)

    sections = []

    for index, chunk in enumerate(chunks):

        print(f"\nAnalyzing chunk " f"{index + 1}/{len(chunks)}...")

        l5_result = asyncio.run(
            layer5_deep_dive(
                chunk=chunk,
                video_info=video_info,
                parsed=l2_result,
                llm_service=llm_service,
            )
        )

        # ----------------------------------------------------
        # Preserve chunk metadata.
        # ----------------------------------------------------

        section = dict(l5_result)

        section["chunk_id"] = chunk.get("chunk_id")

        section["title"] = chunk.get("title") or "Untitled Section"

        section["start"] = chunk.get(
            "start",
            0,
        )

        section["end"] = chunk.get(
            "end",
            section["start"],
        )

        section["word_count"] = chunk.get(
            "word_count",
            0,
        )

        sections.append(section)

    print(f"\nGenerated {len(sections)} " f"L5 sections")

    # ========================================================
    # L6
    # ========================================================

    #
    # IMPORTANT:
    #
    # Your current L6 implementation/function is not included
    # in the files you posted earlier, so this CLI expects you
    # to plug your existing L6 function into this section.
    #
    # For example:
    #
    # from l6_layer import layer6_synthesis
    #
    # l6_result = asyncio.run(
    #     layer6_synthesis(
    #         video_info=video_info,
    #         sections=sections,
    #         parsed=l2_result,
    #         kg=l3_result,
    #         llm_service=llm_service,
    #     )
    # )
    #

    """print("\n")
    print("=" * 80)
    print("L6 RESULT REQUIRED")
    print("=" * 80)

    print("Your existing L6 result should be supplied here.")

    print("\nFor testing L7 independently, enter " "a path to an L6 JSON file.")

    l6_path = input("L6 JSON file path: ").strip()

    if not l6_path:

        print("L6 JSON file is required for this test.")

        exit(1)"""

    try:

        l6_result = asyncio.run(
            layer6_synthesis(
                video_info=video_info,
                sections=sections,
                parsed=l2_result,
                kg=l3_result,
                llm_service=llm_service,
            )
        )

    except Exception as exc:

        print(f"Failed to load L6 JSON: {exc}")

        exit(1)

    # ========================================================
    # L7
    # ========================================================

    print("\n")
    print("=" * 80)
    print("RUNNING L7")
    print("=" * 80)

    l7_result = asyncio.run(
        layer7_study_assets(
            sections=sections,
            synthesis=l6_result,
            kg=l3_result,
            parsed=l2_result,
            llm_service=llm_service,
        )
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print("\n")
    print("=" * 80)
    print("L7 RESULT")
    print("=" * 80)

    print(
        json.dumps(
            l7_result,
            indent=2,
            ensure_ascii=False,
        )
    )

    # ========================================================
    # HUMAN READABLE OUTPUT
    # ========================================================

    print("\n")
    print("=" * 80)
    print("L7 HUMAN-READABLE SUMMARY")
    print("=" * 80)

    # --------------------------------------------------------
    # QUIZ
    # --------------------------------------------------------

    print("\nQUIZ")
    print("-" * 80)

    for index, question in enumerate(
        l7_result.get("quiz", []),
        start=1,
    ):

        print(f"\n{index}. " f"{question.get('question', '')}")

        for option in question.get(
            "options",
            [],
        ):

            print(f"   {option}")

        print(f"   Correct: " f"{question.get('correct', '')}")

        print(f"   Difficulty: " f"{question.get('difficulty', '')}")

        print(f"   Section: " f"{question.get('section_ref', 0)}s")

        print(f"   Explanation: " f"{question.get('explanation', '')}")

    # --------------------------------------------------------
    # TIMELINE
    # --------------------------------------------------------

    print("\n")
    print("CONCEPT TIMELINE")
    print("-" * 80)

    for item in l7_result.get(
        "concept_timeline",
        [],
    ):

        print(
            f"{item.get('timestamp', 0):>8.1f}s | "
            f"{item.get('importance', 'medium'):>6} | "
            f"{item.get('concept', '')}"
        )

    # --------------------------------------------------------
    # MIND MAP
    # --------------------------------------------------------

    print("\n")
    print("MIND MAP")
    print("-" * 80)

    print(
        l7_result.get(
            "mind_map_text",
            "",
        )
    )
