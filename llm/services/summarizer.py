from string import Template

from llm.groq_service import LLMService


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
        for chunk in chunks:
            prompt = self.summary_prompt.substitute(
                transcript=chunk
            )

            summary = self.llm.generate(prompt)
            partial_summaries.append(summary)

        # Reduce step: merge chunk summaries
        merged_summaries = "\n\n".join(partial_summaries)

        final_prompt = self.combine_prompt.substitute(
            summaries=merged_summaries
        )

        final_summary = self.llm.generate(final_prompt)

        return final_summary