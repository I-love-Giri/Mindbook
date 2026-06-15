def _parse_timedtext_json3(data: dict) -> list:
    segments = []
    for event in data.get("events", []):
        if "segs" not in event:
            continue
        text = "".join(s.get("utf8", "") for s in event["segs"]).strip()
        if not text or text == "\n":
            continue
        start = event.get("tStartMs", 0) / 1000
        dur   = event.get("dDurationMs", 1000) / 1000
        segments.append({"text": text, "start": start, "duration": dur})
    return segments