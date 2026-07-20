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
        final_summary = self.combine_summaries(partial_summaries)

        logger.info("Summary generation completed.")

        return final_summary

    
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
