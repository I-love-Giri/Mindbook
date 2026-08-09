import json
import logging
import time
from typing import Any

from config.prompts.services.prompt_registry import PromptRegistry
from llm.groq_service import LLMService

logger = logging.getLogger(__name__)

DEFAULT_DOMAIN = "narrative"
DEFAULT_DIFFICULTY = "intermediate"

# How many words of a chunk's text to use as a fallback title when no
# real chapter title is available (see _chunk_title).
FALLBACK_TITLE_WORDS = 7


def _chunk_text(chunk: Any) -> str:
    """
    Normalizes a chunk into plain text.

    TranscriptChunker (pipeline/chunking/chunker.py) always returns
    chunks as dicts with a "text" key (see create_chunk and
    split_long_unit). Plain strings are also accepted so this stays
    compatible with any simpler chunker used in tests or elsewhere.
    """

    if isinstance(chunk, str):
        return chunk

    if isinstance(chunk, dict):
        text = chunk.get("text")
        if isinstance(text, str):
            return text
        raise TypeError(f"Chunk dict has no 'text' field: {list(chunk.keys())}")

    raise TypeError(f"Unsupported chunk type: {type(chunk)!r}")


def _chunk_title(chunk: Any, index: int) -> str:
    """
    Extracts a section title from a chunk.

    If the chunker produced a real title (e.g. from a video chapter),
    use it as-is. Otherwise fall back to a short heuristic title built
    from the chunk's own first words, so every section still gets a
    readable heading instead of a generic "Section N".
    """

    if isinstance(chunk, dict):
        title = chunk.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()

    text = _chunk_text(chunk)
    words = text.split()[:FALLBACK_TITLE_WORDS]

    if not words:
        return f"Section {index + 1}"

    fallback = " ".join(words)
    if len(text.split()) > FALLBACK_TITLE_WORDS:
        fallback += "..."

    return fallback.strip().capitalize()


def _chunk_start(chunk: Any) -> float:
    if isinstance(chunk, dict):
        start = chunk.get("start")
        if isinstance(start, (int, float)):
            return float(start)
    return 0.0


