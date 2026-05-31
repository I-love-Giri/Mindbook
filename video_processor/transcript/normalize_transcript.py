def normalize_transcript(transcript):
    normalized = []
    for t in transcript:
        try:
            if isinstance(t,dict):
                normalized.append({
                    "text": t.get("text",""),
                    "start": t.get("start",0),
                    "duration": t.get("duration",0)
                })
            else:
                normalized.append({
                    "text": t.getattr("text",""),
                    "start": t.getattr("start",0),
                    "duration": t.getattr("duration",0)
                })
        except Exception:
            continue

        return normalized
