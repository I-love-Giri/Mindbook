import yt_dlp

def _ydl_download(url: str , opts: dict)->None:

  with  yt_dlp.YoutubeDL(opts) as ydl:
    code = ydl.download([url])
    if code != 0:
      raise RuntimeError(f"Download failed with code {code}")
