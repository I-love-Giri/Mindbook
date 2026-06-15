import json
import httpx
import logging

from video_processor.transcript.parse_timedtext_json3 import parse_timedtext_json3

logger = logging.getLogger(__name__)

'''def _fetch_timedtext(video_id: str) -> list:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(timeout=15, headers=headers) as client:
        for lang in ["en", "en-US", "en-GB", "a.en"]:
            url = (
                f"https://www.youtube.com/api/timedtext"
                f"?v={video_id}&lang={lang}&fmt=json3&xorb=2&xobt=3&xovt=3"
            )
            try:
                resp = client.get(url)
                if resp.status_code == 200 and resp.text.strip():
                    data = resp.json()
                    return data 
            except Exception as exc:
                logger.debug("timedtext lang=%s failed: %s", lang, exc)
    return []'''

def _fetch_timedtext(video_id: str) -> list:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(timeout=15, headers=headers) as client:
        for lang in ["en", "en-US", "en-GB", "a.en"]:
            url = (
                f"https://www.youtube.com/api/timedtext"
                f"?v={video_id}&lang={lang}&fmt=json3&xorb=2&xobt=3&xovt=3"
            )
            try:
                resp = client.get(url)
                if resp.status_code == 200 and resp.text.strip():
                    data = resp.json()
                    segments = parse_timedtext_json3(data)
                    if segments:
                        return segments
            except Exception as exc:
                logger.debug("timedtext lang=%s failed: %s", lang, exc)
    return []

