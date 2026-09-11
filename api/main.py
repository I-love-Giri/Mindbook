from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from test_new_notes import run_pipeline
from video_processor.services.parser import extract_video_id

app = FastAPI()


# Allow requests from Next.js frontend
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


class VideoRequest(BaseModel):
    url: str


def test_background_task(video_id: str):
    print(f"Background processing started for {video_id}")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "MindBook API is running",
    }


@app.post("/process")
def process_video(
    request: VideoRequest,
    background_tasks: BackgroundTasks,
):
    video_id = extract_video_id(request.url)

    background_tasks.add_task(run_pipeline, video_id)

    return {
        "status": "processing",
        "video_id": video_id,
    }


@app.get("/status/{video_id}")
def get_status(video_id: str):
    return {
        "video_id": video_id,
        "status": "processing",
    }
