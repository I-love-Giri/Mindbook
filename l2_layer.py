import json
import logging
from typing import Any

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
    api_key: str,
) -> dict:
    """
    Analyze a YouTube transcript and video metadata using an LLM.

    `transcript` is the Transcript object returned by
    YoutubeTranscriptService.fetch_transcript().

    `video_info` is the dictionary returned by
    extract_chapters_and_info().

    Extracts:
        - content type
        - difficulty
        - domain
        - overall topic
        - prerequisites
        - key entities
        - inferred topics/sections
        - learning objectives
        - knowledge graph in Mermaid format
    """

    # ---------------------------------------------------------
    # 1. Get transcript segments
    # ---------------------------------------------------------

    segments = transcript.segments

    n = len(segments)

    # ---------------------------------------------------------
    # 2. Sample transcript intelligently
    # ---------------------------------------------------------
    #
    # For short videos:
    #     use everything
    #
    # For long videos:
    #     beginning + middle + end
    #
    # This prevents sending an enormous transcript to the LLM.
    # ---------------------------------------------------------

    if n <= 300:
        sample_segments = segments
    else:
        head = segments[:100]

        middle_start = max(0, n // 2 - 50)
        middle_end = min(n, n // 2 + 50)

        mid = segments[middle_start:middle_end]

        tail = segments[-100:]

        sample_segments = head + mid + tail

    sample = " ".join(segment.text for segment in sample_segments if segment.text)

    # Keep prompt size under control.
    sample = sample[:5000]

    # ---------------------------------------------------------
    # 3. Build chapter information
    # ---------------------------------------------------------

    chapters_text = ""

    chapters = video_info.get("chapters") or []

    if chapters:
        chapters_text = "CHAPTERS:\n" + "\n".join(
            f"  {chapter.get('start_time', 0):.0f}s — " f"{chapter.get('title', '')}"
            for chapter in chapters
        )

    # ---------------------------------------------------------
    # 4. Build LLM prompt
    # ---------------------------------------------------------

    title = video_info.get("title") or "Unknown"
    duration = video_info.get("duration") or 0

    prompt = f"""
Analyze this YouTube video transcript carefully.

VIDEO: "{title}"
DURATION: {duration:.0f}s

{chapters_text}

TRANSCRIPT SAMPLE:
{sample}

Extract structured metadata.

Return ONLY valid JSON. Do not use markdown.
Do not wrap the JSON in ```json fences.

The JSON must have exactly this structure:

{{
  "content_type": "tutorial|lecture|demo|review|vlog|interview|course|documentary|analysis|explainer|news|debate",
  "difficulty": "beginner|intermediate|advanced",

  "domain": "Main knowledge domain. Be specific and accurate.",

  "overall_topic": "One precise sentence describing what this video is actually about.",

  "prerequisites": [
    "knowledge or concept the viewer should already understand"
  ],

  "key_entities": [
    {{
      "name": "entity name",
      "type": "concept|tool|person|place|country|organization|event|policy|law|movement|ideology|algorithm|library|framework",
      "importance": 1
    }}
  ],

  "topics": [
    {{
      "title": "Topic or section title",
      "start_approx": 0,
      "summary": "1-2 sentence summary of this section"
    }}
  ],

  "learning_objectives": [
    "After watching this, viewers will understand..."
  ],

  "knowledge_graph_mermaid": "graph TD\\n A[concept] --> B[concept]"
}}

Rules:

1. Only include entities that are actually supported by the transcript.
2. Do not hallucinate people, organizations, technologies, events, or concepts.
3. Use the chapter timestamps when they provide useful section boundaries.
4. If chapters are unavailable, infer approximate topic timestamps from the transcript.
5. Keep topics meaningful rather than creating a topic for every small subject change.
6. Keep the number of key entities reasonable.
7. The knowledge graph should contain the most important concepts and relationships.
8. Return raw JSON only.
"""

    # ---------------------------------------------------------
    # 5. Call your existing LLM helper
    # ---------------------------------------------------------

    raw = await call_text(
        [{"role": "user", "content": prompt}],
        api_key,
        max_tokens=1500,
        fast=False,
    )

    # ---------------------------------------------------------
    # 6. Parse response
    # ---------------------------------------------------------

    result = _extract_json(raw)

    if isinstance(result, dict) and result:
        result["knowledge_graph_mermaid"] = _sanitize_mermaid(
            result.get("knowledge_graph_mermaid", "")
        )

        return result

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
