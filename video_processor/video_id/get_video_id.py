from typing import Optional
from urllib.parse import urlparse, parse_qs


def get_video_id(url: str) -> Optional[str]:
    parsed = urlparse(url)

    if parsed.hostname == "youtu.be":
        return parsed.path[1:].split("?")[0]

    if parsed.hostname in ("www.youtube.com", "youtube.com"):

        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            return qs.get("v", [None])[0]

        for prefix in ("/embed/", "/v/", "/shorts/"):
            if parsed.path.startswith(prefix):
                return parsed.path.split("/")[2]

    return None