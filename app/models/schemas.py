"""Pydantic models for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversionResponse(BaseModel):
    """Response model for successful conversion."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Human-readable status message")
    total_slides: int = Field(..., description="Number of slides converted")
    images: List[str] = Field(..., description="List of image paths/URLs")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "message": "Successfully converted 5 slides",
                "total_slides": 5,
                "images": [
                    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_001.jpg",
                    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_002.jpg",
                ],
                "processing_time_ms": 3450,
            }
        }
    }


class JobStatusResponse(BaseModel):
    """Response model for job status queries."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    message: str = Field(..., description="Human-readable status message")
    images: Optional[List[str]] = Field(None, description="List of image paths (when completed)")
    error: Optional[str] = Field(None, description="Error message (when failed)")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "progress": 100,
                "message": "Successfully converted 5 slides",
                "images": [
                    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_001.jpg",
                ],
                "error": None,
                "created_at": "2026-01-15T10:30:00Z",
                "completed_at": "2026-01-15T10:30:03Z",
            }
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Detailed error message")
    job_id: Optional[str] = Field(None, description="Related job ID if applicable")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "ConversionError",
                "detail": "Failed to convert PPTX: LibreOffice process timed out",
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="Service version")
    libreoffice_available: bool = Field(..., description="LibreOffice dependency status")
    poppler_available: bool = Field(..., description="Poppler dependency status")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "libreoffice_available": True,
                "poppler_available": True,
            }
        }
    }
