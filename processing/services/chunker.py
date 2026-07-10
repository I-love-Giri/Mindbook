import re
from typing import List

class TranscriptChunker:

    def __init__(self, max_words: int = 800):
        self.max_words = max_words


    def chunk(self, text: str)->List[str]:

        text = text.strip()

        if not text:
            return []

        sentences = re.split(r'(?<=[.!?])\s+', text)

        '''
        Suppose we have

        Hello.
        How are you?
        I'm fine!
        Nice to meet you.

        The regular expression says:

        Whenever you find ., ?, or !, followed by spaces, split there.

        Result:

        [
            "Hello.",
            "How are you?",
            "I'm fine!",
            "Nice to meet you."
        ]

        So now instead of one huge paragraph...

        Hello. How are you? I'm fine!

        we have

        Sentence 1
        Sentence 2
        Sentence 3
        Sentence 4
        
        
        '''

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:

            words = sentence.split()

            '''

            This breaks one sentence into words.

            Example

            sentence = "Python is easy"

            becomes

            ["Python", "is", "easy"]
            
            '''

            if current_length + len(words) <= self.max_words:

                current_chunk.append(sentence)
                current_length += len(words)
            
            else:

                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = len(words)
            
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

