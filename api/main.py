print("=== DEBUG: checking transformers ===")

try:
    import torch
    import transformers

    print("DEBUG torch:", torch.__version__)
    print("DEBUG transformers:", transformers.__version__)

    from transformers import PreTrainedModel

    print("DEBUG: PreTrainedModel import OK")

except Exception as e:
    print("DEBUG: PreTrainedModel import FAILED:", repr(e))


import asyncio
import json

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from storage.services.ContentParseService import ContentParseService
from storage.services.KG_Service import KGService
from storage.services.deep_dive_service import DeepDiveService
from storage.services.study_assets_service import StudyAssetsService
from storage.services.synthesis_service import SynthesisService
from storage.mongo_storage import MongoStorage

from test_new_notes import run_pipeline
from video_processor.services.parser import extract_video_id

from pipeline.embeddings.embedder import EmbeddingService
from pipeline.vectorstore.qdrant_store import QdrantStore
from pipeline.retrieval.retriever import Retriever
from pipeline.rag.context_builder import ContextBuilder
from pipeline.rag.generator import Generator
from pipeline.rag.rag_index_service import RAGIndexService

processing_status = {}

app = FastAPI()


# --------------------------------------------------
# Qdrant
# --------------------------------------------------

# One shared Qdrant client for the whole FastAPI app.
# It is used by both /process and /ask.
vector_store = QdrantStore()


# --------------------------------------------------
# RAG components
# --------------------------------------------------

context_builder = ContextBuilder()
generator = Generator()


# Embedding model and Retriever are created lazily.
# This prevents Qwen from loading when FastAPI starts.

embedding_service = None
retriever = None


def get_retriever():
    global embedding_service, retriever

    if retriever is None:
        print("Loading embedding model...")

        embedding_service = EmbeddingService()

        retriever = Retriever(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

        print("Embedding model loaded.")

    return retriever


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://mindbook-navy.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Request models
# --------------------------------------------------


class VideoRequest(BaseModel):
    url: str


class AskRequest(BaseModel):
    video_id: str
    question: str


def sse(payload: dict) -> str:
    """Encode a single Server-Sent Event payload."""
    return f"data: {json.dumps(payload, default=str)}\n\n"


# --------------------------------------------------
# Health
# --------------------------------------------------


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "MindBook API is running",
    }


@app.get("/health/db")
def health_db():
    try:
        db = MongoStorage()
        db.client.admin.command("ping")
        return {"status": "ok", "mongodb": "connected"}
    except Exception as e:
        return {"status": "error", "mongodb": str(e)}


# --------------------------------------------------
# Background processing
# --------------------------------------------------


async def background_process(video_id: str):
    try:
        print(f"Pipeline started for {video_id}")

        await run_pipeline(
            video_id,
            vector_store,
        )

        processing_status[video_id] = "completed"

        print(f"Pipeline completed for {video_id}")

    except Exception as e:
        processing_status[video_id] = "failed"

        print(f"Pipeline failed for {video_id}: {e}")


# --------------------------------------------------
# Process video
# --------------------------------------------------


@app.post("/process")
def process_video(
    request: VideoRequest,
    background_tasks: BackgroundTasks,
):
    video_id = extract_video_id(request.url)

    processing_status[video_id] = "processing"

    background_tasks.add_task(
        background_process,
        video_id,
    )

    return {
        "status": "processing",
        "video_id": video_id,
    }


