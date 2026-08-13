import json
import logging
from typing import Any
import asyncio
from llm.groq_service import LLMService
from storage.services.transcript_service import TranscriptService
from video_processor.services.parser import extract_video_id
from video_processor.services.video_info import extract_chapters_and_info
from video_processor.services.youtube_service import YoutubeTranscriptService

logger = logging.getLogger(__name__)


def _extract_json(raw: str) -> dict:
    """
    Extract a JSON object from an LLM response.

    Handles responses where the model accidentally wraps JSON
    in ```json ... ``` fences.
    """
    if not raw:
        return {}

    raw = raw.strip()

    # Remove markdown code fences
    if raw.startswith("```"):
        lines = raw.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        raw = "\n".join(lines).strip()

    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON")
        return {}


def _sanitize_mermaid(mermaid: str) -> str:
    """
    Basic cleanup for Mermaid output.

    Keeps the function defensive because LLM-generated Mermaid
    can contain formatting that breaks rendering.
    """
    if not mermaid:
        return ""

    mermaid = mermaid.strip()

    if mermaid.startswith("```"):
        lines = mermaid.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        mermaid = "\n".join(lines).strip()

    return mermaid


async def layer2_content_parse(
    transcript,
    video_info: dict,
    llm_service: LLMService,
) -> dict:
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

    segments = transcript.segments
    n = len(segments)

    # ---------------------------------------------------------
    # Select transcript sample
    # ---------------------------------------------------------

    if n <= 300:
        sample_segments = segments

    else:
        head = segments[:100]

        mid_start = max(0, n // 2 - 50)
        mid_end = min(n, n // 2 + 50)

        mid = segments[mid_start:mid_end]
        tail = segments[-100:]

        sample_segments = head + mid + tail

    # ---------------------------------------------------------
    # Preserve timestamps
    # ---------------------------------------------------------

    sample = "\n".join(
        f"[{segment.start:.1f}s] {segment.text}"
        for segment in sample_segments
        if segment.text
    )

    sample = sample[:5000]

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

    prompt = f"""
Analyze this YouTube video transcript carefully.

VIDEO:
"{title}"

DURATION:
{duration:.0f} seconds

{chapters_text}

TRANSCRIPT SAMPLE:
{sample}

Extract structured metadata.

Return a JSON object with exactly these fields:

{{
    "content_type": "tutorial|lecture|demo|review|vlog|interview|course|documentary|analysis|explainer|news|debate",

    "difficulty": "beginner|intermediate|advanced",

    "domain": "Main knowledge domain. Be specific.",

    "overall_topic": "One precise sentence describing what this video is about.",

    "prerequisites": [
        "knowledge required before understanding this video"
    ],

    "key_entities": [
        {{
            "name": "entity name",
            "type": "concept|tool|person|place|country|organization|event|policy|law|movement|ideology|algorithm|library|framework",
            "importance": importance must be an integer from 1 to 5
        }}
    ],

    "topics": [
        {{
            "title": "Topic title",
            "start_approx": 0,
            "summary": "1-2 sentence summary"
        }}
    ],

    "learning_objectives": [
        "After watching this, viewers will understand..."
    ],

    "knowledge_graph_mermaid": "graph TD\\n A[concept] --> B[concept]"
}}

Rules:

- Only include information supported by the transcript.
- Do not hallucinate entities.
- Use chapter timestamps when available.
- If chapters are unavailable, infer approximate timestamps
  using transcript timestamps.
- Identify meaningful sections rather than tiny topic changes.
- Keep the knowledge graph focused on the most important concepts.


Entity Entity importance must be scored from 1 to 5:
   - 5 = central to the video's subject
   - 4 = very important
   - 3 = moderately important
   - 2 = minor supporting entity
   - 1 = briefly mentioned

- Only include entities that are actually supported by the transcript.
- Do not create entities merely because they are implied.

PREREQUISITE RULES:

- Only include knowledge genuinely necessary to understand the video.
- Do not include generic or optional background knowledge.
- Return an empty list if no prerequisites are necessary.

Return valid JSON only.



"""

    # ---------------------------------------------------------
    # LLM call
    # ---------------------------------------------------------

    result = await llm_service.generate(
        prompt=prompt,
        max_tokens=1500,
        temperature=0.2,
        json_output=True,
    )

    # ---------------------------------------------------------
    # Sanitize Mermaid
    # ---------------------------------------------------------

    result["knowledge_graph_mermaid"] = _sanitize_mermaid(
        result.get("knowledge_graph_mermaid", "")
    )

    return result


"""
    # ---------------------------------------------------------
    # 7. Safe fallback
    # ---------------------------------------------------------

    return {
        "content_type": "tutorial",
        "difficulty": "intermediate",
        "domain": title,
        "overall_topic": title,
        "prerequisites": [],
        "key_entities": [],
        "topics": [],
        "learning_objectives": [],
        "knowledge_graph_mermaid": "",
    }
"""

if __name__ == "__main__":

    url = input("Enter the URL: ").strip()

    if not url:
        print("URL cannot be empty")
        exit(1)

    id = extract_video_id(url)
    print(f"Video ID: {id}")

    llm_service = LLMService()

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
