

def normalize_transcript(transcript):
    normalised=[]
    for t in transcript:
        try:
            if isinstance(t,dict):
                normalised.append({
                    "text": t.get("text",""),
                    "start": t.get("start",0),
                    "duration": t.get("duration",0)
                })
            else:
                normalised.append({
                    "text": t.getattr("text",""),
                    "start": t.getattr("start",0),
                    "duration": t.getattr("duration",0)
                })
        except Exception:
            continue