from concurrent.futures import ThreadPoolExecutor, as_completed
from string import Template
from typing import Any
import json
import logging
import time

from config.prompts.services.prompt_manager import PromptManager
from config.prompts.services.pyd_model import SubjectClassification
from llm.groq_service import LLMService

logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(
        self,
        llm: LLMService,
        prompts: PromptManager,
        max_workers: int = 5,
        combine_batch_size: int = 10,
    ):
        self.llm = llm
        self.prompts = prompts
        self.max_workers = max_workers
        self.combine_batch_size = combine_batch_size

        self.summary_prompt = Template(self.prompts.get("summary"))
        self.combine_prompt = Template(self.prompts.get("combine_summary"))
        self.classifier_prompt = Template( self.prompts.get("subject_classifier"))
                                            
            

    def _build_summary_prompt(self, transcript: str) -> str:
        return self.summary_prompt.substitute(
            transcript=transcript
        )

    def _build_combine_prompt(
        self,
        summaries: list[dict[str, Any]],
    ) -> str:
        return self.combine_prompt.substitute(
            summaries=json.dumps(
                summaries,
                indent=2,
                ensure_ascii=False,
            )
        )
    


    def _chunk_list(
        self,
        items: list[Any],
        size: int,
    ):
        """Yield successive batches from a list."""
        for i in range(0, len(items), size):
            yield items[i:i + size]

    def summarize_chunk(
        self,
        chunk: str,
    ) -> dict[str, Any]:
        """
        Generate a structured summary for a single transcript chunk.
        """
        start = time.perf_counter()

        prompt = self._build_summary_prompt(chunk)

        summary = self.llm.generate(
            prompt,
            json_output=True,
        )

        logger.info(
            "Chunk processed in %.2f sec",
            time.perf_counter() - start,
        )

        return summary

    def combine_summaries(
        self,
        summaries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Combine a batch of JSON summaries into one JSON summary.
        """
        prompt = self._build_combine_prompt(summaries)

        return self.llm.generate(
            prompt,
            json_output=True,
        )

    def hierarchical_combine(
        self,
        summaries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Hierarchically combine summaries until only one remains.
        """

        if not summaries:
            return {
                "title": "",
                "overview": "",
                "topics": [],
                "key_takeaways": [],
            }

        if len(summaries) <= self.combine_batch_size:
            return self.combine_summaries(summaries)

        round_number = 1

        while len(summaries) > 1:

            logger.info(
                "Combine round %d (%d summaries)",
                round_number,
                len(summaries),
            )

            batches = list(
                self._chunk_list(
                    summaries,
                    self.combine_batch_size,
                )
            )

            next_level = [None] * len(batches)

            with ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:

                future_to_index = {
                    executor.submit(
                        self.combine_summaries,
                        batch,
                    ): idx
                    for idx, batch in enumerate(batches)
                }

                for future in as_completed(future_to_index):

                    idx = future_to_index[future]

                    try:
                        next_level[idx] = future.result()

                        logger.info(
                            "Completed combine batch %d/%d",
                            idx + 1,
                            len(batches),
                        )

                    except Exception:
                        logger.exception(
                            "Failed combine round %d batch %d",
                            round_number,
                            idx + 1,
                        )
                        raise

            summaries = next_level
            round_number += 1

        return summaries[0]
    

    def _build_classifier_prompt(
        self,
        summary: dict[str, Any],
    ) -> str:
        return self.classifier_prompt.substitute( 
            summary=json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
    )

    def classify_summary(
    self,
    summary: dict[str, Any],
    ) -> SubjectClassification:
        prompt = self._build_classifier_prompt(summary)

        response = self.llm.generate(
            prompt,
            json_output=True,
        )
        return response


    def summarize(
        self,
        chunks: list[str],
    ) -> dict[str, Any]:
        """
        Map-Reduce summarization with hierarchical reduction.
        """

        if not chunks:
            logger.warning("No transcript chunks received.")

            return {
                "title": "",
                "overview": "",
                "topics": [],
                "key_takeaways": [],
            }

        pipeline_start = time.perf_counter()

        logger.info(
            "Starting summarization (%d chunks)",
            len(chunks),
        )

        partial_summaries: list[dict[str, Any] | None] = [None] * len(chunks)

        # ---------------- MAP ----------------

        with ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:

            future_to_index = {
                executor.submit(
                    self.summarize_chunk,
                    chunk,
                ): idx
                for idx, chunk in enumerate(chunks)
            }

            for future in as_completed(future_to_index):

                idx = future_to_index[future]

                try:
                    partial_summaries[idx] = future.result()

                    logger.info(
                        "Completed chunk %d/%d",
                        idx + 1,
                        len(chunks),
                    )

                except Exception:
                    logger.exception(
                        "Failed to summarize chunk %d",
                        idx + 1,
                    )
                    raise

        logger.info(
            "Starting hierarchical combine (%d summaries)",
            len(partial_summaries),
        )

        combine_start = time.perf_counter()

        final_summary = self.hierarchical_combine(
            partial_summaries  # type: ignore[arg-type]
        )

        classification = self.classify_summary(
            final_summary
        )


        logger.info(
            "Combine completed in %.2f sec",
            time.perf_counter() - combine_start,
        )

        logger.info(
            "Total summarization completed in %.2f sec",
            time.perf_counter() - pipeline_start,
        )

        #return final_summary




'''
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from string import Template
import logging
import time

from config.prompts.services.prompt_manager import PromptManager
from llm.groq_service import LLMService

logger = logging.getLogger(__name__)
class Summarizer:
    def __init__(
        self,
        llm: LLMService,
        prompts: PromptManager,
        max_workers: int = 5,
        combine_batch_size: int = 10,
    ):
        self.llm = llm
        self.prompts = prompts
        self.max_workers = max_workers
        self.combine_batch_size = combine_batch_size

        self.summary_prompt = Template(self.prompts.get("summary"))
        self.combine_prompt = Template(self.prompts.get("combine_summary"))

    def _build_summary_prompt(self, transcript: str) -> str:
        return self.summary_prompt.substitute(
            transcript=transcript
        )

    def _build_combine_prompt(self, summaries: list[str]) -> str:
        return self.combine_prompt.substitute(
            summaries="\n\n".join(summaries)
        )

    def _chunk_list(self, items: list[str], size: int):
        """Yield successive batches from a list."""
        for i in range(0, len(items), size):
            yield items[i:i + size]

    def summarize_chunk(self, chunk: str) -> str:
        """
        Generate a summary for a single transcript chunk.
        """
        start = time.perf_counter()

        prompt = self._build_summary_prompt(chunk)
        #result = self.llm.generate(prompt).strip()

        result = self.llm.generate(prompt).strip()
        summary = json.loads(result)

        logger.info(
            "Chunk processed in %.2f sec",
            time.perf_counter() - start,
        )

        return summary


    def combine_summaries(self, summaries: list[str]) -> str:
        """
        Combine a batch of summaries into one summary.
        """
        #prompt = self._build_combine_prompt(summaries)
        #return self.llm.generate(prompt).strip()

        prompt = self.combine_prompt.substitute(
            summaries=json.dumps(summaries, indent=2)
        )

        result = self.llm.generate(prompt).strip()

        return json.loads(result)

        



    def hierarchical_combine(self, summaries: list[str]) -> str:
        """
        Hierarchically combine summaries until a single summary remains.
        """

        if not summaries:
            return ""

        if len(summaries) <= self.combine_batch_size:
            return self.combine_summaries(summaries)

        round_number = 1

        while len(summaries) > 1:

            logger.info(
                "Combine round %d: %d summaries",
                round_number,
                len(summaries),
            )

            batches = list(
                self._chunk_list(
                    summaries,
                    self.combine_batch_size,
                )
            )

            next_level = [None] * len(batches)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:

                future_to_index = {
                    executor.submit(self.combine_summaries, batch): idx
                    for idx, batch in enumerate(batches)
                }

                for future in as_completed(future_to_index):

                    idx = future_to_index[future]

                    try:
                        next_level[idx] = future.result()
                        logger.info(
                            "Completed combine batch %d/%d",
                            idx + 1,
                            len(batches),
                        )

                    except Exception:
                        logger.exception(
                            "Failed combine round %d batch %d",
                            round_number,
                            idx + 1,
                        )
                        raise

            summaries = next_level
            round_number += 1

        return summaries[0]

    def summarize(self, chunks: list[str]) -> str:
        """
        Map-Reduce summarization with hierarchical reduction.
        """

        if not chunks:
            logger.warning("No transcript chunks received.")
            return ""

        pipeline_start = time.perf_counter()

        logger.info(
            "Starting summarization (%d chunks)",
            len(chunks),
        )

        partial_summaries = [None] * len(chunks)

        # -------------------
        # MAP PHASE
        # -------------------
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:

            future_to_index = {}

            for index, chunk in enumerate(chunks):

                logger.info(
                    "Submitting chunk %d/%d",
                    index + 1,
                    len(chunks),
                )

                future = executor.submit(
                    self.summarize_chunk,
                    chunk,
                )

                future_to_index[future] = index

            for future in as_completed(future_to_index):

                index = future_to_index[future]

                try:
                    partial_summaries[index] = future.result()

                    logger.info(
                        "Completed chunk %d/%d",
                        index + 1,
                        len(chunks),
                    )

                except Exception:
                    logger.exception(
                        "Failed to summarize chunk %d",
                        index + 1,
                    )
                    raise

        logger.info(
            "Starting hierarchical combine (%d summaries)",
            len(partial_summaries),
        )

        # -------------------
        # REDUCE PHASE
        # -------------------
        combine_start = time.perf_counter()

        final_summary = self.hierarchical_combine(partial_summaries)

        logger.info(
            "Combine phase completed in %.2f sec",
            time.perf_counter() - combine_start,
        )

        logger.info(
            "Summarization completed in %.2f sec",
            time.perf_counter() - pipeline_start,
        )

        return final_summary
'''


'''
--------------------------------------------------------------------------------------------
Initial Strategy (Version 1)
--------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------
Problems : 
--------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------

3. Not Scalable

Suppose you summarize 5 chunks => No problem.

Suppose you summarize 500 chunks

Now, 500 summaries

must fit into one prompt.

That becomes impractical.

--------------------------------------------------------------------------------------------

4. Poor Separation of Responsibilities

Version 1 contains logic like

prompt = self.summary_prompt.substitute(...)

directly inside summarize()

The method is doing many jobs:

building prompts
calling the LLM
storing summaries
merging summaries

--------------------------------------------------------------------------------------------

5. Harder to Test
Suppose you want to test only the prompt construction.

Version 1:

You have to run

summarize()

which also calls the LLM.

You can't easily test

"Is the prompt formatted correctly?"

--------------------------------------------------------------------------------------------

6. Memory Isn't the Issue—Scalability Is

Version 1 is not "memory inefficient."

The real limitation is that Version 1 sends all partial summaries in one final prompt, which doesn't scale well as the number of chunks grows.


--------------------------------------------------------------------------------------------
Parallel Map-Reduce (Version 2)
--------------------------------------------------------------------------------------------

Same as Version 1 but now it summarizes each chunk in parallel, and then combines those summaries into one final summary.

--------------------------------------------------------------------------------------------
Why Version 2 is better than Version 1 ?
--------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------

2. Better Prompt Passing Through : PromptManager 

from config.prompts.services.prompt_manager import PromptManager

Instead of directly passing prompt strings. i.e summary_prompt = "Summarize..."

Now we doing: self.prompts.get("summary")

This is cleaner because all prompts live in one place.

--------------------------------------------------------------------------------------------

3. Reduce CPU Waiting

LLM calls are network requests.

During, self.llm.generate(prompt)

The CPU is mostly idle, waiting for the server to respond.

Version 1

CPU
│
├── Send request
├── Wait...
├── Wait...                   (Most of the time is spent waiting.)
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

--------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------
What Version 2 Did NOT Solve ? 
--------------------------------------------------------------------------------------------

Version 2 still combines all summaries at once:

final_summary = self.combine_summaries(partial_summaries)

If there are

200 summaries

the final prompt may become enormous.

That problem still exists.

--------------------------------------------------------------------------------------------
Parallel Map-Reduce + Hierarchical Reduction (version 3)
--------------------------------------------------------------------------------------------














'''
'''
from concurrent.futures import ThreadPoolExecutor, as_completed
from string import Template
import logging
import time
from config.prompts.services.prompt_manager import PromptManager
from llm.groq_service import LLMService
logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(
        self,
        llm: LLMService,
        prompts: PromptManager
    ):
        self.llm = llm
        self.prompts = prompts

        self.summary_prompt = Template(self.prompts.get("summary"))
        self.combine_prompt = Template(self.prompts.get("combine_summary"))

    def _build_summary_prompt(self, transcript: str) -> str:
        return self.summary_prompt.substitute(
            transcript=transcript
        )

    def _build_combine_prompt(self, summaries: list[str]) -> str:
        return self.combine_prompt.substitute(
            summaries="\n\n".join(summaries)
        )

    def summarize_chunk(self, chunk: str) -> str:
        start = time.perf_counter()
        """
        Generate a summary for a single transcript chunk.
        """
        prompt = self._build_summary_prompt(chunk)
        result = self.llm.generate(prompt).strip()

        logger.info(
            "Chunk processed in %.2f sec",
            time.perf_counter() - start,
        )

        return result


    
    def combine_summaries(self, summaries: list[str]) -> str:
        """
        Merge partial summaries into one coherent summary.
        """
        prompt = self._build_combine_prompt(summaries)
        return self.llm.generate(prompt).strip()
    

    def hierarchical_combine(self, summaries: list[str]) -> str:
        round_number = 1

        while len(summaries) > 1:

            logger.info(
                "Combine round %d (%d summaries)",
                round_number,
                len(summaries),
            )

            batches = list(
                self._chunk_list(
                    summaries,
                    self.combine_batch_size,
                )
            )

            next_level = [None] * len(batches)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.combine_summaries, batch): idx
                    for idx, batch in enumerate(batches)
                }

                for future in as_completed(futures):
                    idx = futures[future]
                    next_level[idx] = future.result()

            summaries = next_level
            round_number += 1

        return summaries[0]

    
    def summarize(self, chunks: list[str]) -> str:
        """
        Map-Reduce summarization.
        """

        logger.info("Starting summarization (%d chunks)", len(chunks))

        partial_summaries = [None] * len(chunks)

        # Map (parallel)
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {}

            for index, chunk in enumerate(chunks):
                logger.info("Submitting chunk %d/%d", index + 1, len(chunks))
                future = executor.submit(self.summarize_chunk, chunk)
                future_to_index[future] = index

            for future in as_completed(future_to_index):
                index = future_to_index[future]

                try:
                    partial_summaries[index] = future.result()
                    logger.info("Completed chunk %d/%d", index + 1, len(chunks))
                except Exception:
                    logger.exception("Failed to summarize chunk %d", index + 1)
                    raise

        logger.info("Combining %d partial summaries", len(partial_summaries))

        # Reduce
        final_summary = self.hierarchical_combine(partial_summaries)

        logger.info("Summary generation completed.")

        return final_summary
'''


''''

    def summarize(self, chunks: list[str]) -> str:
        logger.info("Starting summarization (%d chunks)", len(chunks))

        # Map (parallel)
        with ThreadPoolExecutor(max_workers=5) as executor:
            partial_summaries = list(
                executor.map(self.summarize_chunk, chunks)
            )

        logger.info("Combining %d partial summaries", len(partial_summaries))

        # Reduce
        final_summary = self.combine_summaries(partial_summaries)

        logger.info("Summary generation completed.")

        return final_summary
    
'''
