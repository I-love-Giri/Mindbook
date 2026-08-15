import json
import logging
from typing import Any, Dict, Tuple

from llm.groq_service import LLMService

logger = logging.getLogger(__name__)


def _extract_json(raw: str) -> dict:
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

    raw = raw.strip()

    if raw.startswith("```"):
        lines = raw.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        raw = "\n".join(lines).strip()

    try:
        result = json.loads(raw)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        logger.warning("Failed to parse L6 JSON response")

    return {}


def _section_explanation(section: dict, max_chars: int = 500) -> str:
    """
    Extract a compact explanation from an L5 section.

    L5 currently stores explanations inside paragraph blocks rather
    than using a dedicated 'explanation' field.
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


def _build_sections_text(
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

        explanation = _section_explanation(
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


def _build_entities_text(parsed: dict) -> str:
    """
    Build compact entity context from L2.
    """

    entities = parsed.get("key_entities", [])

    return ", ".join(
        f"{entity.get('name', '')} " f"({entity.get('type', 'concept')})"
        for entity in entities[:20]
        if entity.get("name")
    )


def _build_concepts_text(
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


def _category_instructions(
    domain: str,
    content_type: str,
) -> Tuple[str, str, str]:

    domain_l = (domain or "").lower()
    content_type_l = (content_type or "").lower()

    code_keywords = {
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

    quant_keywords = {
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

    narrative_types = {
        "vlog",
        "interview",
        "documentary",
        "news",
        "debate",
        "review",
        "podcast",
        "story",
    }

    if content_type_l in narrative_types:
        category = "narrative"

    elif any(keyword in domain_l for keyword in code_keywords):
        category = "code"

    elif any(keyword in domain_l for keyword in quant_keywords):
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


async def layer6_synthesis(
    video_info: Dict[str, Any],
    sections: list,
    parsed: Dict[str, Any],
    kg: Dict[str, Any],
    llm_service: LLMService,
) -> Dict[str, Any]:
    """
    L6 — Grounded whole-video synthesis.

    Combines:

        L2:
            semantic metadata

        L3:
            knowledge graph and dependency order

        L5:
            section-level explanations

    Produces a reusable learning resource containing:

        - complete guide
        - executive summary
        - FAQ
        - evidence-aware gaps
        - related concepts
        - next steps
        - flashcards
        - key terms
        - difficulty progression
    """

    if not sections:
        return {
            "complete_guide": "",
            "executive_summary": "",
            "faq": [],
            "gaps": "",
            "related_concepts": [],
            "next_steps": [],
            "flashcards": [],
            "key_terms": [],
            "difficulty_progression": [],
        }

    title = video_info.get("title", "")
    duration = video_info.get("duration", 0)

    domain = parsed.get("domain", "")
    content_type = parsed.get(
        "content_type",
        "tutorial",
    )

    difficulty = parsed.get(
        "difficulty",
        "intermediate",
    )

    entities_text = _build_entities_text(parsed)

    sections_text = _build_sections_text(
        sections,
        max_chars_per_section=500,
    )

    concepts_text = _build_concepts_text(
        parsed,
        kg,
    )

    dependency_order = kg.get(
        "dependency_order",
        [],
    )

    category, guide_instruction, next_steps_instruction, term_instruction = (
        _category_instructions(
            domain,
            content_type,
        )
    )

    prompt = f"""
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
            "source_section": 1
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

    try:
        result = await llm_service.generate(
            prompt=prompt,
            max_tokens=3500,
            temperature=0.15,
            json_output=True,
        )

    except Exception as exc:
        logger.exception(
            "L6 synthesis failed: %s",
            exc,
        )

        return {
            "complete_guide": "",
            "executive_summary": "",
            "faq": [],
            "gaps": "",
            "related_concepts": [],
            "next_steps": [],
            "flashcards": [],
            "key_terms": [],
            "difficulty_progression": [],
        }

    if isinstance(result, str):
        result = _extract_json(result)

    if not isinstance(result, dict):
        return {
            "complete_guide": "",
            "executive_summary": "",
            "faq": [],
            "gaps": "",
            "related_concepts": [],
            "next_steps": [],
            "flashcards": [],
            "key_terms": [],
            "difficulty_progression": [],
        }

    # ---------------------------------------------------------
    # Defensive defaults
    # ---------------------------------------------------------

    result.setdefault("complete_guide", "")
    result.setdefault("executive_summary", "")
    result.setdefault("faq", [])
    result.setdefault("gaps", "")
    result.setdefault("related_concepts", [])
    result.setdefault("next_steps", [])
    result.setdefault("flashcards", [])
    result.setdefault("key_terms", [])
    result.setdefault("difficulty_progression", [])

    return result


