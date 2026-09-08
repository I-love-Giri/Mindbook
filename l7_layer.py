import asyncio
import json
import logging
from typing import Any, Dict

from features.study_assets.l7_context_builder import (
    build_dependency_context,
    build_flashcard_context,
    build_graph_context,
    build_key_terms_context,
    build_sections_context,
)
from features.study_assets.l7_prompt import build_study_assets_prompt
from features.study_assets.l7_validators import normalize_study_assets_result

from l6_layer import layer6_synthesis
from llm.groq_service import LLMService
from llm.gemini_service import GeminiService

from l2_layer import layer2_content_parse
from l3_layer import layer3_knowledge_graph
from l5_layer import layer5_deep_dive
from pipeline.chunking.chunker import TranscriptChunker
from video_processor.services.parser import extract_video_id
from storage.services.transcript_service import TranscriptService

logger = logging.getLogger(__name__)


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

    sections_context = build_sections_context(
        sections,
        max_chars=7000,
    )

    # ========================================================
    # L3 graph
    # ========================================================

    dependency_context = build_dependency_context(kg)

    graph_context = build_graph_context(kg)

    # ========================================================
    # L6 synthesis
    # ========================================================

    key_terms_context = build_key_terms_context(synthesis)

    flashcards_context = build_flashcard_context(synthesis)

    executive_summary = synthesis.get(
        "executive_summary",
        "",
    )

    # ========================================================
    # Prompt
    # ========================================================

    prompt = build_study_assets_prompt(
        domain=domain,
        content_type=content_type,
        difficulty=difficulty,
        overall_topic=overall_topic,
        learning_objectives=learning_objectives,
        sections_context=sections_context,
        graph_context=graph_context,
        dependency_context=dependency_context,
        key_terms_context=key_terms_context,
        flashcards_context=flashcards_context,
        executive_summary=executive_summary,
    )

    # ========================================================
    # LLM CALL
    # ========================================================

    try:

        result = await llm_service.generate(
            prompt=prompt,
            max_tokens=3000,
            temperature=0.2,
            json_output=True,
        )

        """print("\n================ L7 RAW RESULT ================\n")
        print(result)
        print("\n================================================\n")"""

        normalized = normalize_study_assets_result(result)

        """print("\n================ L7 NORMALIZED ================\n")
        print(normalized)
        print("\n================================================\n")"""

        return normalized

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


# ============================================================
# TEST / CLI
# ============================================================


async def main():

    # ========================================================
    # INPUT
    # ========================================================

    url = input("Enter YouTube URL: ").strip()

    if not url:
        print("URL cannot be empty")
        return

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
    # LLM SERVICES
    # ========================================================

    llm_service = LLMService()
    gemini_llm_service = GeminiService()

    # ========================================================
    # L2
    # ========================================================

    print("\n")
    print("=" * 80)
    print("RUNNING L2")
    print("=" * 80)

    l2_result = await layer2_content_parse(
        transcript=transcript,
        video_info=video_info,
        llm_service=gemini_llm_service,
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

    l3_result = await layer3_knowledge_graph(
        layer2_result=l2_result,
        transcript=transcript.segments,
        video_info=video_info,
        llm_service=llm_service,
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

        # IMPORTANT:
        # Do NOT use asyncio.run() here.
        # We are already inside the main event loop.

        l5_result = await layer5_deep_dive(
            chunk=chunk,
            video_info=video_info,
            parsed=l2_result,
            llm_service=llm_service,
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

    print("\n")
    print("=" * 80)
    print("RUNNING L6")
    print("=" * 80)

    try:

        # IMPORTANT:
        # Do NOT use asyncio.run() here.
        # GeminiService is reused inside the SAME event loop.

        l6_result = await layer6_synthesis(
            video_info=video_info,
            sections=sections,
            parsed=l2_result,
            kg=l3_result,
            llm_service=gemini_llm_service,
        )

    except Exception as exc:

        print(f"\nL6 synthesis failed: {exc}")

        raise

    # ========================================================
    # L7
    # ========================================================

    print("\n")
    print("=" * 80)
    print("RUNNING L7")
    print("=" * 80)

    l7_result = await layer7_study_assets(
        sections=sections,
        synthesis=l6_result,
        kg=l3_result,
        parsed=l2_result,
        llm_service=llm_service,
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


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
