import threading
from video_processor.transcript.private_strategies.yt_dlp_vtt_subtitle.vtt_subtitle_extraction import _strat_ytdlp
from video_processor.utilities.video_id.get_video_id import get_video_id


class video_processor:
    def __init__(self):
        pass

    def extract_transcript(self , url: str , api_key: str= " ")->list[dict]:

        '''  Tiered strategy:
          1–4  run concurrently (timedtext, yt-dlp VTT, ytt-api+cookies, ytt-api direct)
        '''

        video_id = get_video_id(url)

        cancel_evt = threading.Event()

        fast: list[tuple[str, callable[[],list]]] = []

        if video_id:
            fast.append(("timedtext",lambda: self._strat_timedtext(video_id)))
            fast.append(    ("yt-dlp vtt",
                          lambda: self._strat_ytdlp(url, cancel_evt)))