@app.post("/process/stream")
async def process_video_stream(request: VideoRequest):
    """Run the pipeline once and expose genuine, incremental progress to the UI."""
    video_id = extract_video_id(request.url)

    async def event_stream():
        services = []
        try:
            yield sse(
                {
                    "type": "status",
                    "stage": 0,
                    "message": "Fetching transcript and metadata…",
                }
            )
            content_service = ContentParseService()
            kg_service = KGService()
            deep_dive_service = DeepDiveService(
                rag_index_service=RAGIndexService(vector_store)
            )
            synthesis_service = SynthesisService()
            study_assets_service = StudyAssetsService()
            services = [
                content_service,
                kg_service,
                deep_dive_service,
                synthesis_service,
                study_assets_service,
            ]

            content = await content_service.get(video_id)
            if content is None:
                raise RuntimeError("Could not retrieve or parse the video transcript.")
            yield sse(
                {
                    "type": "content",
                    "stage": 1,
                    "content": content,
                    "message": "Transcript parsed.",
                }
            )

            yield sse(
                {
                    "type": "status",
                    "stage": 1,
                    "message": "Mapping the knowledge graph…",
                }
            )
            knowledge_graph = await kg_service.get(video_id)
            yield sse(
                {
                    "type": "knowledge_graph",
                    "stage": 2,
                    "knowledge_graph": knowledge_graph,
                    "message": "Knowledge graph ready.",
                }
            )

            yield sse(
                {
                    "type": "status",
                    "stage": 2,
                    "message": "Writing the deep dive, chapter by chapter…",
                }
            )
            batch_queue: asyncio.Queue[tuple[list[dict], int, int]] = asyncio.Queue()

            async def on_batch(batch: list[dict], start: int, total: int):
                await batch_queue.put((batch, start, total))

            deep_task = asyncio.create_task(
                deep_dive_service.get(video_id, on_batch=on_batch)
            )
            received = 0
            while not deep_task.done() or not batch_queue.empty():
                try:
                    batch, start, total = await asyncio.wait_for(
                        batch_queue.get(), timeout=0.25
                    )
                except TimeoutError:
                    continue
                for offset, section in enumerate(batch):
                    received += 1
                    yield sse(
                        {
                            "type": "deep_dive_section",
                            "stage": 2,
                            "section": section,
                            "section_index": start + offset,
                            "total": total,
                            "received": received,
                            "message": f"Chapter {received}/{total} is ready.",
                        }
                    )
            deep_dive = await deep_task

            yield sse(
                {
                    "type": "status",
                    "stage": 3,
                    "message": "Synthesizing the learning guide…",
                }
            )
            synthesis = await synthesis_service.get(video_id)
            yield sse({"type": "synthesis", "stage": 3, "synthesis": synthesis})

            yield sse(
                {"type": "status", "stage": 4, "message": "Building study assets…"}
            )
            study_assets = await study_assets_service.get(video_id)
            yield sse(
                {
                    "type": "complete",
                    "stage": 4,
                    "message": "MindBook is ready.",
                    "result": {
                        "video_id": video_id,
                        "content": content,
                        "knowledge_graph": knowledge_graph,
                        "deep_dive": deep_dive,
                        "synthesis": synthesis,
                        "study_assets": study_assets,
                    },
                }
            )
        except Exception as exc:
            yield sse({"type": "error", "message": str(exc) or "Processing failed."})
        finally:
            for service in services:
                service.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------
# Processing status
# --------------------------------------------------


@app.get("/status/{video_id}")
def get_status(video_id: str):
    status = processing_status.get(video_id)

    if status is None:
        return {
            "video_id": video_id,
            "status": "not_found",
        }

    return {
        "video_id": video_id,
        "status": status,
    }


# --------------------------------------------------
# Get complete result
# --------------------------------------------------


@app.get("/result/{video_id}")
async def get_result(video_id: str):

    content_service = ContentParseService()
    kg_service = KGService()
    deep_dive_service = DeepDiveService()
    synthesis_service = SynthesisService()
    study_assets_service = StudyAssetsService()

    try:
        content = await content_service.get(video_id)

        knowledge_graph = await kg_service.get(video_id)

        deep_dive = await deep_dive_service.get(video_id)

        synthesis = await synthesis_service.get(video_id)

        study_assets = await study_assets_service.get(video_id)

        return {
            "video_id": video_id,
            "content": content,
            "knowledge_graph": knowledge_graph,
            "deep_dive": deep_dive,
            "synthesis": synthesis,
            "study_assets": study_assets,
        }

    finally:
        content_service.close()
        kg_service.close()
        deep_dive_service.close()
        synthesis_service.close()
        study_assets_service.close()


# --------------------------------------------------
# Ask question using RAG
# --------------------------------------------------


@app.post("/ask")
def ask_question(request: AskRequest):

    # Embedding model loads only when /ask is actually called.
    retriever = get_retriever()

    retrieved_chunks = retriever.retrieve(
        query=request.question,
        video_id=request.video_id,
        limit=5,
    )

    if not retrieved_chunks:
        return {"answer": "No relevant information found."}

    context = context_builder.build(retrieved_chunks)

    answer = generator.generate(
        question=request.question,
        context=context,
    )

    return {"answer": answer}