class Summarizer:
    """
    Deep summarization pipeline.

    Stages:
      1. Quick per-chunk summaries        (summary/chunk_summary)
      2. Domain + difficulty classification (classification/domain_classifier)
      3. Deep, domain-adaptive section pass (summary/section_analysis_<category>)
      4. Key concept extraction           (extraction/key_concepts)
      5. Hierarchical chapter merge       (summary/chapter_summary)
      6. Final citation-aware synthesis   (summary/video_summary_<category>)
      7. Grounding check                  (validation/grounding_checker)

    Every LLM call uses the educator persona (system/educator) as the
    system prompt. No vision/frame extraction is used anywhere in this
    pipeline - every stage works from transcript text only.
    """

    def __init__(
        self,
        llm: LLMService,
        prompts: PromptRegistry,
        batch_size: int = 5,
    ):
        self.llm = llm
        self.prompts = prompts
        self.batch_size = batch_size

        # These are category-independent, safe to preload once.
        self.chunk_summary_prompt = prompts.chunk_summary()
        self.key_concepts_prompt = prompts.key_concepts()
        self.chapter_summary_prompt = prompts.chapter_summary()
        self.domain_classifier_prompt = prompts.domain_classifier()
        self.grounding_checker_prompt = prompts.grounding_checker()

        # These depend on the classified category and are loaded per
        # run inside summarize(), once the category is known.
        self._section_analysis_prompt = None
        self._video_summary_prompt = None

        self.educator_system_prompt = prompts.educator_system()

    # --------------------------------------------------
    # Prompt Builders
    # --------------------------------------------------

    def _build_chunk_summary_prompt(self, transcript: str) -> str:
        return self.chunk_summary_prompt.substitute(transcript=transcript)

    def _build_section_analysis_prompt(
        self,
        transcript: str,
        domain: str,
        difficulty: str,
        section_title: str,
    ) -> str:
        return self._section_analysis_prompt.substitute(
            transcript=transcript,
            domain=domain,
            difficulty=difficulty,
            section_title=section_title,
        )

    def _build_key_concepts_prompt(self, transcript: str) -> str:
        return self.key_concepts_prompt.substitute(transcript=transcript)

    def _build_chapter_prompt(
        self,
        sections: list[dict[str, Any]],
    ) -> str:
        return self.chapter_summary_prompt.substitute(
            sections=json.dumps(sections, ensure_ascii=False, indent=2)
        )

    def _build_video_prompt(
        self,
        chapter_summary: dict[str, Any],
        indexed_sections: list[dict[str, Any]],
    ) -> str:
        return self._video_summary_prompt.substitute(
            chapters=json.dumps(chapter_summary, ensure_ascii=False, indent=2),
            sections=json.dumps(indexed_sections, ensure_ascii=False, indent=2),
        )

    def _build_classifier_prompt(
        self,
        summary: dict[str, Any],
    ) -> str:
        return self.domain_classifier_prompt.substitute(
            summary=json.dumps(summary, ensure_ascii=False, indent=2)
        )

    def _build_grounding_prompt(
        self,
        reference_content: dict[str, Any],
        summary: dict[str, Any],
    ) -> str:
        return self.grounding_checker_prompt.substitute(
            reference_content=json.dumps(
                reference_content, ensure_ascii=False, indent=2
            ),
            summary=json.dumps(summary, ensure_ascii=False, indent=2),
        )

    # --------------------------------------------------
    # LLM Call Wrapper
    # --------------------------------------------------

    def _call(self, prompt: str) -> dict[str, Any]:
        return self.llm.generate(
            prompt,
            system_prompt=self.educator_system_prompt,
            json_output=True,
        )

    # --------------------------------------------------
    # Stage 1: Quick Chunk Summary
    # --------------------------------------------------

    def summarize_chunk(self, chunk: str) -> dict[str, Any]:
        start = time.perf_counter()

        prompt = self._build_chunk_summary_prompt(chunk)
        result = self._call(prompt)

        logger.info(
            "Quick chunk summary done in %.2fs",
            time.perf_counter() - start,
        )

        return result

    # --------------------------------------------------
    # Stage 2: Domain + Difficulty Classification
    # --------------------------------------------------

    def classify_domain(
        self,
        chunk_summaries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prompt = self._build_classifier_prompt({"chunk_summaries": chunk_summaries})
        return self._call(prompt)

    # --------------------------------------------------
    # Stage 3: Deep, Domain-Adaptive Section Analysis
    # --------------------------------------------------

    def analyze_section(
        self,
        chunk_text: str,
        domain: str,
        difficulty: str,
        section_title: str,
    ) -> dict[str, Any]:
        prompt = self._build_section_analysis_prompt(
            chunk_text, domain, difficulty, section_title
        )
        return self._call(prompt)

    # --------------------------------------------------
    # Stage 4: Key Concept Extraction
    # --------------------------------------------------

    def extract_key_concepts(self, chunk_texts: list[str]) -> list[dict[str, Any]]:
        """
        Extracts key concepts per chunk (bounded, same as every other
        stage) instead of sending the whole transcript in one request -
        that single-shot approach was blowing past Groq's per-request
        token budget on anything longer than a few minutes of video.
        Results are merged and deduplicated by concept name.
        """

        all_concepts: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        for index, chunk_text in enumerate(chunk_texts):
            try:
                prompt = self._build_key_concepts_prompt(chunk_text)
                result = self._call(prompt)

                for concept in result.get("concepts", []):
                    name = concept.get("name", "").strip()
                    key = name.lower()

                    if name and key not in seen_names:
                        seen_names.add(key)
                        all_concepts.append(concept)

            except Exception:
                logger.exception(
                    "Key concept extraction failed for chunk %d, skipping",
                    index + 1,
                )

        return all_concepts

    # --------------------------------------------------
    # Stage 5: Hierarchical Chapter Merge
    # --------------------------------------------------

    def merge_summaries(
        self,
        summaries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prompt = self._build_chapter_prompt(summaries)
        return self._call(prompt)

    def hierarchical_merge(
        self,
        summaries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        level = summaries
        round_number = 1

        while len(level) > 1:

            logger.info(
                "Merge round %d | %d summaries",
                round_number,
                len(level),
            )

            next_level = []

            for i in range(0, len(level), self.batch_size):
                batch = level[i : i + self.batch_size]
                merged = self.merge_summaries(batch)
                next_level.append(merged)

            level = next_level
            round_number += 1

        return level[0]

    # --------------------------------------------------
    # Stage 6: Final Citation-Aware Synthesis
    # --------------------------------------------------

    def create_video_summary(
        self,
        chapter_summary: dict[str, Any],
        indexed_sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prompt = self._build_video_prompt(chapter_summary, indexed_sections)
        return self._call(prompt)

    # --------------------------------------------------
    # Stage 7: Grounding Check
    # --------------------------------------------------

    def check_grounding(
        self,
        reference_content: dict[str, Any],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Checks the final summary against the condensed chapter_summary
        it was synthesized from - not the raw transcript. Grounding
        against the full transcript would be more thorough in theory,
        but for anything beyond a few minutes of video it single-
        handedly blew the per-request token budget (this was the
        actual cause of the 413 "Request too large" errors). Checking
        against the already-condensed chapter content still catches
        the failure mode that matters here: the final synthesis step
        inventing something beyond what the pipeline already
        established, while staying within a bounded request size.
        """
        prompt = self._build_grounding_prompt(reference_content, summary)
        return self._call(prompt)

    # --------------------------------------------------
    # Main Pipeline
    # --------------------------------------------------

    def summarize(self, chunks: list[Any]) -> dict[str, Any]:
        """
        Runs the full deep-summary pipeline and returns:

        {
            "summary": {...},         # video_summary_<category> schema
            "sections": [...],        # per-chunk deep section analyses
            "classification": {...},  # domain_classifier schema
            "key_concepts": [...],
            "grounding": {...},       # grounding_checker schema
        }
        """

        if not chunks:
            logger.warning("No transcript chunks received.")
            return {}

        pipeline_start = time.perf_counter()

        logger.info(
            "Starting deep summarization | chunks=%d",
            len(chunks),
        )

        chunk_texts = [_chunk_text(chunk) for chunk in chunks]
        chunk_titles = [_chunk_title(chunk, i) for i, chunk in enumerate(chunks)]
        chunk_starts = [_chunk_start(chunk) for chunk in chunks]

        # Step 1: quick per-chunk summaries (fast first pass)
        chunk_summaries: list[dict[str, Any]] = []

        for index, chunk_text in enumerate(chunk_texts):
            try:
                summary = self.summarize_chunk(chunk_text)
                chunk_summaries.append(summary)

                logger.info(
                    "Completed quick summary %d/%d",
                    index + 1,
                    len(chunks),
                )

            except Exception:
                logger.exception(
                    "Failed quick summary for chunk %d",
                    index + 1,
                )
                raise

        # Step 2: classify domain + difficulty from the quick summaries,
        # before running the more expensive domain-adaptive deep pass
        try:
            classification = self.classify_domain(chunk_summaries)
            category = classification.get("category", DEFAULT_DOMAIN)
            difficulty = classification.get("difficulty", DEFAULT_DIFFICULTY)

        except Exception:
            logger.exception("Domain classification failed, using default")
            classification = {
                "category": DEFAULT_DOMAIN,
                "difficulty": DEFAULT_DIFFICULTY,
                "confidence": 0.0,
                "reason": "Classification failed; default applied.",
            }
            category = DEFAULT_DOMAIN
            difficulty = DEFAULT_DIFFICULTY

        logger.info(
            "Detected category: %s | difficulty: %s (confidence=%s)",
            category,
            difficulty,
            classification.get("confidence"),
        )

        # Load the category-specific templates now that we know which
        # domain we're dealing with.
        self._section_analysis_prompt = self.prompts.section_analysis(category)
        self._video_summary_prompt = self.prompts.video_summary(category)

        # Step 3: deep, domain-adaptive analysis per chunk
        section_analyses: list[dict[str, Any]] = []

        for index, chunk_text in enumerate(chunk_texts):
            try:
                analysis = self.analyze_section(
                    chunk_text,
                    category,
                    difficulty,
                    chunk_titles[index],
                )
                analysis["title"] = chunk_titles[index]
                analysis["start"] = chunk_starts[index]

                section_analyses.append(analysis)

                logger.info(
                    "Completed deep analysis %d/%d",
                    index + 1,
                    len(chunks),
                )

            except Exception:
                logger.exception(
                    "Failed deep analysis for chunk %d",
                    index + 1,
                )
                raise

        # Step 4: extract key concepts from the full transcript
        try:
            key_concepts = self.extract_key_concepts(chunk_texts)

        except Exception:
            logger.exception("Key concept extraction failed")
            key_concepts = []

        # Step 5: hierarchically merge deep section analyses into chapters
        chapter_summary = self.hierarchical_merge(section_analyses)

        # Build a compact, indexed section list for citation-aware
        # synthesis (FAQ source_section references, etc). Kept small
        # and separate from the full section_analyses so the final
        # synthesis prompt stays bounded even for long videos.
        indexed_sections = [
            {
                "index": i + 1,
                "title": s.get("title", f"Section {i + 1}"),
                "start": s.get("start", 0.0),
                "key_concepts": s.get("key_concepts", []),
            }
            for i, s in enumerate(section_analyses)
        ]

        # Step 6: produce the final connected, citation-aware video summary
        final_summary = self.create_video_summary(chapter_summary, indexed_sections)

        # Step 7: verify the final summary is grounded in the transcript
        try:
            grounding = self.check_grounding(chapter_summary, final_summary)

            if not grounding.get("grounded", True):
                logger.warning(
                    "Grounding check flagged issues: %s",
                    grounding.get("issues"),
                )

        except Exception:
            logger.exception("Grounding check failed")
            grounding = {
                "grounded": None,
                "confidence": 0.0,
                "verdict": "unknown",
                "issues": [],
            }

        logger.info(
            "Deep summarization pipeline finished in %.2fs",
            time.perf_counter() - pipeline_start,
        )

        return {
            "summary": final_summary,
            "sections": section_analyses,
            "classification": classification,
            "key_concepts": key_concepts,
            "grounding": grounding,
        }

        # return final_summary


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


"""
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

If there are 200 summaries

the final prompt may become enormous.

That problem still exists.

Possible issues include:

exceeding the model's context window
API errors
truncated prompts
lower-quality summaries because the model has too much information to process at once
This is the main limitation of Versions 1 and 2.

--------------------------------------------------------------------------------------------
Parallel Map-Reduce + Hierarchical Reduction (version 3)
--------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------
Why Is This Better?
--------------------------------------------------------------------------------------------

Instead of sending

500 summaries

to the LLM,

each LLM call only sees

5 summaries

(or whatever batch size you choose).

This keeps every prompt well within the model's limits.

--------------------------------------------------------------------------------------------
Problems Solved by Version 3
--------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------

2. Scales to Very Large Transcripts
Suppose you're summarizing

2-hour meeting ✔
10-hour meeting ✔
entire book ✔
weeks of call transcripts ✔
Versions 1 and 2 eventually break because the final prompt keeps growing.

Version 3 keeps each combine step bounded by the batch size, so it scales much better.

--------------------------------------------------------------------------------------------

3. Better LLM Performance
LLMs generally produce better summaries when given a focused amount of information.

Instead of asking:

"Summarize these 500 summaries."

you ask:

"Summarize these 5 summaries."

The intermediate summaries are then combined, which is often easier for the model to do consistently.

--------------------------------------------------------------------------------------------

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

--------------------------------------------------------------------------------------------

5. Memory Usage Is More Predictable
You still keep all partial summaries in memory, but each LLM request only needs to process a small batch of summaries rather than one enormous combined prompt. This makes the size of individual requests predictable and independent of the total transcript size.

"""
