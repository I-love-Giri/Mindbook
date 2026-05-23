import yt_dlp

def extract_chaters_and_info(url: str)->dict:
    _Empty = {
        "title": "",
        "description": "",
        "duration": 0,
        "chapters": [],
        "thumbnail": ""
    }
    
    opts = make_ydl_opts(

        outmpl = "%(id)s.%(ext)s",
        skip_download = True,
        clients = ["ios","android","web","tv_embedded"]

    )

    opts.pop("format")

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url,download=False)
    except Exception as exc:
        logger.warning(f"extract_chapters_and_info failed: %s", exc)
        return _Empty
    
    if not info:
        return _Empty
    
    chapters = [
        {
            "title" : ch.get("title",""),
            "start_time": float(ch.get("start_time",0)),
        }
        for ch in info.get("chapters") or []
    ]

    return {

        "title": info.get("title",""),
        "description": info.get("description",""),
        "duration": float(info.get("duration",0)),
        "chapters": chapters,
        "thumbnails": info.get("thumbnails",[])
    }