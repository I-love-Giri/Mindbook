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
            summary.model_dump(),
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

from string import Template
import logging
from llm.groq_service import LLMService
logger = logging.getLogger(__name__)

class Summarizer:
    def __init__(
        self,
        llm: LLMService,
        summary_prompt: str,
        combine_prompt: str,
    ):
        self.llm = llm
        self.summary_prompt = Template(summary_prompt)
        self.combine_prompt = Template(combine_prompt)

    def summarize(self, chunks: list[str]) -> str:
        """
        Summarize a transcript using the map-reduce approach.
        """

        partial_summaries = []

        # Map step: summarize each chunk
        for i, chunk in enumerate(chunks):
            logger.info("Summarizing chunk %d/%d", i + 1, len(chunks))

            prompt = self.summary_prompt.substitute(
                transcript=chunk
            )


            summary = self.llm.generate(prompt)
            partial_summaries.append(summary)
        
        logger.info("Combining %d partial summaries", len(partial_summaries))
        
        # Reduce step: merge chunk summaries
        merged_summaries = "\n\n".join(partial_summaries)


        final_prompt = self.combine_prompt.substitute(
            summaries=merged_summaries
        )

        logger.info("Generating final summary")

        final_summary = self.llm.generate(final_prompt)

        return final_summary

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
    
'''

    def summarize(self, chunks: list[str]) -> str:
        """
        Map-Reduce summarization.
        """

        logger.info("Starting summarization (%d chunks)", len(chunks))

        partial_summaries = []

        # Map
        for index, chunk in enumerate(chunks, start=1):
            logger.info("Summarizing chunk %d/%d", index, len(chunks))

            summary = self.summarize_chunk(chunk)
            partial_summaries.append(summary)

        logger.info("Combining %d partial summaries", len(partial_summaries))

        # Reduce
        final_summary = self.combine_summaries(partial_summaries)

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
