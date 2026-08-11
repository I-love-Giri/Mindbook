import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Multiple player clients tried in order — yt-dlp's "web" client alone
# gets blocked/throttled by YouTube fairly often; falling back through
# ios/android substantially improves reliability.
YDL_CLIENTS = ["ios", "android", "web"]

_EMPTY_RESULT = {"title": "", "duration": 0.0, "chapters": []}


def _cookies_path() -> Optional[str]:
    """
    Optional cookies.txt sitting next to this file, used to reduce
    YouTube's bot-detection false positives if you have one. Purely
    optional - everything works without it, just less reliably on
    some networks.
    """
    p = Path(__file__).parent / "cookies.txt"
    return str(p) if p.exists() else None


def extract_chapters_and_info(video_id: str) -> dict:
    """
    Fetches video-level metadata - title, duration, and chapter
    markers - via yt-dlp.

    This is intentionally a SEPARATE data source from
    YoutubeTranscriptService: youtube_transcript_api only returns
    transcript text/timing, never chapters or duration. yt-dlp is
    what actually exposes chapter markers, so chapter-aware chunking
    needs this call in addition to the existing transcript fetch.

    Returns {"title": str, "duration": float, "chapters": [...]}
    where each chapter is {"title": str, "start_time": float}.

    Never raises - on missing dependency, network failure, or a video
    with no chapters, returns the empty-safe default so callers (and
    TranscriptChunker, which already treats an empty/None chapters
    list as "no chapters") can proceed without chapter-aware chunking
    rather than crashing the whole pipeline over optional metadata.

    Requires the `yt-dlp` package: pip install yt-dlp
    """

    try:
        import yt_dlp
    except ImportError:
        logger.warning(
            "yt-dlp is not installed; chapter-aware chunking will fall "
            "back to whole-transcript chunking. Install with: "
            "pip install yt-dlp"
        )
        return dict(_EMPTY_RESULT)

    url = f"https://www.youtube.com/watch?v={video_id}"

    opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 5,
        "ignoreerrors": False,
        "extractor_args": {"youtube": {"player_client": list(YDL_CLIENTS)}},
    }

    cookies = _cookies_path()
    if cookies:
        opts["cookiefile"] = cookies

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        logger.warning("extract_chapters_and_info failed for %s: %s", video_id, exc)
        return dict(_EMPTY_RESULT)

    if not info:
        return dict(_EMPTY_RESULT)

    chapters = [
        {
            "title": ch.get("title", ""),
            "start_time": float(ch.get("start_time", 0)),
        }
        for ch in (info.get("chapters") or [])
    ]

    return {
        "title": info.get("title", ""),
        "duration": float(info.get("duration") or 0),
        "chapters": chapters,
    }


if __name__ == "__main__":
    result = extract_chapters_and_info("dQw4w9WgXcQ")
    print("RESULT:")
    print(result)
