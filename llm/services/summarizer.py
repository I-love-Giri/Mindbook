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