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
