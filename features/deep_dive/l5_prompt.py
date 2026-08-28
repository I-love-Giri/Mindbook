from features.deep_dive.l5_category_classifier import classify_content_category

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


def build_section_prompt(
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
Allowed block types:
- heading
- paragraph
- code
- table
- callout
"""

    elif category == "quant":
        block_types = """
Allowed block types:
- heading
- paragraph
- table
- callout
"""

    else:
        block_types = """
Allowed block types:
- heading
- paragraph
- table
- callout
"""

    return f"""
You are an expert educator and technical writer creating a
self-contained knowledge-base explanation of one section of a video.

Your job is NOT to summarize the transcript mechanically.

Your job is to identify the actual knowledge in the transcript and
explain it clearly, accurately, and structurally.

==================================================
SOURCE INFORMATION
==================================================

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


==================================================
TRANSCRIPT
==================================================

{transcript_text}


==================================================
SOURCE OF TRUTH
==================================================

The transcript is the primary source of truth.

Use only information that is explicitly stated or clearly implied
by the supplied transcript.

You may reorganize, clarify, simplify, and explain ideas from the
transcript, but you must not introduce unsupported factual claims.

Do NOT use outside knowledge to add facts.

If the transcript is incomplete, ambiguous, contradictory, or too
limited to support a claim, do not guess.

When information is insufficient, prefer a shorter accurate explanation
over a more complete but speculative explanation.


==================================================
PRIMARY OBJECTIVE
==================================================

Create an explanation that can stand on its own as a knowledge-base
article.

A reader should be able to understand the important knowledge from
this section without listening to the original audio.

Focus on:

1. What is being taught?
2. What are the important concepts?
3. How do the concepts relate to one another?
4. Why does something work or matter, when the transcript supports this?
5. What process, mechanism, reasoning, or sequence is being explained?
6. What conclusions or takeaways are explicitly supported?


==================================================
EXPLANATION RULES
==================================================

- Explain ideas rather than merely paraphrasing sentences.
- Preserve the meaning of the transcript.
- Prefer precise explanations over generic statements.
- Explain cause-and-effect relationships when supported.
- Explain mechanisms when the transcript provides them.
- Preserve important qualifications and limitations.
- Preserve important numbers, conditions, and constraints exactly.
- Preserve technical terminology when it is important.
- Define specialized terminology when the transcript provides enough
  information to define it.
- Organize related ideas together.
- Remove conversational filler and repetition.
- Do not repeat the transcript word-for-word.
- Do not unnecessarily follow the transcript's speaking order.
- Do not mention "the video".
- Do not mention "the creator".
- Do not mention "the speaker".
- Do not say "in this section".
- Do not refer to yourself.
- Do not add unrelated background information.


==================================================
ANTI-HALLUCINATION RULES
==================================================

Never invent:

- facts
- statistics
- dates
- names
- citations
- references
- quotations
- examples
- analogies
- formulas
- technical details
- code
- commands
- APIs
- implementation details
- historical context

unless they are supported by the supplied transcript.

Do not complete missing code.

Do not "correct" the speaker using outside knowledge.

If the transcript contains a claim that appears technically questionable,
preserve it as presented rather than silently replacing it with outside
knowledge.

You may improve wording and structure, but not factual content.


==================================================
EXAMPLE POLICY
==================================================

{example_policy}

Follow the example policy exactly.

Examples must never be invented unless the policy explicitly allows
them and the example is directly supported by the transcript.

When examples are present in the transcript, explain their purpose
when that purpose is clear from the transcript.


==================================================
BLOCK TYPES
==================================================

{block_types}

Use blocks to structure the explanation.

HEADING:
Use for major conceptual subsections only.

Do not create a heading for every paragraph.

PARAGRAPH:
Use for explanations, definitions, reasoning, mechanisms, and narrative
content.

CODE:
Use only for programming content and only when the transcript genuinely
contains or directly describes the code.

Never invent, complete, or reconstruct missing code.

TABLE:
Use only when information naturally benefits from structured comparison,
classification, properties, steps, or other tabular organization.

Do not create a table merely for visual variety.

CALLOUT:
Use for an especially important principle, warning, definition,
constraint, or takeaway explicitly supported by the transcript.

Do not overuse callouts.


==================================================
CONTENT STRUCTURE
==================================================

For most sections:

- Start with a heading when the section contains a distinct major idea.
- Follow with explanatory paragraphs.
- Add additional headings only when the topic genuinely changes.
- Use tables only when they improve comprehension.
- Use callouts sparingly.
- Use code only when directly supported by programming content.

Do not force every available block type into the output.

For a short transcript, produce a concise explanation.

For a dense transcript, produce enough blocks to cover the important
knowledge without unnecessary repetition.


==================================================
KEY CONCEPTS
==================================================

Extract the most important concepts represented in this section.

Return 2-8 concepts.

Each concept must:

- be supported by the transcript
- be meaningful for understanding the section
- be concise
- not duplicate another concept
- not be a generic word such as "information", "topic", or "idea"

Prefer concepts such as:

- important definitions
- principles
- mechanisms
- techniques
- processes
- entities
- problems
- solutions
- important relationships

Do not include minor details simply because they were mentioned.


==================================================
SKETCH NOTE
==================================================

Create a compact visual-learning representation of the section.

The sketch note must be grounded entirely in the transcript.

"title":
- maximum 5 words
- concise
- represents the central idea

"subtitle":
- exactly one sentence
- summarizes the central idea

"boxes":
- 3-6 items
- each item should contain one important idea
- keep each item concise
- order them logically

"takeaway":
- exactly one sentence
- memorable but factually grounded
- must reflect an important idea from the transcript

Do not introduce new information in the sketch note.


==================================================
DIFFICULTY RATING
==================================================

difficulty_rating represents how difficult the concepts in this section
are for the intended learner.

Return an integer from 1 to 5.

1 = very simple / introductory
2 = basic
3 = moderate
4 = advanced
5 = highly advanced / technically or conceptually difficult

Base the rating on the actual content, terminology, abstraction,
reasoning, and prerequisites present in the transcript.

Do not simply copy the input difficulty value.


==================================================
OUTPUT VALIDATION
==================================================

Before returning the answer, verify internally that:

1. The output is valid JSON.
2. There is exactly one top-level JSON object.
3. The top-level fields are exactly:
   - blocks
   - key_concepts
   - sketch_note
   - difficulty_rating
4. Every block has:
   - type
   - content
5. Every block type is allowed for the current content category.
6. Code blocks appear only for programming content.
7. Code is never invented or completed.
8. key_concepts contains 2-8 items.
9. sketch_note.title contains no more than 5 words.
10. sketch_note.subtitle is one sentence.
11. sketch_note.boxes contains 3-6 items.
12. sketch_note.takeaway is one sentence.
13. difficulty_rating is an integer from 1 to 5.
14. No unsupported facts have been introduced.
15. No citations or quotations have been fabricated.
16. No unnecessary repetition exists.


==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

Do not return:

- Markdown
- code fences
- explanations
- introductory text
- comments
- trailing text

Use exactly this structure:

{{
    "blocks": [
        {{
            "type": "heading",
            "content": "Major Concept"
        }},
        {{
            "type": "paragraph",
            "content": "Explanation of the concept."
        }}
    ],

    "key_concepts": [
        "Concept 1",
        "Concept 2",
        "Concept 3"
    ],

    "sketch_note": {{
        "title": "Core Idea",
        "subtitle": "One sentence explaining the central idea.",
        "boxes": [
            "Important point",
            "Important relationship",
            "Important mechanism"
        ],
        "takeaway": "One memorable insight supported by the transcript."
    }},

    "difficulty_rating": 3
}}

Return ONLY the JSON object.
"""
