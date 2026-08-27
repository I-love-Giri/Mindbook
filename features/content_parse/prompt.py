def build_content_parser_prompt(
    title: str, duration: float, chapters_text: str, transcript_sample: str
) -> str:

    return f"""
You are a content analysis engine.

Analyze the provided YouTube video metadata, chapters, and transcript sample.
Extract structured metadata strictly from the information supported by the input.

VIDEO TITLE:
{title}

VIDEO DURATION:
{duration:.0f} seconds

CHAPTERS:
{chapters_text if chapters_text else "No chapters available."}

TRANSCRIPT SAMPLE:
{transcript_sample}

IMPORTANT EVIDENCE RULES:
- Use ONLY information explicitly supported by the provided input.
- Do NOT rely on outside knowledge, assumptions, or the video title alone.
- Do NOT hallucinate people, tools, concepts, organizations, events, laws, or other entities.
- The transcript may be only a SAMPLE of the full transcript. Do not assume that unseen parts of the video contain information that is not present in the provided input.
- If the available evidence is insufficient to determine something confidently, use a reasonable empty value rather than guessing.
- Prefer precision over completeness.

OUTPUT:
Return exactly one valid JSON object with exactly these fields and no additional fields:

{{
  "content_type": "tutorial",
  "difficulty": "beginner",
  "domain": "Main knowledge domain",
  "overall_topic": "One precise sentence describing what this video is mainly about.",
  "prerequisites": [],
  "key_entities": [
    {{
      "name": "Entity name",
      "type": "concept",
      "importance": 5
    }}
  ],
  "topics": [
    {{
      "title": "Topic title",
      "start_approx": 0,
      "summary": "1-2 sentence summary of this section."
    }}
  ],
  "learning_objectives": [
    "Explain ...",
    "Understand ...",
    "Identify ..."
  ],
  "knowledge_graph_mermaid": "graph TD\\n    A[Concept A] --> B[Concept B]"
}}

FIELD RULES:

1. content_type
Choose exactly ONE of:
- tutorial
- lecture
- demo
- review
- vlog
- interview
- course
- documentary
- analysis
- explainer
- news
- debate

Choose based on the primary purpose and structure of the content.

2. difficulty
Choose exactly ONE:
- beginner
- intermediate
- advanced

Use the apparent level of knowledge required to follow the content.

Guidelines:
- beginner = assumes little or no prior knowledge
- intermediate = assumes basic familiarity
- advanced = requires substantial prior knowledge or deals with technically/ conceptually complex material

Do not infer difficulty merely from the presence of technical terminology.

3. domain
Return one specific knowledge domain.

Examples:
- software engineering
- machine learning
- cybersecurity
- personal finance
- history
- economics
- physics
- biology
- psychology
- marketing
- cooking

Avoid overly broad values such as "technology" when a more specific domain is supported.

4. overall_topic
Write exactly ONE concise sentence explaining the main subject of the video.

It should describe what the viewer is actually learning, understanding, watching, or discussing.

5. prerequisites
List only knowledge that is genuinely necessary to understand the content.

Examples:
[
  "Basic Python programming",
  "Understanding of linear algebra"
]

If no prerequisites are clearly necessary, return:
[]

Do not list generic requirements such as:
- "attention"
- "basic intelligence"
- "watching the video"
- "internet access"

6. key_entities
Extract only meaningful entities that are explicitly supported by the input.

Allowed entity types:
- concept
- tool
- person
- place
- country
- organization
- event
- policy
- law
- movement
- ideology
- algorithm
- library
- framework

Each entity must have:
- name: canonical/common name
- type: exactly one allowed type
- importance: integer from 1 to 5

Importance:
- 5 = central to the video's subject
- 4 = very important
- 3 = moderately important
- 2 = minor supporting entity
- 1 = briefly mentioned

Rules:
- Deduplicate entities.
- Do not include generic words as entities.
- Do not include an entity merely because it appears in the title unless the transcript/chapter evidence supports its relevance.
- Prefer canonical names when clearly supported.
- Do not invent entity types.

7. topics
Identify meaningful sections of the video.

Rules:
- Return topics in chronological order.
- Use chapter timestamps when available.
- If chapters are unavailable, infer approximate timestamps only from transcript timestamps provided in the input.
- start_approx must be a number representing seconds from the beginning of the video.
- The first meaningful topic should normally start at or near 0.
- Do not create a topic for every small change in subject.
- Merge closely related discussion into one topic.
- Avoid duplicate or overlapping topics.
- Each topic should represent a meaningful section of the video.
- If there is not enough evidence for multiple sections, return fewer topics.
- Do not invent timestamps.

Each topic must contain:
- title
- start_approx
- summary

The summary should be 1-2 concise sentences and contain only information supported by the input.

8. learning_objectives
Return 2-6 concise learning objectives when enough information is available.

Objectives should describe what a viewer can understand or do after watching the content.

Prefer action-oriented wording such as:
- "Explain how ..."
- "Understand why ..."
- "Identify the differences between ..."
- "Describe the process of ..."
- "Apply ..."

Do not write vague objectives such as:
- "Learn about the topic"
- "Understand the video"
- "Know more about X"

If the input is insufficient to determine learning objectives, return [].

9. knowledge_graph_mermaid
Create a small, focused Mermaid knowledge graph containing only the most important concepts/entities supported by the input.

Requirements:
- Use Mermaid flowchart syntax beginning with:
  graph TD
- Focus on the most important relationships.
- Prefer 3-10 nodes.
- Do not include every entity.
- Do not invent relationships.
- Relationships must be supported or strongly implied by the provided content.
- Node IDs must be simple alphanumeric identifiers such as A, B, C1.
- Keep node labels concise.
- Avoid Mermaid syntax characters inside labels when possible.
- Escape the Mermaid string correctly for JSON.
- If there is insufficient information to build a meaningful graph, return:
  "graph TD"

FINAL VALIDATION:
Before returning the response, verify that:
- The output is valid JSON.
- There are exactly 9 top-level fields.
- All required commas, quotes, brackets, and braces are present.
- No markdown code fences are included.
- No explanatory text appears before or after the JSON.
- content_type contains exactly one allowed value.
- difficulty contains exactly one allowed value.
- importance values are integers from 1 to 5.
- start_approx values are numbers representing seconds.
- key_entities are deduplicated.
- topics are chronologically ordered.
- No unsupported facts have been added.

Return valid JSON only.
"""
