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
    sections: list[dict],
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

    else:

        block_types = """
Allowed block types:

- heading
- paragraph
- table
- callout
"""

    # --------------------------------------------------
    # Build transcript for ALL chunks
    # --------------------------------------------------

    sections_text = ""

    for section in sections:

        sections_text += f"""
==================================================
CHUNK ID:
{section["chunk_id"]}

SECTION TITLE:
{section["title"]}

SECTION TIMESTAMP:
{section["start_time"]:.2f}s - {section["end_time"]:.2f}s
==================================================

{section["transcript"]}

"""

    return f"""
You are an expert teacher and technical educator.

Your task is to turn ONE transcript section into a deep,
clear, and genuinely useful learning explanation.

You are NOT writing a transcript summary.

You are TEACHING the knowledge contained in the transcript.

Imagine that a student is reading your explanation instead of
watching this part of the video.

Your explanation should feel like a good teacher sitting beside
the student and saying:

"Let me first explain what this means.
Now let me show you why it matters.
Now let's understand how it works.
Now let's connect it to the example.
And finally, let's make sure the main idea is clear."

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

==================================================
TRANSCRIPT
==================================================

{sections_text}

==================================================
YOUR PRIMARY GOAL
==================================================

ULTIMATE FINAL OUTPUT GOAL: Write a clear, structured, teaching-quality explanation of what is actually covered —
think of it like the best textbook page, encyclopedia entry, or documentation for THIS specific
subject. Stay tightly grounded in the transcript; do not drift into unrelated territory.

For this chunk, produce a DEEP LEARNING EXPLANATION.

The goal is not to preserve the speaker's wording.

The goal is to preserve the KNOWLEDGE and make that knowledge
easy for a learner to understand.

A strong explanation should answer, whenever the transcript
provides enough information:

- What is this concept?
- What does it mean in simple language?
- Why is it important?
- How does it work?
- Why does it work?
- What problem does it solve?
- How are the different ideas connected?
- What example is being used?
- What does the example demonstrate?
- What would happen in the process?
- What important distinction should the learner understand?
- What is the main takeaway?

Do NOT force questions that are not relevant to the chunk.

CONTINUITY AND REPETITION RULES:

Treat the chunks as parts of ONE continuous lesson, not as
independent articles.

Each chunk should advance the learner's understanding.

Do NOT repeatedly reintroduce concepts that were already clearly
explained in earlier chunks.

For example, if an earlier chunk has already explained:

- what a decision tree is
- what decision nodes and leaf nodes are
- what x0 and x1 represent

then later chunks should normally refer to those ideas naturally
instead of defining them again.

Use short references such as:
"At this point, the tree..."
"Now the splitting process..."
"Once a split is chosen..."
rather than restarting the explanation.

Repeat a concept only when:

1. the current chunk introduces a new aspect of it,
2. a brief reminder is necessary for clarity, or
3. the transcript itself revisits the concept in a materially
   different way.

Prioritize NEW UNDERSTANDING over repeated BACKGROUND.

Every chunk should answer:
"What does this chunk teach that the learner did not already know?"

Avoid repetitive opening patterns such as:
"A decision tree is..."
"A decision tree is..."
"A decision tree is..."

Also avoid forcing every chunk to contain:
definition → why → how → example → takeaway.

The structure should follow the actual teaching progression of
the material.

==================================================
TEACHING PHILOSOPHY
==================================================

Teach progressively.

Do not immediately dump technical terminology on the learner.

When appropriate, follow this natural progression:

1. START WITH THE IDEA

Introduce the main concept in simple language.

The learner should understand the basic idea before seeing
technical details.

2. BUILD INTUITION

Explain what the concept means intuitively.

If the transcript provides an analogy, comparison, visualization,
or real-world explanation, use it.

3. EXPLAIN THE REASONING

Explain WHY the concept works or WHY it is useful when the
transcript provides that reasoning.

Do not merely state facts.

Explain the relationship between cause and effect.

4. EXPLAIN THE MECHANISM

If the transcript explains how something works, walk through
that mechanism clearly.

Break complicated processes into understandable steps.

5. USE THE EXAMPLE

If the transcript contains an example, do not merely mention it.

Explain:

- what the example is showing
- why the example was introduced
- how it demonstrates the concept
- what the learner should notice

6. CONNECT IDEAS

If the transcript connects this concept with another concept,
make that relationship explicit.

For example:

"Because X happens, Y becomes possible."

or:

"X is useful because it solves the limitation of Y."

7. END WITH THE IMPORTANT IDEA

Finish with the central insight when the chunk contains a
clear conclusion.



==================================================
DEPTH RULE
==================================================

Do not optimize for brevity.

Optimize for UNDERSTANDING.

A short transcript may naturally produce a short explanation.

A dense transcript should produce a sufficiently detailed
explanation covering the important ideas.

Do not artificially shorten an explanation merely because the
transcript is concise.

At the same time, do not repeat the same idea using different
words.

Every paragraph should either:

- introduce an important idea
- explain an idea
- explain why it matters
- explain how it works
- clarify a relationship
- explain an example
- resolve an important distinction
- provide a supported takeaway

==================================================
FRIENDLY TEACHING STYLE
==================================================

Use simple, natural language.

Prefer:

"Think of this as..."

"The important idea here is..."

"This matters because..."

"In simple terms..."

"The reason for this is..."

"For example..."

"This means that..."

when they naturally improve understanding.

Do not use these phrases mechanically.

The writing should feel natural, not like a fixed template.

Technical terminology should still be preserved when important.

When introducing an important technical term, explain it in
simple language before relying on it.

The result should be approachable WITHOUT becoming shallow.

==================================================
EXAMPLE POLICY
==================================================

{example_policy}

Follow this policy strictly.

If the transcript already contains an example, explain that
example deeply.

Do not invent examples unless the example policy explicitly
allows them.

==================================================
GROUNDING
==================================================

The transcript is the source of truth.

You may:

- reorganize ideas
- simplify wording
- clarify relationships
- explain reasoning already present
- combine closely related statements
- turn an implicit explanation into clearer teaching language

You may NOT introduce unsupported factual information.

Do not use outside knowledge to expand the topic.

If something is not sufficiently supported by the transcript,
do not guess.

Accuracy is more important than completeness.

==================================================
WHAT NOT TO DO
==================================================

Do NOT:

- mechanically paraphrase the transcript
- reproduce the transcript
- turn every sentence into a separate bullet
- create shallow one-paragraph summaries
- list concepts without explaining them
- mention "the video"
- mention "the speaker"
- mention "the creator"
- say "in this section"
- add unrelated background information
- invent facts
- invent examples
- invent formulas
- invent code
- fabricate quotations
- fabricate citations

Do not force every possible block type into the explanation.

==================================================
STRUCTURE
==================================================

Use a natural teaching structure.

A typical conceptual explanation may look like:

Heading:
What is the concept?

Paragraph:
Simple explanation.

Paragraph:
Intuition / meaning.

Heading:
Why does it matter?

Paragraph:
Reason or purpose supported by the transcript.

Heading:
How does it work?

Paragraph:
Mechanism or process.

Heading:
Example

Paragraph:
Explain the example and what it demonstrates.

Callout:
Important insight / common distinction / key takeaway.

However, DO NOT force this exact structure.

Choose the structure that best teaches the actual chunk.

For a process:

Goal
→ Step 1
→ Step 2
→ Step 3
→ Result

For a mathematical concept:

Concept
→ Meaning of variables
→ Reasoning
→ Worked example
→ Interpretation

For programming:

Concept
→ Why it is needed
→ How it works
→ Code
→ Expected behavior

For a comparison:

Concept A
→ Concept B
→ Difference
→ When each matters

==================================================
BLOCK TYPES
==================================================

Allowed block types:

{block_types}

HEADING:
Use for meaningful conceptual changes.

PARAGRAPH:
Use for detailed explanations, reasoning, mechanisms,
definitions, examples, and connections.

TABLE:
Use only when a comparison, classification, sequence,
or structured relationship genuinely becomes easier to understand
as a table.

CALLOUT:
Use for an especially important insight, warning, distinction,
reason, or takeaway supported by the transcript.

CODE:
Use only when genuinely supported programming content exists.

Do not use blocks merely to make the output look structured.

==================================================
IMPORTANT QUALITY RULE
==================================================

The explanation should NOT feel like:

"Here are the things mentioned in the transcript."

It should feel like:

"Now I understand what this concept means,
why it matters, and how it works."

Prioritize learner understanding over information density.

==================================================
KEY CONCEPTS
==================================================

Return 2-8 important concepts.

These are NOT a summary of every topic mentioned.

They should represent the concepts a learner should remember
after understanding this chunk.

==================================================
SKETCH NOTE
==================================================

Create a compact visual representation of the explanation.

title:
Maximum 5 words.

subtitle:
Exactly one sentence explaining the central idea.

boxes:
3-6 important ideas in logical order.

takeaway:
Exactly one sentence containing the most important insight.

The sketch note must contain only information supported by
the transcript.

==================================================
DIFFICULTY
==================================================

Return an integer from 1 to 5.

1 = very simple
2 = basic
3 = moderate
4 = advanced
5 = highly advanced

Base this on the actual conceptual difficulty of the chunk.

==================================================
FINAL SELF-CHECK
==================================================

Before returning the answer, verify:

1. The explanation actually teaches the concept.
2. The explanation is deeper than a simple summary.
3. Important WHY and HOW reasoning has been explained when supported.
4. Examples have been explained rather than merely mentioned.
5. Related ideas have been connected.
6. No unsupported facts have been introduced.
7. No unnecessary repetition exists.
8. The result is grounded in the transcript.
9. key_concepts contains 2-8 items.
10. sketch_note is concise and grounded.
11. difficulty_rating is between 1 and 5.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "results": [
        {{
            "chunk_id": 0,
            "blocks": [
                {{
                    "type": "heading",
                    "content": "Main Concept"
                }},
                {{
                    "type": "paragraph",
                    "content": "Detailed explanation..."
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
                    "Important idea",
                    "Important relationship",
                    "Important mechanism"
                ],
                "takeaway": "One memorable insight."
            }},
            "difficulty_rating": 3
        }}
    ]
}}

Return ONLY the JSON object.
"""
