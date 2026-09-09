from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "MindBook API is running",
    }


@app.post("/process")
def process_video(request: VideoRequest):
    return {
        "status": "received",
        "url": request.url,
    }
