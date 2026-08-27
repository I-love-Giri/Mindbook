from types import SimpleNamespace

from features.content_parse.mermaid import clean_mermaid
from features.content_parse.result_validator import (
    normalize_content_parse_result,
)
from features.content_parse.transcript_sample import (
    build_transcript_sample,
)


def test_clean_mermaid_removes_code_fence():
    raw_mermaid = """```mermaid
graph TD
A[Python] --> B[Variables]
```"""

    result = clean_mermaid(raw_mermaid)

    assert result == "graph TD\nA[Python] --> B[Variables]"


def test_validator_adds_safe_defaults():
    raw_result = {
        "content_type": "tutorial",
        "overall_topic": "Python basics",
        "topics": "This should have been a list",
    }

    result = normalize_content_parse_result(raw_result)

    assert result["content_type"] == "tutorial"
    assert result["overall_topic"] == "Python basics"
    assert result["topics"] == []
    assert result["prerequisites"] == []
    assert result["knowledge_graph_mermaid"] == ""


def test_transcript_sample_keeps_timestamps():
    transcript = SimpleNamespace(
        segments=[
            SimpleNamespace(start=0.0, text="Welcome to Python."),
            SimpleNamespace(start=8.5, text="Variables store values."),
        ]
    )

    result = build_transcript_sample(transcript)

    assert result == ("[0.0s] Welcome to Python.\n" "[8.5s] Variables store values.")


import asyncio

from l2_layer import layer2_content_parse


class FakeLLM:
    def __init__(self):
        self.last_request = None

    async def generate(self, **kwargs):
        self.last_request = kwargs

        return {
            "content_type": "tutorial",
            "difficulty": "beginner",
            "domain": "Programming",
            "overall_topic": "An introduction to Python variables.",
            "prerequisites": [],
            "key_entities": [],
            "topics": [],
            "learning_objectives": ["Understand what variables are."],
            "knowledge_graph_mermaid": """```mermaid
graph TD
A[Python] --> B[Variables]
```""",
        }


def test_layer2_runs_with_a_fake_llm():
    transcript = SimpleNamespace(
        segments=[
            SimpleNamespace(
                start=0.0,
                text="Welcome to a lesson about Python variables.",
            ),
            SimpleNamespace(
                start=10.0,
                text="Variables let us store information.",
            ),
        ]
    )

    video_info = {
        "title": "Python Variables for Beginners",
        "duration": 120,
        "chapters": [],
    }

    fake_llm = FakeLLM()

    result = asyncio.run(
        layer2_content_parse(
            transcript=transcript,
            video_info=video_info,
            llm_service=fake_llm,
        )
    )

    assert result["content_type"] == "tutorial"
    assert result["difficulty"] == "beginner"
    assert result["knowledge_graph_mermaid"] == ("graph TD\nA[Python] --> B[Variables]")

    assert fake_llm.last_request["json_output"] is True
    assert "Python Variables for Beginners" in fake_llm.last_request["prompt"]
    assert "Welcome to a lesson about Python variables." in (
        fake_llm.last_request["prompt"]
    )


def test_long_transcript_uses_beginning_middle_and_ending():
    transcript = SimpleNamespace(
        segments=[
            SimpleNamespace(
                start=float(index),
                text=f"Segment {index}",
            )
            for index in range(301)
        ]
    )

    result = build_transcript_sample(transcript, max_chars=10_000)

    assert "[0.0s] Segment 0" in result
    assert "[99.0s] Segment 99" in result

    assert "[100.0s] Segment 100" in result
    assert "[150.0s] Segment 150" in result
    assert "[199.0s] Segment 199" in result

    assert "[201.0s] Segment 201" in result
    assert "[300.0s] Segment 300" in result

    assert "[200.0s] Segment 200" not in result
