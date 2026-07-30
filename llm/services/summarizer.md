---

## Initial Strategy (Version 1)

Sequential Map-Reduce Implementation:

LLMs have a limit on how much text they can process in one request (their context window). If you try to summarize a very long transcript directly, it may exceed that limit or become inefficient.

Map-reduce solves this by:

Splitting the transcript into manageable chunks.
Summarizing each chunk separately (map phase).
Combining those summaries into one coherent final summary (reduce phase).
This approach scales well for long meeting transcripts, books, interviews, or documents.

Transcript
│
Split into chunks
│
Chunk 1 ──► LLM ──► Summary 1
(wait)
Chunk 2 ──► LLM ──► Summary 2
(wait)
Chunk 3 ──► LLM ──► Summary 3
(wait)
...

│
Combine all summaries ──► LLM ──► final Summary
│
Final Summary

Example with Real Data
Suppose you have a transcript split into three chunks:

chunks = [
"Alice discussed project planning...",
"Bob explained the backend implementation...",
"The team finalized deadlines..."
]

Map phase:

Chunk 1 → "Project goals and planning were discussed."
Chunk 2 → "Backend architecture and APIs were explained."
Chunk 3 → "Deadlines and action items were finalized."
These are collected into:

partial_summaries = [
"Project goals and planning were discussed.",
"Backend architecture and APIs were explained.",
"Deadlines and action items were finalized."
]

Reduce phase:

The combined prompt asks the LLM to merge these into a single summary, producing something like:

"The meeting focused on project planning, reviewed the backend architecture, and concluded with agreed deadlines and action items."

So the class performs two rounds of LLM calls:

One call per chunk to create partial summaries.
One final call to merge those partial summaries into a coherent overall summary.

---

## Problems :

1. Sequential Processing (Slowest Problem)

for chunk in chunks:
summary = self.summarize_chunk(chunk)

Each chunk waits for the previous one to finish.

Suppose:

10 chunks
each LLM request takes 3 seconds
Timeline:

Chunk 1 → 3 sec
Chunk 2 → 3 sec
Chunk 3 → 3 sec
...
Chunk 10 → 3 sec

Total: 30 seconds

So Version 1 wastes a lot of time waiting on network requests.

---

2. Single Large Reduce Step

merged_summaries = "\n\n".join(partial_summaries)

final_prompt = self.combine_prompt.substitute(
summaries=merged_summaries
)

Every partial summary is placed into one prompt.

Imagine:

100 chunks

Each summary is 250 words

Total: 100 x 250 = 25,000 words

That may exceed the model's context window.

Possible consequences:

API rejects the request
prompt gets truncated
model produces poor summaries

---

3. Not Scalable

Suppose you summarize 5 chunks => No problem.

Suppose you summarize 500 chunks

Now, 500 summaries

must fit into one prompt.

That becomes impractical.

---

4. Poor Separation of Responsibilities

Version 1 contains logic like

prompt = self.summary_prompt.substitute(...)

directly inside summarize()

The method is doing many jobs:

building prompts
calling the LLM
storing summaries
merging summaries

---

5. Harder to Test
   Suppose you want to test only the prompt construction.

Version 1:

You have to run

summarize()

which also calls the LLM.

You can't easily test

"Is the prompt formatted correctly?"

---

6. Memory Isn't the Issue—Scalability Is

Version 1 is not "memory inefficient."

The real limitation is that Version 1 sends all partial summaries in one final prompt, which doesn't scale well as the number of chunks grows.

---

## Parallel Map-Reduce (Version 2)

Same as Version 1 but now it summarizes each chunk in parallel, and then combines those summaries into one final summary.

---

## Why Version 2 is better than Version 1 ?

1. It Solves Sequential Processing

from concurrent.futures import ThreadPoolExecutor

It allows multiple tasks to run concurrently.

Without it:

Chunk1 → wait
Chunk2 → wait
Chunk3 → wait
Chunk4 → wait

With it:

Chunk1 | Chunk2 | Chunk3 | Chunk4

all running together

Since every chunk requires an API call to the LLM, most of the time is spent waiting for the network.

Parallel execution greatly reduces the total time.

---

2. Better Prompt Passing Through : PromptManager

from config.prompts.services.prompt_manager import PromptManager

Instead of directly passing prompt strings. i.e summary_prompt = "Summarize..."

Now we doing: self.prompts.get("summary")

This is cleaner because all prompts live in one place.

---

3. Reduce CPU Waiting

