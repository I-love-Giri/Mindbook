import yt_dlp

def extract_chaters_and_info(url: str)->dict:
    _Empty = {
        "title": "",
"description": "",
        "duration": 0,
                "chapters": [],
                "thumbnail": ""
    }
    