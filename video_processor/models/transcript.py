# Nothing here fetches YouTube.
# Nothing saves files.
# It only describes what a transcript is

from dataclasses import dataclass

'''
dataclass:  decorator from Python's dataclasses module.

A decorator is something that modifies a class or function.

'''

@dataclass
class Segment:
    text: str
    start: float
    duration: float

'''
@dataclass: This tells Python:

"Generate useful methods for this class automatically."

It automatically creates things like:

__init__
__repr__
__eq__

So instead of writing

class Segment:
    def __init__(self, text, start, duration):
        self.text = text
        self.start = start
        self.duration = duration

Python writes it for you.

'''

@dataclass
class Transcript:
    video_id: str
    language_code: str
    language: str
    segments: list[Segment] 
    @property
    def text(self)->str:
        return  " ".join(segment.text for segment in self.segments)

'''
Transcript
|
│── video_id = "abc123
├── language_code = "en"
├── language = "English"
└── segments
      │
      ├── Segment 1
      ├── Segment 2
      └── Segment 3

@property

This converts a method into an attribute (read-only property).

Without @property

transcript.text()

With @property

transcript.text


Example : print(transcript.text)

Output:

Hello everyone Welcome!

Notice that text is accessed like an attribute, not a method, because of @property

'''