def format_timestamp(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

'''
Visual Flow

7265 seconds
      │
      ▼
divmod(7265, 3600)
      │
      ├── Hours = 2
      └── Remaining = 65
                    │
                    ▼
           divmod(65, 60)
                    │
           ├── Minutes = 1
           └── Seconds = 5
                    │
                    ▼
             "02:01:05"
What is divmod()?

Think of it as division + remainder at the same time.

divmod(17, 5)

returns

(3, 2)

because:

17 ÷ 5 = 3
remainder = 2

It's equivalent to writing:

quotient = 17 // 5   # 3
remainder = 17 % 5   # 2

but divmod() gives you both values in one call, making the code shorter and cleaner.

'''

def transcript_to_timestamped(transcript):

    lines = []

    for segment in transcript.segments:
        lines.append(f"[{format_timestamp(segment.start)}] {segment.text}")

    return "\n".join(lines)

'''
The function returns a single string where each transcript segment is on its own line, prefixed with a formatted timestamp.

For example, if:

transcript.segments = [
    Segment(start=0.0, text="Hello everyone."),
    Segment(start=5.3, text="Welcome to today's meeting."),
    Segment(start=12.8, text="Let's get started.")
]

and format_timestamp() returns timestamps like 00:00, 00:05, and 00:12, then the output would be:

[00:00] Hello everyone.
[00:05] Welcome to today's meeting.
[00:12] Let's get started.

'''

def transcript_to_text(transcript):

    return transcript.text