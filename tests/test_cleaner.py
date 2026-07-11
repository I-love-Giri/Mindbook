from processing.services.cleaner import TranscriptCleaner


def test_remove_extra_spaces():
    raw = "Hello     world"
    assert TranscriptCleaner.clean(raw) == "Hello world"


def test_collapse_repeated_punctuation():
    raw = "Hello!!! How are you??"
    assert TranscriptCleaner.clean(raw) == "Hello! How are you?"


def test_normalize_quotes():
    raw = "He said “hello”"
    assert TranscriptCleaner.clean(raw) == 'He said "hello"'


def test_empty_input():
    assert TranscriptCleaner.clean("") == ""


def test_full_transcript_cleanup():
    raw = """
    Hello     world!!!

    This is a test...
    “Clean transcripts”
    """

    expected = 'Hello world! This is a test. "Clean transcripts"'

    assert TranscriptCleaner.clean(raw) == expected


'''
A lesson from these tests

The first test caught a formatting bug ("" vs " " in join).
The second test caught an edge case (empty input).
The third test exposed a logic bug (adding an empty chunk before the first sentence).

'''