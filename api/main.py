from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from storage.services.ContentParseService import ContentParseService
from storage.services.KG_Service import KGService
from storage.services.deep_dive_service import DeepDiveService
from storage.services.study_assets_service import StudyAssetsService
from storage.services.synthesis_service import SynthesisService

from test_new_notes import run_pipeline
from video_processor.services.parser import extract_video_id

from pipeline.embeddings.embedder import EmbeddingService
from pipeline.vectorstore.qdrant_store import QdrantStore
from pipeline.retrieval.retriever import Retriever
from pipeline.rag.context_builder import ContextBuilder
from pipeline.rag.generator import Generator

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


# --------------------------------------------------
# Health
# --------------------------------------------------


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "MindBook API is running",
    }


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
        request.question,
        limit=5,
    )

    # Keep only chunks belonging to the current video.
    retrieved_chunks = [
        chunk for chunk in retrieved_chunks if chunk["video_id"] == request.video_id
    ]

    if not retrieved_chunks:
        return {"answer": "No relevant information found."}

    context = context_builder.build(retrieved_chunks)

    answer = generator.generate(
        question=request.question,
        context=context,
    )

    return {"answer": answer}
