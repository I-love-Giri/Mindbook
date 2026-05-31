from asyncio.log import logger
import yt_dlp
from make_ydl_opts import _make_ydl_opts
from typing import download

def extract_chapters_and_info(url: str)->dict:

    _EMPTY = {"title": "", "description": "", "duration": 0,
              "chapters": [], "thumbnail": ""}

    opts = _make_ydl_opts(
        outtmpl="%(id)s.%(ext)s",
        extra={"skip_download": True},
        clients=["ios", "android", "web", "tv_embedded"],
    )
    
    opts.pop("format", None)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download-False)
    except Exception as exc:
        logger.warning("extract_chapters_and_info failed: %s", exc)
        return _EMPTY
    
    if not info:
        return _EMPTY
    
    chapters = [
        {"title": ch.get("title", ""),
         "start_time": float(ch.get("start_time", 0))}
        for ch in (info.get("chapters") or [])
    ]

    return { "title": info.get("title",""),
            "description": info.get("description",""),
            "duration": float(info.get("duration",0)),
            "chapters": chapters,
            "thumbnail": info.get("thumbnail","")}