LLM calls are network requests.

During, self.llm.generate(prompt)

The CPU is mostly idle, waiting for the server to respond.

Version 1

CPU
│
├── Send request
├── Wait...
├── Wait... (Most of the time is spent waiting.)
├── Wait...
└── Receive response

Version 2

While one request is waiting,

Another request is already running.

Request 1
Request 2
Request 3
Request 4
Request 5

The waiting time overlaps, making much better use of available time.

---

4. Better Progress Tracking

Earlier Version 1 logs

Summarizing chunk 1
Summarizing chunk 2
Summarizing chunk 3

This only tells you what was started.

But in Version 2 logs, we have

logger.info("Submitting chunk...")

logger.info("Completed chunk...")

Now you know

what has been submitted
what has finished
how much work remains
This is useful for monitoring long-running jobs.

---

5. Order Preservation

Parallel execution introduces a new challenge.

Suppose

Chunk1
Chunk2
Chunk3
Chunk4

are submitted.

Completion order might be

Chunk3
Chunk1
Chunk4
Chunk2

If you simply appended results,

you'd get

[
summary3,
summary1,
summary4,
summary2
]

which is out of order.

Your solution was

future_to_index[future] = index

and later

partial_summaries[index] = future.result()

This preserves the original order regardless of which thread finishes first.

---

## What Version 2 Did NOT Solve ?

Version 2 still combines all summaries at once:

final_summary = self.combine_summaries(partial_summaries)

If there are

200 summaries

the final prompt may become enormous.

That problem still exists.

---

## Parallel Map-Reduce + Hierarchical Reduction (version 3)

Version 3 is where your summarizer becomes scalable. While Version 2 improved speed, Version 3 improves the reduce phase so it can handle very large transcripts without exceeding the LLM's context window.

Instead of combining everything at once,

Version 3 combines summaries in batches.

Suppose, combine_batch_size = 5

and you have 25 summaries

Instead of

25 → 1

Version 3 performs

25 → 5 → 1

Round 1
Summary 1
Summary 2
Summary 3
Summary 4
Summary 5
│
▼
Combined Summary A

At the same time

Summary 6
Summary 7
Summary 8
Summary 9
Summary10
│
▼
Combined Summary B

and so on.

After Round 1

25 summaries

↓

5 summaries

Round 2
Now combine those five summaries.

Combined A
Combined B
Combined C
Combined D
Combined E

↓

Final Summary

---

## Why Is This Better?

Instead of sending

500 summaries

to the LLM,

each LLM call only sees

5 summaries

(or whatever batch size you choose).

This keeps every prompt well within the model's limits.

---

## Problems Solved by Version 3

1. Solves Context Window Problems

Version 1 & 2
100 summaries

↓

One gigantic prompt

Risk:

prompt too large
model context exceeded

Version 3

100 summaries

↓

20 summaries

↓

4 summaries

↓

1 summary

Every LLM call stays small.

---

2. Scales to Very Large Transcripts
   Suppose you're summarizing

2-hour meeting ✔
10-hour meeting ✔
entire book ✔
weeks of call transcripts ✔
Versions 1 and 2 eventually break because the final prompt keeps growing.

Version 3 keeps each combine step bounded by the batch size, so it scales much better.

---

3. Better LLM Performance
   LLMs generally produce better summaries when given a focused amount of information.

Instead of asking:

"Summarize these 500 summaries."

you ask:

"Summarize these 5 summaries."

The intermediate summaries are then combined, which is often easier for the model to do consistently.

---

4. Parallel Reduction
   Notice you didn't just make the map phase parallel.

You also made the reduce phase parallel.

This part

with ThreadPoolExecutor(max_workers=self.max_workers)

means multiple batches are combined simultaneously.

Example:

Batch A ─► LLM

Batch B ─► LLM

Batch C ─► LLM

Batch D ─► LLM

All four happen at the same time.
So Version 3 improves both scalability and performance.

---

5. Memory Usage Is More Predictable
   You still keep all partial summaries in memory, but each LLM request only needs to process a small batch of summaries rather than one enormous combined prompt. This makes the size of individual requests predictable and independent of the total transcript size.

# Problems :

That error usually means the tool or model you are using was expected to return valid JSON, but it couldn't produce output that matched the required JSON format.

Depending on the context, it can mean different things:

1. The prompt is too vague or conflicting (most common)
   If you're asking an AI to return JSON, but your prompt also asks for explanations or markdown.

2. The generated JSON doesn't match the required schema
   Suppose the application expects:

