# tests/test_chunker.py

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from pipeline.chunking.chunker import TranscriptChunker

from video_processor.models.transcript import Segment




@pytest.fixture
def chunker():
    chunker = TranscriptChunker(
        max_words=10,
        overlap_words=2,
        soft_limit_ratio=0.8,
    )

    # Mock cleaner so these tests don't depend on TranscriptCleaner
    chunker.cleaner.clean = MagicMock(side_effect=lambda text: text)

    return chunker


def test_single_chunk(chunker):
    segments = [
        Segment("hello world", 0.0, 2.0),
        Segment("how are you", 2.0, 2.0),
    ]

    chunks = chunker.chunk(segments, "video1")

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk["chunk_id"] == 0
    assert chunk["video_id"] == "video1"
    assert chunk["text"] == "hello world how are you"
    assert chunk["start"] == 0.0
    assert chunk["end"] == 4.0
    assert chunk["word_count"] == 5


def test_hard_limit_creates_multiple_chunks():
    chunker = TranscriptChunker(
        max_words=5,
        overlap_words=1,
        soft_limit_ratio=1.0,
    )

    chunker.cleaner.clean = MagicMock(side_effect=lambda text: text)

    segments = [
        Segment("one two", 0, 1),
        Segment("three four", 1, 1),
        Segment("five six", 2, 1),
    ]

    chunks = chunker.chunk(segments, "video1")

    assert len(chunks) == 2

    assert chunks[0]["text"] == "one two three four"
    assert chunks[1]["text"] == "five six"


def test_create_overlap(chunker):
    segments = [
        {"text": "one two"},
        {"text": "three four"},
        {"text": "five six"},
    ]

    overlap = chunker.create_overlap(segments)

    assert overlap == [
        {"text": "five six"}
    ]


def test_create_chunk(chunker):
    segments = [
        {
            "text": "hello world",
            "start": 0.0,
            "duration": 2.0,
        },
        {
            "text": "again",
            "start": 2.0,
            "duration": 1.0,
        },
    ]

    chunk = chunker.create_chunk(segments, "video1", 0)

    assert chunk == {
        "chunk_id": 0,
        "video_id": "video1",
        "text": "hello world again",
        "start": 0.0,
        "end": 3.0,
        "word_count": 3,
    }


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Now let's begin", True),
        ("Finally we finish", True),
        ("Moving on to the next topic", True),
        ("This ends here.", True),
        ("Is this working?", True),
        ("Amazing!", True),
        ("hello everyone", False),
    ],
)
def test_is_natural_boundary(chunker, text, expected):
    assert chunker.is_natural_boundary(text) is expected


def test_has_pause_true(chunker):
    previous = {
        "start": 0,
        "duration": 2,
    }

    current = {
        "start": 4,
        "duration": 1,
    }

    assert chunker.has_pause(previous, current)


def test_has_pause_false(chunker):
    previous = {
        "start": 0,
        "duration": 2,
    }

    current = {
        "start": 2.5,
        "duration": 1,
    }

    assert not chunker.has_pause(previous, current)


def test_empty_cleaned_segments_are_skipped(chunker):
    chunker.cleaner.clean = MagicMock(return_value="")

    segments = [
        Segment("hello", 0, 1),
        Segment("world", 1, 1),
    ]

    chunks = chunker.chunk(segments, "video1")

    assert chunks == []


def test_cleaner_called_for_every_segment(chunker):
    segments = [
        Segment("one", 0, 1),
        Segment("two", 1, 1),
        Segment("three", 2, 1),
    ]

    chunker.chunk(segments, "video1")

    assert chunker.cleaner.clean.call_count == 3
