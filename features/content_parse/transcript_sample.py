def build_transcript_sample(transcript, max_chars=5000) -> str:

    segments = transcript.segments

    total_segments = len(segments)

    # ---------------------------------------------------------
    # Select transcript sample
    # ---------------------------------------------------------

    if total_segments <= 300:
        selected_segments = segments
    else:

        """

        Maan le total:

        1000 segments

        Middle:

        1000 // 2 = 500

        Toh:

        middle_start = 500 - 50 = 450
        middle_end   = 500 + 50 = 550

        So segments:

        450 → 549

        milenge = 100 segments.

        max() aur min() safety ke liye hain, taaki starting/ending index range ke bahar na chale jaye.

        """
        beginning = segments[:100]

        middle_start = max(0, total_segments // 2 - 50)
        middle_end = min(total_segments, total_segments // 2 + 50)
        middle = segments[middle_start:middle_end]

        # Ending ke last 100

        ending = segments[-100:]

        selected_segments = beginning + middle + ending

        # ---------------------------------------------------------
        # Preserve timestamps
        # ---------------------------------------------------------

    sample = "\n".join(
        f"[{segment.start:.1f}s] {segment.text}"
        for segment in selected_segments
        if segment.text
    )

    return sample[:max_chars]
