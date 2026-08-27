def build_transcript_sample(transcript, max_chars: int = 4000) -> str:
    """
    Build a representative transcript sample.

    Uses:
        - beginning
        - middle
        - ending

    while preserving timestamps.

    """

    n = len(transcript)

    if n == 0:
        return ""

    if n <= 160:
        sample_segments = transcript

    else:
        head = transcript[:60]

        mid_start = max(0, n // 2 - 20)
        middle = transcript[mid_start : mid_start + 40]

        tail = transcript[-60:]

        sample_segments = head + middle + tail

    parts = []

    current_length = 0

    for segment in sample_segments:

        text = getattr(segment, "text", "") or ""

        if not text:
            continue

        start = getattr(segment, "start", 0)

        line = f"[{start:.1f}s] {text}"

        if current_length + len(line) > max_chars:
            break

        parts.append(line)
        current_length += len(line)

    return "\n".join(parts)
