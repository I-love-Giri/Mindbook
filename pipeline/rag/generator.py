class AnswerGenerator:

    def generate(self, question, context):

        prompt = f"""
Answer the question using only the context.

Context:
{context}

Question:
{question}

Answer:
"""

        response = llm.generate(prompt)

        return response