{
"name": "string",
"age": "number"
}

But the model returns:

{
"name": "Alice",
"age": "twenty-five"
}

3. The JSON itself is malformed
   For example:

{
"name": "Alice",
"age": 25,
}

Notice the trailing comma.

Or:

{
name: "Alice"
}

Keys must be quoted.

4. The model exceeded limits or got confused
   If your prompt is very long or asks for many things at once, the model may output incomplete JSON like:

{
"users": [
{
"name": "Alice"

The JSON is incomplete, so parsing fails.

5. Your application is enforcing structured output
   If you're using APIs with features like:

JSON mode
Structured Outputs
Function Calling
Response schemas
then the model must produce JSON matching a specific schema. Any mismatch triggers an error such as:

Failed to generate JSON. Please adjust your prompt.

---

This code implements a complete LLM summarization pipeline.

Instead of sending one huge transcript to the LLM (which may exceed token limits), it:

Splits the transcript into chunks.
Summarizes each chunk individually.
Merges the summaries together.
Repeats merging until only one final summary remains.
Can also classify the final summary into a subject/category.

Think of it like summarizing a book:

Book
│
├── Chapter 1 → Summary
├── Chapter 2 → Summary
├── Chapter 3 → Summary
├── Chapter 4 → Summary
└── Chapter 5 → Summary
│
▼
Merge summaries
│
▼
Final Book Summary

Let's go through every part.

Imports
import json

Used for converting Python dictionaries/lists into JSON strings.

Example:

data = {
"title": "Python",
"duration": 20
}

json.dumps(data)

Output

'{"title": "Python", "duration": 20}'

The LLM prompt needs JSON text instead of Python objects.

from string import Template

Template lets you create prompt templates with placeholders.

Example

from string import Template

prompt = Template("Summarize this:\n$transcript")

prompt.substitute(
transcript="Python is easy."
)

Output

Summarize this:
Python is easy.

Instead of manually concatenating strings, placeholders are replaced automatically.

from typing import Any

Used only for type hints.

Example

dict[str, Any]

means

dictionary
keys = strings
values = anything

Example

{
"title":"Python",
"score":95,
"topics":["Variables","Loops"]
}

All value types are allowed.

import logging

Used to print logs.

Example

logger.info("Started")

Output

INFO Started

Useful for debugging.

import time

Used to measure execution time.

Example

start = time.perf_counter()

# some work

print(time.perf_counter() - start)

Output

0.53 seconds

from config.prompts.services.prompt_manager import PromptManager

Loads prompt templates.

Instead of writing

Summarize the following transcript...

inside Python code, prompts are stored separately.

Example

summary.txt

Summarize this:

$transcript

Then

prompts.get("summary")

returns that text.

from config.prompts.services.pyd_model import SubjectClassification

Probably a Pydantic model.

Example

class SubjectClassification(BaseModel):

    subject: str

    confidence: float

LLM output

{
"subject":"Python",
"confidence":0.94
}

gets converted into this model.

from llm.groq_service import LLMService

This is your wrapper around Groq.

Instead of

client.chat.completions.create(...)

you call

self.llm.generate(...)

Much cleaner.

Logger
logger = logging.getLogger(**name**)

Creates a logger for this file.

Summarizer Class
class Summarizer:

This class manages the entire summarization pipeline.

Constructor
def **init**(...)

Receives

llm

Example

Groq
OpenAI
Claude
Gemini

and

prompts

which contains prompt templates.

It stores them

self.llm = llm
self.prompts = prompts

Then loads templates.

self.summary_prompt = Template(
self.prompts.get("summary")
)

Suppose

summary prompt

Summarize:

$transcript

Now this becomes a reusable template.

Same for

classifier_prompt
merge_prompt

\_build_summary_prompt()
def \_build_summary_prompt(
transcript
)

Creates the final prompt.

Template

Summarize:

$transcript

Input

Python has variables...

Output

Summarize:

Python has variables...

summarize_chunk()

This summarizes one chunk.

Example chunk

Python variables
Loops
Functions

Step 1

Start timer

start = time.perf_counter()

Step 2

Build prompt

prompt = self.\_build_summary_prompt(chunk)

Step 3

Call the LLM

summary = self.llm.generate(
prompt,
json_output=True
)

Suppose the LLM returns

{
"title":"Python Basics",
"topics":[
"Variables",
"Loops",
"Functions"
]
}

Step 4

Log execution time

logger.info(...)

Output

Chunk processed in 2.1 sec

Step 5

Return summary

\_build_classifier_prompt()

Receives

summary

Example

{
"topics":["Loops","Functions"]
}

Turns it into JSON text

json.dumps(
summary,
indent=2
)

Output

{
"topics":[
"Loops",
"Functions"
]
}

Then inserts it into the classifier prompt.

classify_summary()

Builds the prompt.

Calls the LLM.

Returns

SubjectClassification

Example

{
"subject":"Programming",
"confidence":0.97
}

\_build_merge_prompt()

Receives many summaries.

Example

[
{"title":"Variables"},
{"title":"Loops"},
{"title":"Functions"}
]

Converts to JSON.

Then inserts into merge prompt.

merge_summaries()

Calls the LLM with multiple summaries.

Example

Input

Variables summary

Loops summary

Functions summary

LLM returns

{
"title":"Python Basics",
"topics":[
"Variables",
"Loops",
"Functions"
]
}

hierarchical_merge()

This is the most interesting part.

Suppose you have

20 summaries

Instead of merging all 20 at once, you merge them in batches.

Imagine

20 summaries

↓

5
5
5
5

Merge each group

↓

4 summaries

Then merge again

↓

1 final summary

This is called hierarchical merging or a tree reduction.

Suppose

batch_size = 5

20 summaries

Round 1

1 2 3 4 5
↓

Merged A

6 7 8 9 10
↓

Merged B

11 12 13 14 15
↓

Merged C

16 17 18 19 20
↓

Merged D

Now

A
B
C
D

Round 2

Merge

A B C D
↓

Final Summary

Inside the loop

while len(level) > 1:

Keep merging until only one summary remains.

Create empty list

next_level = []

Loop through batches

for i in range(
0,
len(level),
batch_size
)

Example

20 summaries

i

0
5
10
15

Get one batch

batch = level[i:i+batch_size]

If

batch_size = 5

then

0:5

5:10

10:15

15:20

Merge

merged = self.merge_summaries(batch)

Append

next_level.append(merged)

After one round

20 summaries

↓

4 summaries

Repeat.

Eventually

1 summary

Return

level[0]

summarize()

This is the main entry point.

Input

chunks = [
"part1",
"part2",
"part3"
]

If empty

if not chunks:

Return

[]

Start timer

pipeline_start

Create

summaries = []

Loop

for idx, chunk in enumerate(chunks):

Example

0
chunk1

1
chunk2

2
chunk3

Summarize each

summary = self.summarize_chunk(chunk)

Append

summaries.append(summary)

Now

[
summary1,
summary2,
summary3
]

After all chunks are summarized:

final_summary = self.hierarchical_merge(
summaries,
batch_size=5,
)

This produces one combined summary.

Return

return final_summary

Although the return type annotation says:

-> list[dict[str, Any]]

the method actually returns a single dictionary (final_summary). The annotation should be updated to:

def summarize(
self,
chunks: list[str],
) -> dict[str, Any]:

to accurately reflect the implementation.

End-to-End Example

Suppose your original transcript is:

Python is a programming language.

It has variables.

It has loops.

It has functions.

It supports OOP.

It has exceptions.

It has modules.

It has decorators.

You split it into four chunks:

Chunk 1
Python is a programming language.
It has variables.

Chunk 2
It has loops.
It has functions.

Chunk 3
It supports OOP.
It has exceptions.

Chunk 4
It has modules.
It has decorators.

Each chunk is summarized independently:

Summary 1
{
"topics":["Programming Language","Variables"]
}

Summary 2
{
"topics":["Loops","Functions"]
}

Summary 3
{
"topics":["OOP","Exceptions"]
}

Summary 4
{
"topics":["Modules","Decorators"]
}

These summaries are merged (in batches if necessary), resulting in a final summary such as:

{
"title": "Python Overview",
"topics": [
"Programming Language",
"Variables",
"Loops",
"Functions",
"OOP",
"Exceptions",
"Modules",
"Decorators"
]
}

Finally, classify_summary() could classify that merged summary as:

{
"subject": "Programming",
"confidence": 0.99
}

So the overall flow is:

Transcript
│
▼
Split into chunks
│
▼
Summarize each chunk
│
▼
Structured summaries
│
▼
Hierarchical merge
│
▼
Final summary
│
▼
(Optional) Subject classification

This design scales well to very large transcripts because each LLM call stays within token limits, and the tree-style merge keeps the final aggregation efficient and manageable.
