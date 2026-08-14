import asyncio
import json

from llm.groq_service import LLMService
from storage.services.transcript_service import TranscriptService
from video_processor.services.parser import extract_video_id

from pipeline.chunking.chunker import TranscriptChunker
from l2_layer import layer2_content_parse
from l5_layer import layer5_deep_dive


async def main():

    url = input("Enter YouTube URL: ").strip()

    if not url:
        print("URL cannot be empty")
        return

    video_id = extract_video_id(url)

    print(f"\nVideo ID: {video_id}")

    # ---------------------------------------------------------
    # Load transcript
    # ---------------------------------------------------------

    transcript_service = TranscriptService()

    transcript = transcript_service.get(video_id)

    print(f"Transcript segments: {len(transcript.segments)}")

    # ---------------------------------------------------------
    # Video info
    # ---------------------------------------------------------

    video_info = transcript.video_info

    print("\nVIDEO INFO")
    print(json.dumps(video_info, indent=2))

    # ---------------------------------------------------------
    # L2
    # ---------------------------------------------------------

    llm_service = LLMService()

    print("\nRunning L2...\n")

    l2_result = await layer2_content_parse(
        transcript=transcript,
        video_info=video_info,
        llm_service=llm_service,
    )

    print("L2 RESULT")
    print(json.dumps(l2_result, indent=2, ensure_ascii=False))

    # ---------------------------------------------------------
    # Chunk transcript
    # ---------------------------------------------------------

    chunker = TranscriptChunker(
        version=TranscriptChunker.VERSION_SEMANTIC,
        max_words=300,
        overlap_words=50,
    )

    chunks = chunker.chunk(
        segments=transcript.segments,
        video_id=video_id,
        chapters=video_info.get("chapters"),
        duration=video_info.get("duration"),
    )

    print(f"\nGenerated {len(chunks)} chunks")

    # ---------------------------------------------------------
    # Show available chunks
    # ---------------------------------------------------------

    print("\nCHUNKS")
    print("=" * 80)

    for chunk in chunks:
        print(
            f"[{chunk['chunk_id']}] "
            f"{chunk.get('title', 'Untitled')} "
            f"({chunk['start']}s - {chunk['end']}s, "
            f"{chunk['word_count']} words)"
        )

    # ---------------------------------------------------------
    # Select one chunk
    # ---------------------------------------------------------

    choice = input("\nEnter chunk number to analyze [0]: ").strip()

    try:
        index = int(choice) if choice else 0
    except ValueError:
        index = 0

    if index < 0 or index >= len(chunks):
        print("Invalid chunk number")
        return

    chunk = chunks[index]

    print("\nSELECTED CHUNK")
    print("=" * 80)

    print(json.dumps(chunk, indent=2, ensure_ascii=False))

    # ---------------------------------------------------------
    # L5
    # ---------------------------------------------------------

    print("\nRunning L5...\n")

    l5_result = await layer5_deep_dive(
        chunk=chunk,
        video_info=video_info,
        parsed=l2_result,
        llm_service=llm_service,
    )

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------

    print("\n")
    print("=" * 80)
    print("L5 RESULT")
    print("=" * 80)

    print(
        json.dumps(
            l5_result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
