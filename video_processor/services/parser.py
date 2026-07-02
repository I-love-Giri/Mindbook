import re
import sys

def extract_video_id(url_or_id: str):
    """Extract the 11-character YouTube video ID."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            print(match.group(1))
            return

    if re.fullmatch(r"[0-9A-Za-z_-]{11}", url_or_id):
        print(url_or_id)
        return

    raise ValueError(f"Could not extract a video ID from: {url_or_id}")


if __name__ == "__main__":
    extract_video_id(sys.argv[1])
