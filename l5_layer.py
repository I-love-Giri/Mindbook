import json
import logging
from typing import Any, Dict, Optional, Tuple

from l2_layer import layer2_content_parse
from llm.groq_service import LLMService

logger = logging.getLogger(__name__)


CODE_DOMAIN_KEYWORDS = {
    "programming",
    "code",
    "coding",
    "software",
    "software engineering",
    "web dev",
    "web development",
    "backend",
    "frontend",
    "database",
    "devops",
    "cybersecurity",
    "networking",
    "cloud computing",
    "algorithm",
    "data structures",
    "framework",
    "library",
    "app development",
    "machine learning",
    "deep learning",
    "data science",
    "artificial intelligence",
}


QUANT_DOMAIN_KEYWORDS = {
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
    "science",
    "astronomy",
    "thermodynamics",
    "mechanics",
    "geology",
    "neuroscience",
    "medicine",
}


NARRATIVE_CONTENT_TYPES = {
    "vlog",
    "interview",
    "documentary",
    "news",
    "debate",
    "review",
    "podcast",
    "story",
}


def _extract_json(raw: str) -> dict:
    if not raw:
        return {}

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
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Failed to parse L5 JSON response")
        return {}


def classify_content_category(
    domain: str,
    content_type: str,
) -> str:

    domain_l = (domain or "").lower()
    content_type_l = (content_type or "").lower()

    if content_type_l in NARRATIVE_CONTENT_TYPES:
        return "narrative"

    if any(keyword in domain_l for keyword in CODE_DOMAIN_KEYWORDS):
        return "code"

    if any(keyword in domain_l for keyword in QUANT_DOMAIN_KEYWORDS):
        return "quant"

    return "narrative"


EXAMPLE_POLICY = {
    "code": """
Include a code example ONLY when the transcript explicitly discusses
code, syntax, commands, APIs, implementation, or a programming pattern.

Do NOT invent code for a conceptual explanation.

If code is genuinely supported by the transcript:
- Explain what it does.
- Explain the important design decision.
- Mention expected behavior/output when supported.
- Do not pretend reconstructed code is exact source code.
""",
    "quant": """
Include a worked numerical or formula example ONLY when it helps
explain the concept.

Use examples that are directly supported by the transcript or are
simple applications of the exact concept being explained.

Never use programming code blocks.
""",
    "narrative": """
Prioritize explanation over examples.

Use an analogy, comparison, timeline, or illustrative case ONLY when
it genuinely improves understanding.

Do not manufacture events, statistics, quotations, motivations,
examples, or historical details that are not supported by the source.
""",
}


def _build_section_prompt(
    domain: str,
    content_type: str,
    difficulty: str,
    section_title: str,
    start_time: float,
    end_time: float,
    transcript_text: str,
) -> str:

    category = classify_content_category(
        domain,
        content_type,
    )

    example_policy = EXAMPLE_POLICY[category]

    if category == "code":
        block_types = """
- heading
- paragraph
- code
- table
- callout
"""

    elif category == "quant":
        block_types = """
- heading
- paragraph
- table
- callout
"""

    else:
        block_types = """
- heading
- paragraph
- table
- callout
"""

    return f"""
You are a knowledgeable educator creating a deep explanation of one
section of a video.

VIDEO DOMAIN:
{domain}

CONTENT TYPE:
{content_type}

DIFFICULTY:
{difficulty}

CONTENT CATEGORY:
{category}

SECTION TITLE:
{section_title}

SECTION TIMESTAMP:
{start_time:.2f}s - {end_time:.2f}s


TRANSCRIPT
----------

{transcript_text}


PRIMARY OBJECTIVE
-----------------

Explain the actual knowledge contained in this transcript section.

The transcript is the primary source of truth.

Do not invent facts that are not supported by the transcript.

The goal is a self-contained explanation that someone could read later
without needing to listen to the original section.


EXAMPLE POLICY
--------------

{example_policy}


WRITING RULES
-------------

- Explain concepts clearly and directly.
- Explain WHY something works or matters when the transcript supports it.
- Prefer precise explanations over generic filler.
- Do not repeat the transcript word-for-word.
- Do not mention "the video".
- Do not mention "the creator".
- Do not mention "the speaker".
- Do not say "in this section".
- Do not refer to yourself.
- Do not introduce unrelated background information.
- Do not manufacture examples.
- Do not manufacture statistics.
- Do not manufacture citations.
- Do not manufacture code.
- Do not manufacture quotations.

The output should be useful as a knowledge-base article.


BLOCK TYPES
-----------

{block_types}

For programming content, a "code" block is allowed only when the
transcript genuinely supports the code or implementation being discussed.

For non-programming content, never use a "code" block.


OUTPUT FORMAT
-------------

Return ONLY valid JSON.

{{
    "blocks": [
        {{
            "type": "heading",
            "content": "..."
        }},
        {{
            "type": "paragraph",
            "content": "..."
        }}
    ],

    "key_concepts": [
        "concept 1",
        "concept 2"
    ],

    "sketch_note": {{
        "title": "Maximum five words",
        "subtitle": "One sentence summary",
        "boxes": [
            "Key point",
            "Key point",
            "Key point"
        ],
        "takeaway": "One memorable insight"
    }},

    "difficulty_rating": 1
}}

difficulty_rating must be an integer from 1 to 5.

Raw JSON only.
"""


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

    start_time = chunk.get("start", 0)
    end_time = chunk.get("end", start_time)

    prompt = _build_section_prompt(
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
            max_tokens=2800,
            temperature=0.2,
            json_output=True,
        )

        result = raw if isinstance(raw, dict) else _extract_json(raw)

        if result:
            return result

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

    print("\nRunning L2...\n")

    l2_result = asyncio.run(
        layer2_content_parse(
            transcript=transcript,
            video_info=video_info,
            llm_service=llm_service,
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
    # Select one chunk
    # ---------------------------------------------------------

    choice = input("\nEnter chunk number to analyze [0]: ").strip()

    try:
        index = int(choice) if choice else 0
    except ValueError:
        index = 0

    if index < 0 or index >= len(chunks):
        print("Invalid chunk number")
        exit(1)

    chunk = chunks[index]

    print("\nSELECTED CHUNK")
    print("=" * 80)

    print(json.dumps(chunk, indent=2, ensure_ascii=False))

    # ---------------------------------------------------------
    # L5
    # ---------------------------------------------------------

    print("\nRunning L5...\n")

    l5_result = asyncio.run(
        layer5_deep_dive(
            chunk=chunk,
            video_info=video_info,
            parsed=l2_result,
            llm_service=llm_service,
        )
    )

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------

    print("\n")
    print("=" * 80)
    print("L5 RESULT")
    print("=" * 80)

    print(
        json.dumps(
            l5_result,
            indent=2,
            ensure_ascii=False,
        )
    )
