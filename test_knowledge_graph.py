import asyncio
import json

# from storage.services.ContentParseService import ContentParseService
from storage.services.KG_Service import KGService
from video_processor.services.parser import extract_video_id

url = input("Enter the URL: ").strip()

if not url:
    print("URL cannot be empty")
    exit(1)

video_id = extract_video_id(url)

# service = ContentParseService()

service = KGService()


try:
    result = asyncio.run(service.get(video_id))

    print(json.dumps(result, indent=2))

finally:
    service.close()
