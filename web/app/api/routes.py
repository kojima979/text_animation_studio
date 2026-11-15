"""FastAPI ルーティング定義。"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.core.fonts import list_available_fonts, read_license_text
from app.core.storage import JobInfo, job_manager
from app.models.schemas import (
    FontItemResponse,
    JobCreatedResponse,
    JobStatusResponse,
    ScenarioRequest,
    TypewriterRequest,
)
from app.services.scenario_service import generate_scenario_media
from app.services.typewriter_service import generate_typewriter_gif

router = APIRouter(prefix="/api", tags=["api"])


def _to_job_response(job: JobInfo) -> JobStatusResponse:
    output_url = f"/api/outputs/{job.output_filename}" if job.output_filename else None
    download_url = f"/api/download/{job.output_filename}" if job.output_filename else None
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=round(job.progress, 1),
        message_key=job.message_key,
        output_url=output_url,
        download_url=download_url,
        output_filename=job.output_filename,
        output_format=job.output_format,
        file_size_bytes=job.file_size_bytes,
        error_detail=job.error_detail,
    )


@router.get("/fonts", response_model=List[FontItemResponse])
async def get_fonts(include_license_text: bool = Query(default=False)) -> List[FontItemResponse]:
    """利用可能なフリーフォントとライセンス情報を返す。"""
    fonts = list_available_fonts()
    return [
        FontItemResponse(
            id=f.id,
            name=f.name,
            style_ja=f.style_ja,
            style_en=f.style_en,
            license_name=f.license_name,
            license_url=f.license_url,
            copyright=f.copyright,
            source_url=f.source_url,
            license_text=read_license_text(f.id) if include_license_text else None,
        )
        for f in fonts
    ]


@router.post("/typewriter/generate", response_model=JobCreatedResponse)
async def create_typewriter_job(
    req: TypewriterRequest,
    background_tasks: BackgroundTasks,
) -> JobCreatedResponse:
    """Typewriter GIF 生成ジョブを開始する。"""
    job = job_manager.create_job()
    background_tasks.add_task(generate_typewriter_gif, req, job.job_id)
    return JobCreatedResponse(job_id=job.job_id, status=job.status)


@router.post("/scenario/generate", response_model=JobCreatedResponse)
async def create_scenario_job(
    req: ScenarioRequest,
    background_tasks: BackgroundTasks,
) -> JobCreatedResponse:
    """Scenario to Movie 生成ジョブを開始する。"""
    job = job_manager.create_job()
    background_tasks.add_task(generate_scenario_media, req, job.job_id)
    return JobCreatedResponse(job_id=job.job_id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """指定ジョブの現在状態を返す。"""
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_job_response(job)


@router.get("/jobs/{job_id}/events")
async def stream_job_events(job_id: str) -> StreamingResponse:
    """Server-Sent Events (SSE) でジョブの進捗を配信する。"""
    if job_manager.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        last_payload = ""
        while True:
            job = job_manager.get_job(job_id)
            if job is None:
                break
            payload = json.dumps(_to_job_response(job).model_dump(), ensure_ascii=False)
            if payload != last_payload:
                yield f"data: {payload}\n\n"
                last_payload = payload
            if job.status in ("completed", "failed"):
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _media_type_for(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return {
        "gif": "image/gif",
        "apng": "image/apng",
        "png": "image/png",
        "mp4": "video/mp4",
        "webm": "video/webm",
    }.get(ext, "application/octet-stream")


@router.get("/outputs/{filename}")
async def serve_output_inline(filename: str) -> FileResponse:
    """生成ファイルをプレビュー用（inline）として配信する。"""
    path = job_manager.get_output_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Output file not found")
    return FileResponse(path=str(path), media_type=_media_type_for(filename))


@router.get("/download/{filename}")
async def download_output(filename: str) -> FileResponse:
    """生成ファイルをダウンロード用（attachment）として配信する。"""
    path = job_manager.get_output_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Output file not found")
    return FileResponse(
        path=str(path),
        media_type=_media_type_for(filename),
        filename=path.name,
    )
