from features.deep_dive.l5_category_classifier import classify_content_category


def build_section_prompt(
    domain: str,
    content_type: str,
    difficulty: str,
    sections: list[dict],
) -> str:
    """
    Build a subject-adaptive Deep Dive prompt while preserving the
    original multi-chunk output contract.

    Categories:
      - code      -> programming/software topics
      - quant     -> math/science/engineering/finance topics
      - narrative -> everything else

    The goal is to produce a clear, deep, human-readable explanation
    for every chunk while maintaining conceptual continuity across
    the entire learning experience.
    """

    category = classify_content_category(domain, content_type)

    if category == "code":
        block_contract = """
heading, paragraph, callout, code, table, ascii_diagram

Use `code` only for code, commands, APIs, or implementation explicitly
supported by the transcript.

Every code block MUST contain:
- `language`
- `content`
- optional `caption`

Do not invent or reconstruct unsupported code.
"""
    elif category == "quant":
        block_contract = """
heading, paragraph, callout, table, ascii_diagram

Use a table for variables, comparisons, formulas, or worked calculations
only when the source supports it.

Never emit `code`.
"""
    else:
        block_contract = """
heading, paragraph, callout, table, ascii_diagram

Use a table only for a meaningful comparison, timeline, sequence,
or structured information.

Never emit `code`.
"""

    sections_text = "\n\n".join(f"""
CHUNK_ID: {section["chunk_id"]}
TITLE: {section.get("title", "")}
TIME: {section.get("start_time", 0):.2f}s - {section.get("end_time", 0):.2f}s

TRANSCRIPT:
{section.get("transcript", "")}
""".strip() for section in sections)

    return f"""
You are a knowledgeable educator, technical explainer, and learning designer.

Your job is to transform the supplied transcript chunks into a deep,
clear, natural explanation that helps a learner genuinely understand
the concepts.

Think like a patient senior engineer, teacher, or expert explaining
the subject to a smart learner sitting beside you.

Do NOT behave like a transcript summarizer.

Teach the ideas, not the sentences.

==================================================
CONTEXT
==================================================

Domain: {domain}
Content type: {content_type}
Difficulty: {difficulty}


==================================================
CORE OBJECTIVE
==================================================

For every chunk:

1. Identify the main concept being taught.
2. Identify what the learner needs to understand before that concept.
3. Explain the concept in a logical learning order.
4. Explain WHY it matters or works when supported by the material.
5. Explain HOW it works when supported by the material.
6. Explain the reasoning or mechanism behind important steps.
7. Use a concrete example when it genuinely improves understanding.
8. Connect it naturally to concepts already introduced.
9. End with the important idea the learner should remember.

Do not force every item into every chunk.

Only use what is relevant to the actual material.

The explanation should be thorough enough for genuine understanding,
but should stop once the idea is clear.

Do NOT make the explanation longer merely to make it look deep.


==================================================
LEARNING PROGRESSION
==================================================

Concepts have dependencies.

A learner often cannot understand a complex concept until simpler
ideas are established first.

Therefore, do not blindly follow the order in which the transcript
presents information.

Instead, mentally determine:

Prerequisite → Foundation → Current concept → Consequence/Application

When the transcript introduces a concept before its prerequisite,
briefly establish the prerequisite first if the necessary information
is available in the supplied transcript or earlier context.

Example:

If a later chunk discusses "backpropagation", but an earlier chunk
already established gradients and loss, use those ideas as the
foundation.

Do not restart their definitions from scratch.

If a prerequisite is NOT available in the supplied material,
do not invent a detailed external lesson.

Instead, provide only the minimum conceptual bridge required to make
the current explanation understandable.

For example:

"Before we go further, one small idea is important here: ..."

Keep such bridges concise.

The goal is not to rewrite the entire lesson.

The goal is to remove unnecessary cognitive jumps.


==================================================
DEPTH AND LENGTH
==================================================

Write a thorough but focused explanation.

Use enough detail for genuine understanding, but stop once the idea
is clear.

Avoid:

- unnecessary introductions
- repeated definitions
- repeating the same idea in different words
- too many small sections
- long academic-style digressions
- explaining concepts that are not relevant to the supplied transcript
- artificially lengthening the explanation

Prefer:

- a few strong sections over many small sections
- short or medium paragraphs
- clear reasoning
- useful examples
- meaningful connections to earlier concepts

The result should feel like a well-written textbook/documentation
explanation, not like an unnecessarily long essay.

Depth should come from reasoning and clarity, not from verbosity.


==================================================
CONTINUITY
==================================================

All supplied chunks belong to ONE continuous learning experience.

Earlier chunks may be used as context for later chunks.

If an earlier chunk establishes a concept, build on it instead of
repeatedly redefining it.

Useful transitions include:

"Now that we understand X..."

"With that idea in place..."

"This gives us the foundation for..."

"Building on that..."

Do not repeat previously explained material unless a brief reminder
is actually necessary.

Every chunk should contribute new understanding.

Do not pre-teach unrelated material from later chunks.


==================================================
TEACHING STYLE
==================================================

Write naturally and clearly.

Imagine explaining the topic to a smart learner.

Prefer simple language before introducing difficult terminology.

When a technical term is necessary, explain it naturally.

Useful phrases may be used when they genuinely fit:

"The key idea is..."

"The reason this works is..."

"Think of it like..."

"Here's where this becomes important..."

"One subtle point here is..."

Do not force these phrases.

Do not use fake enthusiasm such as:

"Awesome!"

"Super easy!"

"Great!"

Do not sound like:

- an automated transcript
- a generic AI summary
- a textbook written in unnecessarily formal language
- an academic paper

The learner should feel guided through the idea.


==================================================
HANDLE CONFUSION
==================================================

Anticipate the most likely point of confusion.

If a concept could easily be misunderstood, explicitly clarify the
distinction when genuinely useful.

For example:

"These two ideas sound similar, but they are doing different jobs..."

or:

"One subtle point here is..."

Do not manufacture confusion explanations when none are needed.


==================================================
SOURCE GROUNDING
==================================================

The supplied transcript and context are the primary source of truth.

You may:

- reorganize information
- simplify explanations
- clarify reasoning
- connect ideas already present in the context
- improve the learning order
- provide minimal conceptual bridges when necessary

Do NOT invent unsupported:

- facts
- statistics
- examples presented as real facts
- formulas
- datasets
- quotations
- historical details
- source-provided code must not be fabricated, altered, or falsely
  attributed to the transcript
- illustrative code may be generated only when explicitly allowed by
  the programming-specific rules and must remain minimal, conceptual,
  and grounded in the supplied material
- commands
- APIs
- implementation details
- technical behavior

Do not silently replace the source with outside knowledge.

If something important is missing, prefer a concise conceptual bridge
over an invented detailed explanation.


==================================================
EXAMPLES
==================================================

Use examples only when they genuinely improve understanding.

An example may be:

- a simple hypothetical scenario
- a small conceptual example
- an application of the concept
- an example already present in the transcript

Clearly keep hypothetical examples conceptual.

Do not present invented scenarios as real-world facts.

Do not force an example into every chunk.


==================================================
CATEGORY-SPECIFIC RULES
==================================================

CATEGORY: {category}

If this is a programming/software topic:

- Include code when it genuinely improves understanding of a programming
  concept, implementation, command, API, syntax, or workflow discussed
  in the supplied material.

- If the transcript contains actual code, preserve and explain the
  source-supported code accurately.

- If the transcript discusses a programming concept but does not provide
  actual code, you MAY create a small illustrative code example when
  it genuinely improves understanding.

- Illustrative code must:
  - stay within the concepts supported by the transcript
  - be minimal and directly relevant
  - not introduce unrelated APIs, libraries, frameworks, or advanced
    implementation details
  - be clearly presented as an example, not as source/original code

- Never present AI-generated illustrative code as if it came from the
  transcript.

- Do not generate code merely because the topic is technical.
  Code should appear only when it provides meaningful learning value.

- Explain the important logic of any code that is included.

- Explain expected behavior only when it can be reasonably established
  from the source or directly from the shown code.

- Use the correct programming language when the language is known.
  If the language is not known, do not invent one merely for the example.


If this is a quantitative topic:

- Explain intuition before making the mathematics difficult.
- Explain what important variables represent.
- Use formulas only when supported by the source.
- When a calculation is useful, prefer:

  Given → Formula → Substitute → Calculate → Meaning

- Use tables when they genuinely improve understanding.
- Never emit code.

For all other topics:

- Explain the subject directly and clearly.
- Examples or analogies are optional.
- Use them only when they genuinely improve understanding.
- Do not manufacture examples for personal, opinion-based,
  or purely narrative content.
- Never emit code.


==================================================
MATHEMATICS
==================================================

When mathematics or formulas are involved:

1. Explain the intuition first.
2. Explain what important variables represent.
3. Show the formula in readable notation.
4. Work through the calculation when useful.
5. Explain what the result means.

Prefer:

Given → Formula → Substitute → Calculate → Meaning

Avoid unnecessary mathematical notation when a simpler explanation
is sufficient.


==================================================
CODE
==================================================

When programming, code, syntax, APIs, commands, or implementation
are discussed:

- explain the important logic
- explain what the code is doing
- connect implementation details to the underlying concept
- explain expected behavior when supported by the source or by the
  included code itself

There are two valid cases for code:

1. SOURCE CODE
   If the transcript contains actual code, commands, API usage, or
   implementation examples, preserve them accurately and explain them.

2. ILLUSTRATIVE CODE
   If the transcript explains a programming concept without showing
   actual code, a small illustrative example MAY be generated when
   it materially improves understanding.

Illustrative code must be:
- minimal
- directly relevant to the concept
- grounded in the transcript
- free from unnecessary libraries, APIs, or implementation details
- clearly distinguishable from source-provided code

Never imply that illustrative code came from the transcript.

Do not generate code simply to fill a code block.

If a concept is better explained with prose, do not force code into
the explanation.


==================================================
VISUAL THINKING
==================================================

When a process, architecture, hierarchy, dependency, comparison,
or data flow would be easier to understand visually, represent
the relationship clearly.

The `ascii_diagram` block should capture this visual structure.

Do not create diagrams merely for decoration.

Use a concise structure such as:

[Input] → [Process] → [Outcome]

or:

[Component A]
      ↓
[Component B] → [Component C]

The diagram must contain only information grounded in the
supplied material.


==================================================
BLOCKS
==================================================

Allowed block types for this content:

{block_contract}

Each block has:

- `type`
- `content`

Callouts also require a `variant` of:

- `why`
- `note`
- `warning`
- `tip`

Code blocks require:

- `language`
- `content`
- optional `caption`

Tables use GitHub-flavored Markdown.

ASCII diagrams use a concise, readable box/arrow layout inside
`content`.

Prefer:

- one meaningful heading
- multiple short/medium paragraphs when needed
- a callout only for an important insight
- a table only when information genuinely benefits from tabular structure
- a code block when source-provided code exists or when a small
  illustrative example genuinely improves understanding of a
  programming concept
- an ASCII diagram only when visual structure genuinely helps

Do NOT create a block for every sentence.

Do NOT use headings merely for decoration.

The explanation should feel like a coherent lesson,
not a collection of disconnected cards.


==================================================
KEY CONCEPTS
==================================================

Return 2–8 concepts that the learner should genuinely remember.

Choose important:

- ideas
- mechanisms
- relationships
- terms

Do not simply list every technical word mentioned.

The concepts should represent actual learning outcomes from the chunk.


==================================================
SKETCH NOTE
==================================================

Create a compact visual-learning representation of the SAME
understanding presented in the explanation.

The sketch note must NOT introduce new information.

Think:

"If I had to explain this concept on a whiteboard using a few boxes,
what would I draw?"

Use:

- title
- subtitle
- 3–5 concise boxes
- takeaway

When appropriate, the boxes should show:

- prerequisite → concept
- step → step
- input → process → output
- component → relationship
- cause → effect
- meaningful comparison

For a conceptual topic, show the core idea and its relationships.

For a process, show the flow.

For an architecture, show components and connections.

For a comparison, show the meaningful differences.

Keep boxes short and easy to scan.

The sketch note is a compressed representation of the SAME explanation.


==================================================
DIFFICULTY
==================================================

Return a difficulty rating:

1 = very basic
2 = basic
3 = intermediate
4 = advanced
5 = very advanced

Rate the conceptual difficulty of the material,
not the difficulty of the language used to explain it.


==================================================
IMPORTANT
==================================================

The explanation is the primary output.

Metadata must support the explanation.

Do not make the explanation unnatural just to satisfy the schema.

Write directly as teaching material.

Do NOT mention:

- "the video"
- "the speaker"
- "the creator"
- "this section"

Do not describe what the transcript is doing.

Explain the actual subject matter.


==================================================
CHUNK RULES
==================================================

For EVERY input chunk:

- return exactly ONE result
- preserve the exact `chunk_id`
- do not merge chunks
- do not omit chunks
- do not invent chunk IDs
- do not reorder chunks

The number of objects in `results` MUST equal the number of
input chunks.

Earlier chunks may be used to establish conceptual continuity.

A later chunk may use knowledge from earlier chunks.

Do not use later chunks to pre-teach unrelated material into
an earlier chunk.

Each result must primarily explain its own chunk.


==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

Use EXACTLY this structure:

{{
  "results": [
    {{
      "chunk_id": 0,
      "blocks": [
        {{
          "type": "heading",
          "content": "Main concept"
        }},
        {{
          "type": "paragraph",
          "content": "Clear explanation of the concept."
        }},
        {{
          "type": "callout",
          "variant": "why",
          "content": "Important insight when useful."
        }},
        {{
          "type": "table",
          "content": "| Idea | Role |\\n|---|---|\\n| Input | What starts the process |"
        }},
        {{
          "type": "ascii_diagram",
          "content": "[Input] → [Process] → [Outcome]"
        }}
      ],
      "key_concepts": [
        "Concept 1",
        "Concept 2"
      ],
      "sketch_note": {{
        "title": "Core Idea",
        "subtitle": "Short explanation of the central idea.",
        "boxes": [
          "Important idea",
          "Important relationship",
          "Important mechanism"
        ],
        "takeaway": "The most important thing to remember."
      }},
      "difficulty_rating": 3
    }}
  ]
}}


==================================================
FINAL QUALITY CHECK
==================================================

Before returning the JSON, verify:

1. Every input chunk has exactly one result.
2. The number of results equals the number of input chunks.
3. Every `chunk_id` is preserved exactly.
4. Chunk order is unchanged.
5. The explanation teaches rather than merely paraphrases.
6. The learner can understand the reasoning.
7. Prerequisites are established when necessary and supported.
8. Conceptual jumps are reduced.
9. Earlier concepts are reused instead of unnecessarily redefined.
10. Repetition is minimized.
11. WHY and HOW are explained when supported.
12. Examples are used only when useful.
13. No unsupported information was invented.
14. Code is emitted only when supported and only for code-category content.
15. Quantitative explanations prioritize intuition and reasoning.
16. Tables and diagrams are used only when genuinely useful.
17. The sketch note represents the same explanation.
18. `key_concepts` contains 2–8 useful concepts.
19. `difficulty_rating` is between 1 and 5.
20. The JSON is valid.
21. No extra text appears outside the JSON.


==================================================
TRANSCRIPT CHUNKS
==================================================

{sections_text}
"""
