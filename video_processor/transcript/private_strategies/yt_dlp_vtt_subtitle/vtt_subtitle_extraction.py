from pathlib import Path
import tempfile
import threading
from typing import List , Optional
import os


from video_processor.ytdlp_shared_helper.make_ydl_opts.make_ydl_opts import _make_ydl_opts
from video_processor.utilities.retries.retry import _retry
from video_processor.ytdlp_shared_helper.ydl_download.ydl_download import _ydl_download

def _strat_ytdlp(self, url: str,
                     cancel_evt: Optional[threading.Event] = None) -> list:
        """
        yt-dlp VTT subtitle extraction.

        cancel_evt is checked before the (expensive) yt-dlp call so that if
        another strategy has already won, this one exits without doing any
        network work (cooperative cancellation, FIX 3).
        """
        if cancel_evt and cancel_evt.is_set():
            return []
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = _make_ydl_opts(
                outtemp=os.path.join(tmpdir, "%(id)s.%(ext)s"),
                extra={
                    "skip_download":     True,
                    "writesubtitles":    True,
                    "writeautomaticsub": True,
                    "subtitleslangs":    ["en", "en-US", "en-GB"],
                    "subtitlesformat":   "vtt",
                },
            )
            _retry(lambda: _ydl_download(url, opts),retries= 2)
            if cancel_evt and cancel_evt.is_set():
                return []
            vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
            if not vtt_files:
                return []
            content = Path(os.path.join(tmpdir, vtt_files[0])).read_text(
                encoding="utf-8"
            )
        return [content]

        

'''class Dummy:
    pass

url = "https://youtu.be/VWavd0SyAPk?si=n2B4VxvPbV0-BrrN"

result = _strat_ytdlp(Dummy(), url)

print("Type:", type(result))
print("Length:", len(result) if result else 0)

print("\n=== CONTENT START ===")
print(result[:2000] if result else "No content")
print("=== CONTENT END ===")'''


        