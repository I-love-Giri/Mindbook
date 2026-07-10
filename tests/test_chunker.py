from processing.services.chunker import TranscriptChunker


def test_chunker_basic():

    text = (
        "I love Python. "
        "It is easy to learn. "
        "Machine learning is amazing. "
        "AI is changing the world."
    )

    chunker = TranscriptChunker(max_words=8)

    chunks = chunker.chunk(text)

    expected = [
        "I love Python. It is easy to learn.",
        "Machine learning is amazing.",
        "AI is changing the world."
    ]

    assert chunks == expected

def test_short_text():

    chunker = TranscriptChunker(max_words=100)

    text = "Hello world."

    assert chunker.chunk(text) == ["Hello world."]

def test_empty_text():

    chunker = TranscriptChunker()

    assert chunker.chunk("") == []

def test_single_chunk():

    text = "Python is fun. AI is amazing."

    chunker = TranscriptChunker(max_words=50)

    chunks = chunker.chunk(text)

    assert len(chunks) == 1

def test_multiple_chunks():

    text = (
        "One two three. "
        "Four five six. "
        "Seven eight nine."
    )

    chunker = TranscriptChunker(max_words=5)

    chunks = chunker.chunk(text)

    assert len(chunks) == 3

'''
One thing to be aware of is the your algorithm never splits a sentence. If a single sentence is longer than max_words, that sentence will still end up in its own chunk, even though it exceeds the limit.

That's not necessarily wrong, but it's worth testing and deciding whether it's the behavior you want.

'''

# for example:

def test_sentence_longer_than_limit():

    text = "One two three four five six seven eight nine ten."

    chunker = TranscriptChunker(max_words=5)

    chunks = chunker.chunk(text)

    # The current implementation keeps the long sentence intact.
    assert chunks == [text]