if __name__ == "__main__":

    import asyncio
    import json

    from l2_layer import layer2_content_parse
    from l3_layer import layer3_knowledge_graph
    from l5_layer import layer5_deep_dive
    from llm.groq_service import LLMService
    from storage.services.transcript_service import TranscriptService
    from video_processor.services.parser import extract_video_id
    from pipeline.chunking.chunker import TranscriptChunker

    async def main():

        url = input("\nEnter YouTube URL: ").strip()

        if not url:
            print("URL cannot be empty")
            return

        video_id = extract_video_id(url)

        print(f"\nVideo ID: {video_id}")

        # =====================================================
        # SERVICES
        # =====================================================

        transcript_service = TranscriptService()
        llm_service = LLMService()

        # =====================================================
        # LOAD TRANSCRIPT
        # =====================================================

        print("\nLoading transcript...")

        transcript = transcript_service.get(video_id)

        print(f"Transcript segments: " f"{len(transcript.segments)}")

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

        # =====================================================
        # L2
        # =====================================================

        print("\n\nRunning L2...")
        print("=" * 80)

        l2_result = await layer2_content_parse(
            transcript=transcript,
            video_info=video_info,
            llm_service=llm_service,
        )

        print("\nL2 RESULT")
        print("=" * 80)

        print(
            json.dumps(
                l2_result,
                indent=2,
                ensure_ascii=False,
            )
        )

        # =====================================================
        # L3
        # =====================================================

        print("\n\nRunning L3...")
        print("=" * 80)

        l3_result = await layer3_knowledge_graph(
            layer2_result=l2_result,
            transcript=transcript.segments,
            video_info=video_info,
            llm_service=llm_service,
        )

        print("\nL3 RESULT")
        print("=" * 80)

        print(
            json.dumps(
                l3_result,
                indent=2,
                ensure_ascii=False,
            )
        )

        # =====================================================
        # CHUNKING
        # =====================================================

        print("\n\nCreating transcript chunks...")
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

        print(f"\nGenerated {len(chunks)} chunks")

        # =====================================================
        # L5
        # =====================================================

        sections = []

        print("\n\nRunning L5...")
        print("=" * 80)

        for index, chunk in enumerate(chunks):

            print(
                f"\nL5 [{index + 1}/{len(chunks)}] " f"{chunk.get('title', 'Untitled')}"
            )

            l5_result = await layer5_deep_dive(
                chunk=chunk,
                video_info=video_info,
                parsed=l2_result,
                llm_service=llm_service,
            )

            # Preserve chunk metadata together with L5 output.
            section = {
                **chunk,
                **l5_result,
            }

            sections.append(section)

        print(f"\nCompleted L5 for " f"{len(sections)} sections.")

        # =====================================================
        # L6
        # =====================================================

        print("\n\nRunning L6...")
        print("=" * 80)

        l6_result = await layer6_synthesis(
            video_info=video_info,
            sections=sections,
            parsed=l2_result,
            kg=l3_result,
            llm_service=llm_service,
        )

        # =====================================================
        # FINAL OUTPUT
        # =====================================================

        print("\n\n")
        print("=" * 100)
        print("L6 RESULT")
        print("=" * 100)

        print(
            json.dumps(
                l6_result,
                indent=2,
                ensure_ascii=False,
            )
        )

        # =====================================================
        # HUMAN-READABLE OUTPUT
        # =====================================================

        print("\n\n")
        print("=" * 100)
        print("L6 HUMAN-READABLE SUMMARY")
        print("=" * 100)

        print("\nEXECUTIVE SUMMARY")
        print("-" * 80)

        print(
            l6_result.get(
                "executive_summary",
                "",
            )
        )

        print("\n\nCOMPLETE GUIDE")
        print("-" * 80)

        print(
            l6_result.get(
                "complete_guide",
                "",
            )
        )

        print("\n\nFAQ")
        print("-" * 80)

        for index, faq in enumerate(
            l6_result.get("faq", []),
            start=1,
        ):
            print(f"\n{index}. " f"{faq.get('q', '')}")

            print(f"   {faq.get('a', '')}")

            print(f"   Source section: " f"{faq.get('source_section')}")

        print("\n\nKEY TERMS")
        print("-" * 80)

        for term in l6_result.get(
            "key_terms",
            [],
        ):
            print(f"\n{term.get('term', '')}")

            print(f"  {term.get('definition', '')}")

            if term.get("example"):
                print(f"  Example: " f"{term.get('example')}")

        print("\n\nFLASHCARDS")
        print("-" * 80)

        for index, card in enumerate(
            l6_result.get("flashcards", []),
            start=1,
        ):
            print(f"\n{index}. " f"{card.get('front', '')}")

            print(f"   → " f"{card.get('back', '')}")

        print("\n\nNEXT STEPS")
        print("-" * 80)

        for step in l6_result.get(
            "next_steps",
            [],
        ):
            print(f"- {step}")

        print("\n\nGAPS")
        print("-" * 80)

        print(
            l6_result.get(
                "gaps",
                "",
            )
        )

    asyncio.run(main())
