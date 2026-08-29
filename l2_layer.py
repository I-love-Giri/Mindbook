"""
Extract structured semantic metadata from a YouTube video.

Uses:
    transcript:
        Transcript object returned by YoutubeTranscriptService.

    video_info:
        Metadata returned by extract_chapters_and_info().

    llm_service:
        LLMService instance responsible for the actual LLM call.
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

import json
import asyncio
from features.content_parse.mermaid import clean_mermaid
from features.content_parse.prompt import build_content_parser_prompt
from features.content_parse.result_validator import normalize_content_parse_result
from llm.gemini_service import GeminiService
from storage.services.transcript_service import TranscriptService
from video_processor.services.parser import extract_video_id
from features.content_parse.transcript_sample import build_transcript_sample


async def layer2_content_parse(
    transcript,
    video_info: dict,
    llm_service: GeminiService,
) -> dict:

    sample = build_transcript_sample(transcript)

    # ---------------------------------------------------------
    # Chapters
    # ---------------------------------------------------------

    chapters = video_info.get("chapters") or []

    chapters_text = ""

    if chapters:
        chapters_text = "CHAPTERS:\n" + "\n".join(
            f"  {chapter.get('start_time', 0):.0f}s — " f"{chapter.get('title', '')}"
            for chapter in chapters
        )

    # ---------------------------------------------------------
    # Video metadata
    # ---------------------------------------------------------

    title = video_info.get("title") or "Unknown"
    duration = video_info.get("duration") or 0

    # ---------------------------------------------------------
    # Prompt
    # ---------------------------------------------------------

    prompt = build_content_parser_prompt(
        title=title,
        duration=duration,
        chapters_text=chapters_text,
        transcript_sample=sample,
    )

    # ---------------------------------------------------------
    # LLM call
    # ---------------------------------------------------------

    result = await llm_service.generate(
        prompt=prompt,
        max_tokens=10000,
        temperature=0.2,
        json_output=True,
    )

    result = normalize_content_parse_result(result)

    # ---------------------------------------------------------
    # Sanitize Mermaid
    # ---------------------------------------------------------

    result["knowledge_graph_mermaid"] = clean_mermaid(result["knowledge_graph_mermaid"])

    return result


if __name__ == "__main__":

    url = input("Enter the URL: ").strip()

    if not url:
        print("URL cannot be empty")
        exit(1)

    id = extract_video_id(url)
    print(f"Video ID: {id}")

    llm_service = GeminiService()

    # transcript_service = YoutubeTranscriptService()

    # transcript = transcript_service.fetch_transcript(id)

    transcript_service = TranscriptService()
    transcript = transcript_service.get(id)

    video_info = transcript.video_info

    layer2_result = asyncio.run(
        layer2_content_parse(
            transcript=transcript,
            video_info=video_info,
            llm_service=llm_service,
        )
    )

    print(json.dumps(layer2_result, indent=2))
