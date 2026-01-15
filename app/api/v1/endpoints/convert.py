"""Conversion API endpoints."""

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.config import Settings, get_settings
from app.models.schemas import (
    ConversionResponse,
    ErrorResponse,
    JobStatus,
    JobStatusResponse,
)
from app.services.converter import convert_pptx_sync
from app.services.job_manager import JobManager, get_job_manager

logger = logging.getLogger(__name__)
router = APIRouter()


def get_settings_dep() -> Settings:
    """Dependency for settings."""
    return get_settings()


def get_job_manager_dep() -> JobManager:
    """Dependency for job manager."""
    return get_job_manager()


@router.post(
    "/pptx-to-image",
    response_model=ConversionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        413: {"model": ErrorResponse, "description": "File too large"},
        500: {"model": ErrorResponse, "description": "Conversion failed"},
    },
    summary="Convert PPTX to Images",
    description="Upload a PowerPoint file and convert each slide to a JPEG/PNG image.",
)
async def convert_pptx_to_image(
    file: UploadFile = File(..., description="PPTX or PPT file to convert"),
    wait: bool = Query(
        default=True,
        description="Wait for conversion to complete (sync mode). Set to false for async.",
    ),
    settings: Settings = Depends(get_settings_dep),
    job_manager: JobManager = Depends(get_job_manager_dep),
) -> ConversionResponse:
    """
    Convert a PowerPoint presentation to images.

    - **file**: The .pptx or .ppt file to convert
    - **wait**: If true (default), waits for conversion and returns images.
                If false, returns job_id immediately for polling via /status endpoint.
    """
    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_ext}'. Allowed: {', '.join(settings.allowed_extensions)}",
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Create temp directory for upload
    upload_dir = Path(settings.upload_dir) / "temp" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename and create input path
    safe_filename = f"input{file_ext}"
    input_path = upload_dir / safe_filename

    # Calculate max bytes
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    try:
        # Stream file to disk (memory efficient)
        total_size = 0
        async with aiofiles.open(input_path, "wb") as f:
            while chunk := await file.read(64 * 1024):  # 64KB chunks
                total_size += len(chunk)
                if total_size > max_bytes:
                    # Clean up and reject
                    await f.close()
                    input_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB",
                    )
                await f.write(chunk)

        logger.info(f"Received file: {file.filename} ({total_size} bytes) -> Job {job_id}")

        # Submit conversion job
        job = await job_manager.submit_job(job_id, str(input_path), convert_pptx_sync)

        # Sync mode: wait for completion
        if wait:
            job = await job_manager.wait_for_job(job_id)

            if job is None:
                raise HTTPException(status_code=500, detail="Job not found after submission")

            if job.status.value == JobStatus.FAILED.value:
                raise HTTPException(status_code=500, detail=job.error or "Conversion failed")

            return ConversionResponse(
                job_id=job_id,
                status=JobStatus(job.status.value),
                message=f"Successfully converted {len(job.images)} slides",
                total_slides=len(job.images),
                images=job.images,
                processing_time_ms=job.processing_time_ms,
            )

        # Async mode: return immediately
        return ConversionResponse(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            message="Conversion job submitted. Poll /status/{job_id} for results.",
            total_slides=0,
            images=[],
            processing_time_ms=0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Conversion endpoint error for job {job_id}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse, "description": "Job not found"}},
    summary="Get Job Status",
    description="Check the status of a conversion job.",
)
async def get_job_status(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager_dep),
) -> JobStatusResponse:
    """Get the status of a conversion job by ID."""
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Generate status message
    if job.status.value == "pending":
        message = "Job is queued for processing"
    elif job.status.value == "processing":
        message = "Conversion in progress..."
    elif job.status.value == "completed":
        message = f"Successfully converted {len(job.images)} slides"
    else:
        message = f"Conversion failed: {job.error}"

    return JobStatusResponse(
        job_id=job.id,
        status=JobStatus(job.status.value),
        progress=job.progress,
        message=message,
        images=job.images if job.status.value == "completed" else None,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
