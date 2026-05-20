from video_processor.video_id.get_video_id import get_video_id

def main():
    urls = [
        "https://youtu.be/abc123",
        "https://www.youtube.com/watch?v=xyz789",
        "https://youtube.com/embed/HELLO123",
        "https://youtube.com/shorts/SHORT999",
        "https://google.com"
    ]

    for url in urls:
        print(f"{url} -> {get_video_id(url)}")


if __name__ == "__main__":
    main()