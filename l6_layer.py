import json
import logging
from typing import Any, Dict

from features.synthesis.l6_category_classifier import category_instructions

from features.synthesis.l6_context_builder import (
    build_concepts_text,
    build_entities_text,
    build_sections_text,
)
from features.synthesis.l6_prompt import build_synthesis_prompt
from features.synthesis.l6_validator import normalize_synthesis_result
from llm.gemini_service import GeminiService

logger = logging.getLogger(__name__)


async def layer6_synthesis(
    video_info: Dict[str, Any],
    sections: list,
    parsed: Dict[str, Any],
    kg: Dict[str, Any],
    llm_service: GeminiService,
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

    entities_text = build_entities_text(parsed)

    sections_text = build_sections_text(
        sections,
        max_chars_per_section=500,
    )

    concepts_text = build_concepts_text(
        parsed,
        kg,
    )

    dependency_order = kg.get(
        "dependency_order",
        [],
    )

    category, guide_instruction, next_steps_instruction, term_instruction = (
        category_instructions(
            domain,
            content_type,
        )
    )

    prompt = build_synthesis_prompt(
        title=title,
        duration=duration,
        domain=domain,
        content_type=content_type,
        difficulty=difficulty,
        entities_text=entities_text,
        sections_text=sections_text,
        concepts_text=concepts_text,
        dependency_order=dependency_order,
        category=category,
        parsed=parsed,
        guide_instruction=guide_instruction,
        next_steps_instruction=next_steps_instruction,
        term_instruction=term_instruction,
    )

    try:
        result = await llm_service.generate(
            prompt=prompt,
            max_tokens=10000,
            temperature=0.15,
            json_output=True,
        )

        return normalize_synthesis_result(result)

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


if __name__ == "__main__":

    import asyncio
    import json

    from l2_layer import layer2_content_parse
    from l3_layer import layer3_knowledge_graph
    from l5_layer import layer5_deep_dive
    from llm.gemini_service import GeminiService
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
        llm_service = GeminiService()

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
