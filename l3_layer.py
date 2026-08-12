import asyncio
import json
import logging
from typing import Any

from l2_layer import layer2_content_parse
from llm.groq_service import LLMService
from video_processor.services.parser import extract_video_id
from video_processor.services.video_info import extract_chapters_and_info
from video_processor.services.youtube_service import YoutubeTranscriptService

logger = logging.getLogger(__name__)


def _extract_json(raw: str) -> dict:
    """
    Extract a JSON object from an LLM response.

    Handles responses wrapped in ```json ... ``` fences.
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
        logger.warning("Failed to parse Layer 3 LLM response as JSON")

    return {}


def _sanitize_mermaid(mermaid: str) -> str:
    """
    Basic cleanup for Mermaid output.
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


def _build_transcript_sample(transcript, max_chars: int = 4000) -> str:
    """
    Build a representative transcript sample.

    Uses:
        - beginning
        - middle
        - ending

    while preserving timestamps.
    """

    n = len(transcript)

    if n == 0:
        return ""

    if n <= 160:
        sample_segments = transcript

    else:
        head = transcript[:60]

        mid_start = max(0, n // 2 - 20)
        middle = transcript[mid_start : mid_start + 40]

        tail = transcript[-60:]

        sample_segments = head + middle + tail

    parts = []

    current_length = 0

    for segment in sample_segments:

        text = getattr(segment, "text", "") or ""

        if not text:
            continue

        start = getattr(segment, "start", 0)

        line = f"[{start:.1f}s] {text}"

        if current_length + len(line) > max_chars:
            break

        parts.append(line)
        current_length += len(line)

    return "\n".join(parts)


async def layer3_knowledge_graph(
    layer2_result: dict,
    transcript,
    video_info: dict,
    llm_service: LLMService,
) -> dict:
    """
    Build a semantic knowledge graph from Layer 2 metadata.

    Inputs
    ------

    layer2_result:
        Output produced by layer2_content_parse().

    transcript:
        Transcript object returned by YoutubeTranscriptService.

    video_info:
        Metadata returned by extract_chapters_and_info().

    llm_service:
        Existing LLMService instance.

    Returns
    -------

    {
        "nodes": [...],
        "edges": [...],
        "concept_tree": {...},
        "dependency_order": [...],
        "mermaid": "graph TD ..."
    }
    """

    # ---------------------------------------------------------
    # Layer 2 data
    # ---------------------------------------------------------

    overall_topic = layer2_result.get("overall_topic", "")

    domain = layer2_result.get("domain", "")

    content_type = layer2_result.get("content_type", "")

    prerequisites = layer2_result.get("prerequisites", [])

    entities = layer2_result.get("key_entities", [])

    topics = layer2_result.get("topics", [])

    learning_objectives = layer2_result.get(
        "learning_objectives",
        [],
    )

    # ---------------------------------------------------------
    # Limit entities
    # ---------------------------------------------------------

    entity_names = [
        entity.get("name", "") for entity in entities[:20] if entity.get("name")
    ]

    # ---------------------------------------------------------
    # Topics
    # ---------------------------------------------------------

    topic_text = "\n".join(
        f"- {topic.get('title', '')}: " f"{topic.get('summary', '')}"
        for topic in topics[:15]
        if topic.get("title")
    )

    # ---------------------------------------------------------
    # Chapters
    # ---------------------------------------------------------

    chapters = video_info.get("chapters") or []

    chapters_text = ""

    if chapters:
        chapters_text = "\n".join(
            f"- {chapter.get('start_time', 0):.0f}s: " f"{chapter.get('title', '')}"
            for chapter in chapters[:20]
        )

    # ---------------------------------------------------------
    # Transcript sample
    # ---------------------------------------------------------

    transcript_sample = _build_transcript_sample(
        transcript,
        max_chars=4000,
    )

    # ---------------------------------------------------------
    # Prompt
    # ---------------------------------------------------------

    prompt = f"""
You are building a knowledge graph for a YouTube video.

VIDEO:
"{video_info.get('title', '')}"

DOMAIN:
{domain}

CONTENT TYPE:
{content_type}

OVERALL TOPIC:
{overall_topic}

PREREQUISITES:
{json.dumps(prerequisites, ensure_ascii=False)}

KEY ENTITIES:
{json.dumps(entity_names, ensure_ascii=False)}

TOPICS:
{topic_text}

LEARNING OBJECTIVES:
{json.dumps(learning_objectives, ensure_ascii=False)}

CHAPTERS:
{chapters_text or "No chapters available."}

TRANSCRIPT SAMPLE:
{transcript_sample}

Your task is to build a compact semantic knowledge graph.

The graph should represent the most important concepts and entities
in the video and how they relate to each other.

This may be:

- technical
- scientific
- historical
- political
- economic
- geographical
- educational
- business
- social
- current affairs

Adapt the node types and relationships to the actual subject.

Do NOT assume the video is technical.

Only use information supported by the Layer 2 metadata or transcript.

Do not invent concepts, people, events, relationships, or dependencies.

==================================================
NODE RULES
==================================================

Create 6-14 important nodes.

Every node must have:

- id
- label
- type
- level

Node IDs must contain only:

letters, numbers, and underscores.

Examples:

n1
n2
central_topic
economic_factor

Never use spaces or punctuation in IDs.

Possible node types include:

concept
event
person
place
organization
policy
principle
tool
algorithm
law
movement
example
cause
effect
topic

Use the most appropriate type for the actual content.

"level" represents conceptual depth:

0 = central topic
1 = major concepts/entities
2 = supporting concepts/examples

==================================================
EDGE RULES
==================================================

Create only meaningful relationships.

Allowed relations:

requires
enables
contains
contrasts
extends
caused
led_to
influences
opposes
part_of
depends_on
implements
explains
demonstrates
example_of
results_in

Do not create an edge merely because two concepts were mentioned
near each other.

==================================================
CONCEPT TREE
==================================================

Create a hierarchical view of the knowledge.

The root should represent the central subject.

Branches should represent major areas discussed in the video.

==================================================
DEPENDENCY ORDER
==================================================

Determine a useful learning order.

This means:

what should a viewer understand first,
what should they understand next,
and what depends on those concepts?

For a historical video this might represent:

background -> event -> causes -> consequences

For a technical video it might represent:

fundamentals -> concept -> implementation -> application

Do not force artificial dependencies.

==================================================
MERMAID RULES
==================================================

The "mermaid" field MUST start with:

graph TD

Use one edge per line.

Example:

graph TD
    n1[Root] --> n2[Concept]
    n1 --> n3[Concept2]
    n2 --> n4[Example]

Node IDs must match the IDs in the nodes array.

Labels:

- use square brackets
- do not use parentheses
- do not use quotes
- do not use pipe characters
- avoid colons
- replace problematic punctuation with a dash

Keep the Mermaid graph small and readable.

Do not use subgraphs.

==================================================
OUTPUT
==================================================

Return ONLY valid JSON.

{{
    "nodes": [
        {{
            "id": "n1",
            "label": "Central Concept",
            "type": "concept",
            "level": 0
        }}
    ],

    "edges": [
        {{
            "from": "n1",
            "to": "n2",
            "relation": "explains"
        }}
    ],

    "concept_tree": {{
        "root": "Central Concept",
        "branches": [
            {{
                "name": "Major Topic",
                "children": [
                    "Supporting Concept"
                ]
            }}
        ]
    }},

    "dependency_order": [
        "Understand the central concept",
        "Understand the supporting concept",
        "Understand the application or consequence"
    ],

    "mermaid": "graph TD\\n    n1[Central Concept] --> n2[Supporting Concept]"
}}
"""

    # ---------------------------------------------------------
    # LLM call
    # ---------------------------------------------------------

    try:
        result = await llm_service.generate(
            prompt=prompt,
            max_tokens=1800,
            temperature=0.1,
            json_output=True,
        )

    except Exception as exc:
        logger.exception(
            "Layer 3 knowledge graph generation failed: %s",
            exc,
        )

        return {
            "nodes": [],
            "edges": [],
            "concept_tree": {},
            "dependency_order": [],
            "mermaid": "",
        }

    # ---------------------------------------------------------
    # Parse response
    # ---------------------------------------------------------

    if isinstance(result, str):
        result = _extract_json(result)

    if not isinstance(result, dict):
        return {
            "nodes": [],
            "edges": [],
            "concept_tree": {},
            "dependency_order": [],
            "mermaid": "",
        }

    # ---------------------------------------------------------
    # Sanitize Mermaid
    # ---------------------------------------------------------

    result["mermaid"] = _sanitize_mermaid(result.get("mermaid", ""))

    # ---------------------------------------------------------
    # Defensive defaults
    # ---------------------------------------------------------

    result.setdefault("nodes", [])
    result.setdefault("edges", [])
    result.setdefault("concept_tree", {})
    result.setdefault("dependency_order", [])

    return result


if __name__ == "__main__":

    url = input("Enter the URL: ").strip()

    if not url:
        print("URL cannot be empty")
        exit(1)

    id = extract_video_id(url)
    print(f"Video ID: {id}")

    llm_service = LLMService()

    transcript_service = YoutubeTranscriptService()

    transcript = transcript_service.fetch_transcript(id)

    video_info = extract_chapters_and_info(id)

    layer2_result = asyncio.run(
        layer2_content_parse(
            transcript=transcript,
            video_info=video_info,
            llm_service=llm_service,
        )
    )

    # print(json.dumps(layer2_result, indent=2))

    # video_info = extract_chapters_and_info(video_id)

    # transcript = YoutubeTranscriptService().fetch_transcript(video_id)

    """

    layer2 = await layer2_content_parse(
        transcript=transcript,
        video_info=video_info,
        llm_service=llm_service,
    )
    """

    layer3_result = asyncio.run(
        layer3_knowledge_graph(
            layer2_result=layer2_result,
            transcript=transcript.segments,
            video_info=video_info,
            llm_service=llm_service,
        )
    )

    print(json.dumps(layer3_result, indent=2))
