import sys

from video_processor.services.parser import extract_video_id

if __name__ == "__main__":
    extract_video_id(sys.argv[1])