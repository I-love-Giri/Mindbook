import json
import logging
from typing import Any, Dict, Optional, Tuple

from features.deep_dive.l5_prompt import build_section_prompt
from features.deep_dive.l5_validator import normalize_deep_dive_result
from l2_layer import layer2_content_parse
from llm.groq_service import LLMService

logger = logging.getLogger(__name__)


async def layer5_deep_dive(
    chunk: Dict[str, Any],
    video_info: Dict[str, Any],
    parsed: Dict[str, Any],
    llm_service: LLMService,
) -> Dict[str, Any]:

    transcript_text = chunk.get("text", "").strip()

    if not transcript_text:
        return {
            "blocks": [],
            "key_concepts": [],
            "sketch_note": {},
            "difficulty_rating": 1,
        }

    domain = parsed.get("domain", "")
    content_type = parsed.get("content_type", "tutorial")
    difficulty = parsed.get("difficulty", "intermediate")

    section_title = (
        chunk.get("title")
        or parsed.get("overall_topic")
        or video_info.get("title")
        or "Untitled Section"
    )

    # start_time = chunk.get("start", 0)
    # end_time = chunk.get("end", start_time)

    prompt = build_section_prompt(
        domain=domain,
        content_type=content_type,
        difficulty=difficulty,
        section_title=section_title,
        start_time=chunk.get("start", 0),
        end_time=chunk.get("end", 0),
        transcript_text=transcript_text[:6000],
    )

    try:
        raw = await llm_service.generate(
            prompt=prompt,
            max_tokens=6000,
            temperature=0.2,
            json_output=True,
        )

        return normalize_deep_dive_result(raw)

    except Exception as exc:
        logger.exception(
            "L5 deep dive failed for chunk %s: %s",
            chunk.get("chunk_id"),
            exc,
        )

    return {
        "blocks": [
            {
                "type": "paragraph",
                "content": "Analysis unavailable for this section.",
            }
        ],
        "key_concepts": [],
        "sketch_note": {},
        "difficulty_rating": 3,
    }


if __name__ == "__main__":

    import asyncio
    import json

    from llm.groq_service import LLMService
    from llm.gemini_service import GeminiService

    from storage.services.transcript_service import TranscriptService
    from video_processor.services.parser import extract_video_id
    from pipeline.chunking.chunker import TranscriptChunker

    url = input("Enter YouTube URL: ").strip()

    if not url:
        print("URL cannot be empty")
        exit(1)

    video_id = extract_video_id(url)

    print(f"\nVideo ID: {video_id}")

    # ---------------------------------------------------------
    # Load transcript
    # ---------------------------------------------------------

    transcript_service = TranscriptService()

    transcript = transcript_service.get(video_id)

    print(f"Transcript segments: {len(transcript.segments)}")

    # ---------------------------------------------------------
    # Video info
    # ---------------------------------------------------------

    video_info = transcript.video_info

    print("\nVIDEO INFO")
    print(json.dumps(video_info, indent=2))

    # ---------------------------------------------------------
    # L2
    # ---------------------------------------------------------

    llm_service = LLMService()
    gemini_llm_service = GeminiService()

    print("\nRunning L2...\n")

    l2_result = asyncio.run(
        layer2_content_parse(
            transcript=transcript,
            video_info=video_info,
            llm_service=gemini_llm_service,
        )
    )

    print("L2 RESULT")
    print(json.dumps(l2_result, indent=2, ensure_ascii=False))

    # ---------------------------------------------------------
    # Chunk transcript
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Show available chunks
    # ---------------------------------------------------------

    print("\nCHUNKS")
    print("=" * 80)

    for chunk in chunks:
        print(
            f"[{chunk['chunk_id']}] "
            f"{chunk.get('title', 'Untitled')} "
            f"({chunk['start']}s - {chunk['end']}s, "
            f"{chunk['word_count']} words)"
        )

    # ---------------------------------------------------------
    # L5 — Analyze ALL chunks in batches of 3
    # ---------------------------------------------------------

    BATCH_SIZE = 3

    async def process_l5_batch(batch):
        tasks = [
            layer5_deep_dive(
                chunk=chunk,
                video_info=video_info,
                parsed=l2_result,
                llm_service=llm_service,
            )
            for chunk in batch
        ]

        return await asyncio.gather(*tasks)

    async def process_all_l5_chunks():

        all_results = []

        for batch_start in range(0, len(chunks), BATCH_SIZE):

            batch = chunks[batch_start : batch_start + BATCH_SIZE]

            print(
                f"\nRunning L5 batch: "
                f"{batch_start + 1}-"
                f"{batch_start + len(batch)}/{len(chunks)}"
            )

            # Show which chunks are going together
            for chunk in batch:
                print(f"  → [{chunk['chunk_id']}] " f"{chunk.get('title', 'Untitled')}")

            # Run 3 chunks concurrently
            batch_results = await process_l5_batch(batch)

            all_results.extend(batch_results)

            print(
                f"✓ Batch completed: "
                f"{batch_start + 1}-"
                f"{batch_start + len(batch)}"
            )

        return all_results

    print("\nRunning L5 for ALL chunks...\n")

    l5_results = asyncio.run(process_all_l5_chunks())

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------

    print("\n")
    print("=" * 80)
    print("L5 RESULTS")
    print("=" * 80)

    for i, result in enumerate(l5_results):

        print(f"\n{'=' * 80}")
        print(f"SECTION {i + 1}/{len(l5_results)}")
        print(f"{'=' * 80}")

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )
