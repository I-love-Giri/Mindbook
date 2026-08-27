import asyncio

from l3_layer import layer3_knowledge_graph
from types import SimpleNamespace


class FakeLLM:
    def __init__(self):
        self.last_request = None

    async def generate(self, **kwargs):
        self.last_request = kwargs

        return {
            "nodes": [
                {
                    "id": "python",
                    "label": "Python",
                    "type": "concept",
                },
                {
                    "id": "variables",
                    "label": "Variables",
                    "type": "concept",
                },
            ],
            "edges": [
                {
                    "source": "python",
                    "target": "variables",
                    "relation": "has",
                }
            ],
            "dependency_order": [
                "python",
                "variables",
            ],
        }


def test_layer3_runs_with_a_fake_llm():
    transcript = SimpleNamespace(
        segments=[
            SimpleNamespace(
                start=0.0,
                text="Welcome to Python variables.",
            ),
            SimpleNamespace(
                start=10.0,
                text="Variables store information.",
            ),
        ]
    )

    layer2_result = {
        "content_type": "tutorial",
        "domain": "Programming",
        "overall_topic": "Python variables",
        "topics": [],
        "key_entities": [],
    }

    video_info = {
        "title": "Python Variables for Beginners",
        "duration": 120,
        "chapters": [],
    }

    fake_llm = FakeLLM()

    result = asyncio.run(
        layer3_knowledge_graph(
            layer2_result=layer2_result,
            transcript=transcript,
            video_info=video_info,
            llm_service=fake_llm,
        )
    )

    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1

    assert result["nodes"][0]["label"] == "Python"

    assert fake_llm.last_request["json_output"] is True

    assert "Python Variables for Beginners" in (fake_llm.last_request["prompt"])

    assert "Welcome to Python variables." in (fake_llm.last_request["prompt"])
