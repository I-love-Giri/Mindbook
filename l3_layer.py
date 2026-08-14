import asyncio
import json
import logging
from typing import Any

from l2_layer import layer2_content_parse
from llm.groq_service import LLMService
from storage.services.transcript_service import TranscriptService
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


def build_mermaid(nodes: list, edges: list) -> str:
    """
    Build Mermaid graph from structured nodes and edges.

    The LLM is responsible for deciding the graph.
    Python is responsible for rendering it.
    """

    if not nodes:
        return ""

    lines = ["graph TD"]

    # ---------------------------------------------------------
    # Nodes
    # ---------------------------------------------------------

    for node in nodes:
        node_id = node.get("id", "").strip()
        label = node.get("label", "").strip()

        if not node_id or not label:
            continue

        # Mermaid-safe label
        label = (
            label.replace('"', "")
            .replace("'", "")
            .replace(":", " -")
            .replace("|", " -")
            .replace("(", "")
            .replace(")", "")
            .replace("[", "")
            .replace("]", "")
        )

        lines.append(f"    {node_id}[{label}]")

    # ---------------------------------------------------------
    # Edges
    # ---------------------------------------------------------

    valid_ids = {node.get("id") for node in nodes if node.get("id")}

    for edge in edges:
        source = edge.get("from")
        target = edge.get("to")

        if source not in valid_ids:
            continue

        if target not in valid_ids:
            continue

        lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


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

        You are building a semantic knowledge graph from a YouTube video.

        Use ONLY information supported by the supplied metadata and transcript.

        Create 6-14 important nodes.

        Each node:
        - id: letters, numbers, underscores only
        - label
        - type
        - level

        Levels:
        0 = central subject
        1 = major concepts/entities
        2 = supporting concepts/examples

        Create only meaningful semantic relationships.

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

        Do NOT connect every node to the root.
        Do NOT use "contains" merely because something belongs to the subject.
        Do not invent facts.

        Create a concept tree rooted at the central subject.

        Create a dependency_order representing the most useful learning sequence.

        DEPENDENCY ORDER RULES:

        dependency_order is NOT a list of all nodes.

        It represents only the conceptual prerequisites needed to understand
        the main ideas of the video.

        Do NOT include:
        - examples unless the example itself is necessary to understand
        another concept
        - people merely mentioned
        - books or sources
        - historical examples unless they introduce a concept required later

        Do include:
        - foundational concepts
        - definitions
        - mechanisms
        - principles
        - techniques that depend on earlier concepts

        The dependency order should normally contain 3-7 nodes.

        The first node should be the most foundational concept,
        not necessarily the root node.

        Every node ID must exist in the nodes array.

        Do not include a node simply because it exists in the graph.

        For example, if:

        n1 = Elicitation Definition
        n2 = Statements Instead of Questions
        n3 = Correction-Triggering Tactic
        n4 = Disbelief Technique
        n5 = Whole Foods Salary Example

        then a good dependency order is:

        [
            "n1",
            "n2",
            "n3",
            "n4"
        ]

        and NOT:

        [
            "n1",
            "n2",
            "n3",
            "n4",
            "n5"
        ]

        For non-technical content, the sequence may represent:

        background -> event -> causes -> consequences

        For technical content, it may represent:

        fundamentals -> concept -> mechanism -> implementation -> application

        If there is no meaningful dependency, return [].

        Return ONLY one valid JSON object.

        The object MUST contain:

            {{
                "nodes": [],
                "edges": [],
                "concept_tree": {{}},
                "dependency_order": []
            }}

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
                "n1",
                "n2",
                "n5",
                "n6",
                "n7"
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

        """print("RAW LAYER 3 RESULT:")
        print(repr(result))
        print("MERMAID BEFORE SANITIZE:")
        print(repr(result.get("mermaid", "")))"""

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

    # result["mermaid"] = _sanitize_mermaid(result.get("mermaid", ""))

    # ---------------------------------------------------------
    # Defensive defaults
    # ---------------------------------------------------------

    result.setdefault("nodes", [])
    result.setdefault("edges", [])
    result.setdefault("concept_tree", {})
    result.setdefault("dependency_order", [])

    # ---------------------------------------------------------
    # Validate dependency order
    # ---------------------------------------------------------

    valid_node_ids = {node.get("id") for node in result["nodes"] if node.get("id")}

    result["dependency_order"] = [
        node_id for node_id in result["dependency_order"] if node_id in valid_node_ids
    ]

    result["mermaid"] = build_mermaid(
        result.get("nodes", []),
        result.get("edges", []),
    )

    return result


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
