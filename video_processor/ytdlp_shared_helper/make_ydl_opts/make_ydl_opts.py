from typing import Optional

YDL_CLIENTS = ["ios", "android", "web","desktop","tv_embedded"]

def _make_ydl_opts(
        outtemp: str,
        format_str: str = "bestvideo+bestaudio/best",
        extra: Optional[dict] = None,
        clients: list[str] = YDL_CLIENTS
)->dict:
    
    opts = {

        "format": format_str,
        "outtemp": outtemp,
        "quiet": True,
        "no_warnings": False,
        "ignoreerrors": False,
        "retries": 5,
        "extra_args": {"youtube": {"player_client": clients}}

    }

    if extra:
        opts.update(extra)
    return opts

