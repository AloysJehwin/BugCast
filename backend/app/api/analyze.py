import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.pipeline.orchestrator import run_pipeline
from app.utils.config import settings

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("")
async def analyze(video: UploadFile) -> JSONResponse:
    if not video.filename or not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="video/* required")

    job_id = uuid.uuid4().hex[:12]
    upload_dir = Path(settings.upload_dir) / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    video_path = upload_dir / video.filename
    with video_path.open("wb") as f:
        f.write(await video.read())

    result = await run_pipeline(job_id=job_id, video_path=video_path)
    return JSONResponse(result)
