import json


def build_knowledge_graph_prompt(
    layer2_result: dict,
    transcript_sample: str,
    video_info: dict,
) -> str:

    # ---------------------------------------------------------
    # Layer 2 data
    # ---------------------------------------------------------

    overall_topic = layer2_result.get("overall_topic", "")
    domain = layer2_result.get("domain", "")
    content_type = layer2_result.get("content_type", "")

    prerequisites = layer2_result.get("prerequisites", [])
    entities = layer2_result.get("key_entities", [])
    topics = layer2_result.get("topics", [])
    learning_objectives = layer2_result.get("learning_objectives", [])

    # ---------------------------------------------------------
    # Limit entities
    # ---------------------------------------------------------

    entity_names = [
        entity.get("name", "")
        for entity in entities[:20]
        if isinstance(entity, dict) and entity.get("name")
    ]

    # ---------------------------------------------------------
    # Topics
    # ---------------------------------------------------------

    topic_text = "\n".join(
        f"- {topic.get('title', '')}: {topic.get('summary', '')}"
        for topic in topics[:15]
        if isinstance(topic, dict) and topic.get("title")
    )

    # ---------------------------------------------------------
    # Chapters
    # ---------------------------------------------------------

    chapters = video_info.get("chapters") or []

    chapters_text = "\n".join(
        f"- {chapter.get('start_time', 0):.0f}s: {chapter.get('title', '')}"
        for chapter in chapters[:20]
        if isinstance(chapter, dict)
    )

    return f"""
You are an expert knowledge-graph designer.

Your task is to construct a compact, semantically meaningful knowledge graph
representing the important concepts taught, explained, demonstrated, or
connected in a YouTube video.

The graph will be consumed programmatically, so correctness, consistency,
non-redundancy, and valid references are more important than verbosity.

==================================================
SOURCE MATERIAL
==================================================

VIDEO TITLE:
{video_info.get("title", "")}

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
{topic_text or "No topic information available."}

LEARNING OBJECTIVES:
{json.dumps(learning_objectives, ensure_ascii=False)}

CHAPTERS:
{chapters_text or "No chapters available."}

TRANSCRIPT SAMPLE:
{transcript_sample or "No transcript sample available."}

==================================================
CORE RULE
==================================================

Use ONLY information supported by the supplied metadata and transcript.

Do not invent:
- facts
- relationships
- definitions
- causes
- motivations
- conclusions
- examples
- technical mechanisms
- historical details

If something is uncertain or unsupported, leave it out.

The transcript may be incomplete. Do not assume that omitted portions of the
video contain information that is not present in the supplied material.

==================================================
GRAPH SIZE
==================================================

Create between 6 and 14 nodes.

Prefer fewer high-quality nodes over many weak or redundant nodes.

Every node should represent a concept, entity, process, principle, technique,
event, or example that is genuinely useful for understanding the video's
content.

Do not create nodes merely to increase the node count.

==================================================
NODE TYPES
==================================================

Each node must have exactly one of these types:

- concept
- entity
- process
- principle
- technique
- event
- example
- technology

Choose the type that best describes the semantic role of the node.

Do not create separate nodes for trivial wording variations of the same idea.

==================================================
NODE LEVELS
==================================================

Each node must have one level:

0 = central subject of the video
1 = major concepts, mechanisms, entities, or themes
2 = supporting concepts, techniques, examples, or details

There should normally be exactly one level-0 node.

The level-0 node should represent the main subject being explained,
not simply the video title unless the title itself represents the subject.

==================================================
NODE ID RULES
==================================================

Every node must have a unique ID.

IDs must:
- contain only ASCII letters, numbers, and underscores
- contain no spaces
- contain no hyphens
- contain no punctuation
- be short and stable

Use IDs such as:

n1
n2
n3

Do not use semantic IDs such as:

machine_learning_basics

unless necessary.

==================================================
NODE QUALITY RULES
==================================================

A good node should answer at least one of these questions:

- What is the main subject?
- What major concept explains the subject?
- What mechanism is important?
- What principle is taught?
- What technique is introduced?
- What entity is essential to the explanation?
- What event is necessary to understand the argument?
- What example is particularly important?

Avoid:
- filler
- generic words such as "information"
- duplicate concepts
- vague nodes such as "important idea"
- nodes representing sentences rather than concepts
- insignificant names mentioned only in passing

==================================================
RELATIONSHIPS
==================================================

Create only meaningful semantic relationships.

Allowed relations are:

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

The direction of the relationship matters.

For example:

A explains B

must be represented as:

A -> B

when A is the concept doing the explaining.

Use the most semantically precise relation available.

Do not create multiple relationships between the same pair of nodes unless
each relationship represents genuinely different information.

Do not create relationships merely because two nodes appear in the same video.

Do not connect every node to the root.

Do not use "contains" simply because one concept is broadly related to another.

==================================================
GRAPH STRUCTURE
==================================================

The graph should have a clear conceptual hierarchy.

The level-0 node is the central subject.

Level-1 nodes should represent the major ideas required to understand
the subject.

Level-2 nodes should represent supporting concepts, mechanisms, techniques,
examples, or details.

The graph does NOT need to be a strict tree.

It may contain cross-connections when those connections are explicitly
supported by the source material.

Avoid creating a dense "everything connects to everything" graph.

A useful graph normally has:
- 1 central node
- several major concepts
- a smaller number of supporting concepts
- only meaningful cross-connections

==================================================
CONCEPT TREE
==================================================

Create a hierarchical concept tree describing how the major ideas are
organized.

The concept tree must reference node IDs rather than node labels.

The root must be the ID of the level-0 node.

Every child must be an existing node ID.

Do not invent tree nodes that do not exist in the nodes array.

The concept tree does not require every graph edge to correspond to a
tree relationship.

Represent it as:

"concept_tree": {{
    "root": "n1",
    "children": {{
        "n1": ["n2", "n3"],
        "n2": ["n4", "n5"]
    }}
}}

Only include meaningful parent-child relationships.

Nodes that do not naturally belong under another node may remain directly
under the root.

==================================================
DEPENDENCY ORDER
==================================================

Create a dependency_order representing the most useful conceptual sequence
for understanding the main ideas.

IMPORTANT:

dependency_order is NOT a list of all nodes.

It should normally contain only 3-7 nodes.

It should contain only concepts that materially help a learner understand
the main subject.

Include:
- foundational concepts
- important definitions
- prerequisite principles
- mechanisms
- concepts that another major concept depends upon
- techniques that require earlier understanding

Usually exclude:
- incidental people
- books and sources
- minor entities
- decorative details
- illustrative examples
- historical examples
- examples that do not provide necessary conceptual understanding

The first item should normally be the most foundational concept.

The central/root node does NOT have to be first.

For technical content, prefer:

fundamentals -> concept -> mechanism -> implementation -> application

For non-technical explanatory content, a useful sequence may be:

background -> event -> cause -> mechanism -> consequence

For argumentative content, it may be:

problem -> premise -> evidence -> mechanism -> conclusion

Only use a sequence when the relationships actually support it.

If there is no meaningful conceptual dependency, return:

[]

Every dependency_order ID must exist in nodes.

Do not include a node merely because it exists in the graph.

==================================================
DEPENDENCY ORDER EXAMPLE
==================================================

Suppose the graph contains:

n1 = Central Subject
n2 = Foundational Definition
n3 = Core Principle
n4 = Mechanism
n5 = Advanced Technique
n6 = Illustrative Example

A good dependency order could be:

[
    "n2",
    "n3",
    "n4",
    "n5"
]

Do NOT automatically include n6 simply because it is a node.

==================================================
MERMAID
==================================================

Also generate a Mermaid diagram representing the graph.

Use:

graph TD

Use node IDs exactly as they appear in the nodes array.

Use the node label as the Mermaid display text.

Represent graph edges using the relationship direction.

Example:

graph TD
    n1["Central Subject"] -->|explains| n2["Core Concept"]
    n2["Core Concept"] -->|requires| n3["Foundation"]

Escape or simplify labels when necessary so the Mermaid remains valid.

The Mermaid diagram must represent the actual nodes and edges returned in
the JSON.

Do not create Mermaid nodes or edges that are absent from the JSON graph.

==================================================
CONSISTENCY REQUIREMENTS
==================================================

Before producing the final answer, internally verify:

1. There are 6-14 nodes.
2. Every node has id, label, type, and level.
3. Every node ID is unique.
4. Every node type is one of the allowed types.
5. Every level is 0, 1, or 2.
6. There is normally exactly one level-0 node.
7. Every edge.from exists in nodes.
8. Every edge.to exists in nodes.
9. Every edge.relation is allowed.
10. Every dependency_order ID exists in nodes.
11. concept_tree.root exists in nodes.
12. Every concept_tree child ID exists in nodes.
13. No unsupported facts were introduced.
14. No duplicate or trivial nodes were created.
15. The dependency_order contains only meaningful prerequisites.
16. Mermaid uses only valid node IDs and returned edges.
17. The final response is valid JSON.

==================================================
OUTPUT FORMAT
==================================================

Return ONLY one valid JSON object.

Do not return:
- Markdown
- code fences
- explanations
- comments
- introductory text
- trailing text

The JSON must have exactly these top-level fields:

{{
    "nodes": [],
    "edges": [],
    "concept_tree": {{}},
    "dependency_order": [],
    "mermaid": ""
}}

The expected structure is:

{{
    "nodes": [
        {{
            "id": "n1",
            "label": "Central Subject",
            "type": "concept",
            "level": 0
        }},
        {{
            "id": "n2",
            "label": "Major Concept",
            "type": "principle",
            "level": 1
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
        "root": "n1",
        "children": {{
            "n1": ["n2"]
        }}
    }},

    "dependency_order": [
        "n2"
    ],

    "mermaid": "graph TD\\n    n1[Central Subject] -->|explains| n2[Major Concept]"
}}

==================================================
FINAL INSTRUCTION
==================================================

Think carefully about the semantic structure before producing the JSON.

Do not optimize for the number of nodes or edges.

Optimize for:

1. conceptual usefulness
2. factual grounding
3. meaningful hierarchy
4. meaningful dependencies
5. low redundancy
6. machine-readable consistency

Return ONLY the final JSON object.
"""
