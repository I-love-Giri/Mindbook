import asyncio
import json

from video_processor.services.parser import extract_video_id

from storage.services.ContentParseService import ContentParseService
from storage.services.KG_Service import KGService
from storage.services.deep_dive_service import DeepDiveService
from storage.services.synthesis_service import SynthesisService
from storage.services.study_assets_service import StudyAssetsService
from pipeline.rag.rag_index_service import RAGIndexService


async def run_pipeline(video_id, qdrant_store):
    rag_index_service = RAGIndexService(qdrant_store)

    services = [
        ContentParseService(),
        KGService(),
        DeepDiveService(rag_index_service=rag_index_service),
        SynthesisService(),
        StudyAssetsService(),
    ]

    try:
        content_service = services[0]
        kg_service = services[1]
        deep_dive_service = services[2]
        synthesis_service = services[3]
        study_assets_service = services[4]

        print("\n[1/5] Getting content...")
        content = await content_service.get(video_id)
        print("      ✓ Content complete")

        print("\n[2/5] Getting knowledge graph...")
        knowledge_graph = await kg_service.get(video_id)
        print("      ✓ Knowledge graph complete")

        print("\n[3/5] Getting deep dive...")
        deep_dive = await deep_dive_service.get(video_id)
        print("      ✓ Deep dive complete")

        print("\n[4/5] Getting synthesis...")
        synthesis = await synthesis_service.get(video_id)
        print("      ✓ Synthesis complete")

        print("\n[5/5] Getting study assets...")
        study_assets = await study_assets_service.get(video_id)
        print("      ✓ Study assets complete")

        return {
            "video_id": video_id,
            "content": content,
            "knowledge_graph": knowledge_graph,
            "deep_dive": deep_dive,
            "synthesis": synthesis,
            "study_assets": study_assets,
        }

    finally:
        for service in services:
            service.close()
        # qdrant_store.close()


def main():
    url = input("Enter the URL: ").strip()

    if not url:
        print("URL cannot be empty")
        return

    try:
        video_id = extract_video_id(url)
    except Exception as e:
        print(f"Could not extract video ID: {e}")
        return

    if not video_id:
        print("Invalid video URL")
        return

    print("\n" + "=" * 80)
    print("VIDEO LEARNING PIPELINE")
    print("=" * 80)
    print(f"Video ID: {video_id}")

    try:
        result = asyncio.run(run_pipeline(video_id))

        print("\n" + "=" * 80)
        print("PIPELINE COMPLETE")
        print("=" * 80)

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )

        # Save the complete result
        output_file = f"{video_id}_pipeline.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                result,
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        print("\n" + "=" * 80)
        print(f"Saved to: {output_file}")
        print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print("PIPELINE FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        raise


"""if __name__ == "__main__":
    main()
"""
