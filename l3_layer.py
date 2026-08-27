import asyncio
import json
import logging

from features.knowledge_graph.l3_mermaid import build_mermaid
from features.knowledge_graph.l3_prompt import build_knowledge_graph_prompt
from features.knowledge_graph.l3_transcript_layer import build_transcript_sample
from features.knowledge_graph.l3_validator import normalize_knowledge_graph_result
from llm.groq_service import LLMService
from storage.services.transcript_service import TranscriptService
from video_processor.services.parser import extract_video_id

logger = logging.getLogger(__name__)


"""def _extract_json(raw: str) -> dict:
    ""
    Extract a JSON object from an LLM response.

    Handles responses wrapped in ```json ... ``` fences.
    ""

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

    return {}"""


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
    # Transcript sample
    # ---------------------------------------------------------

    transcript_sample = build_transcript_sample(
        transcript,
        max_chars=4000,
    )

    # ---------------------------------------------------------
    # Prompt
    # ---------------------------------------------------------

    prompt = build_knowledge_graph_prompt(layer2_result, transcript_sample, video_info)

    # ---------------------------------------------------------
    # LLM call
    # ---------------------------------------------------------

    try:
        result = await llm_service.generate(
            prompt=prompt,
            max_tokens=3000,
            temperature=0.1,
            json_output=True,
        )

        """
        print("RAW LAYER 3 RESULT:")
        print(repr(result))
        print("MERMAID BEFORE SANITIZE:")
        print(repr(result.get("mermaid", "")))
        """

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

    """if isinstance(result, str):
        result = _extract_json(result)

    if not isinstance(result, dict):
        return {
            "nodes": [],
            "edges": [],
            "concept_tree": {},
            "dependency_order": [],
            "mermaid": "",
        }

    """

    result = normalize_knowledge_graph_result(result)

    result["mermaid"] = build_mermaid(
        result.get("nodes", []),
        result.get("edges", []),
    )

    return result


from l2_layer import layer2_content_parse

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
