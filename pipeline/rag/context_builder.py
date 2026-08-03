from typing import List, Dict


class ContextBuilder:

    def build(self, chunks: List[Dict]) -> str:

        context = []

        for i, chunk in enumerate(chunks, 1):

            context.append(f"""
                Chunk {i}
                Time: {chunk['start']} - {chunk['end']}

                {chunk['text']}
            """)

        return "\n".join(context)
