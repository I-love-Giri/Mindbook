from typing import Literal
from pydantic import BaseModel, Field


class KeyEntity(BaseModel):
    name: str
    type: Literal[
        "concept",
        "tool",
        "person",
        "place",
        "country",
        "organization",
        "event",
        "policy",
        "law",
        "movement",
        "ideology",
        "algorithm",
        "library",
        "framework",
    ]
    importance: int = Field(ge=1, le=5)


class Topic(BaseModel):
    title: str
    start_approx: int = Field(ge=0)
    summary: str


class ContentParserResult(BaseModel):
    content_type: Literal[
        "tutorial",
        "lecture",
        "demo",
        "review",
        "vlog",
        "interview",
        "course",
        "documentary",
        "analysis",
        "explainer",
        "news",
        "debate",
    ]

    difficulty: Literal[
        "beginner",
        "intermediate",
        "advanced",
    ]

    domain: str
    overall_topic: str
    prerequisites: list[str]
    key_entities: list[KeyEntity]
    topics: list[Topic]
    learning_objectives: list[str]
    knowledge_graph_mermaid: str
