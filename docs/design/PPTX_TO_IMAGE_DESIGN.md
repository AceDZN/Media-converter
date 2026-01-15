# Technical Design Document: PPTX-to-Image Conversion Module

**Version:** 1.0
**Date:** 2026-01-15
**Status:** Draft

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Technology Selection](#2-technology-selection)
3. [Architecture & Concurrency](#3-architecture--concurrency)
4. [Implementation Plan](#4-implementation-plan)
5. [Scalability Notes](#5-scalability-notes)
6. [Risks & Mitigations](#6-risks--mitigations)

---

## 1. Executive Summary

This document outlines the technical design for a self-hosted PPTX-to-Image conversion service. The module accepts PowerPoint files (`.ppt`/`.pptx`), converts each slide to a high-fidelity image, and returns the image paths via a REST API.

**Key Design Decisions:**
- **Conversion Pipeline:** `PPTX → PDF → Images` (two-stage conversion for maximum fidelity)
- **Web Framework:** FastAPI (async-first, high performance)
- **Concurrency:** `ProcessPoolExecutor` with bounded workers (no Redis required)
- **Deployment:** Docker container with LibreOffice headless + Poppler

---

## 2. Technology Selection

### 2.1 Web Framework: FastAPI

| Criteria | FastAPI | Flask | Django |
|----------|---------|-------|--------|
| Native Async | ✅ Built-in | ❌ Requires extensions | ⚠️ Django 4.1+ partial |
| Background Tasks | ✅ Built-in | ❌ Requires Celery | ❌ Requires Celery |
| Performance | ✅ High (Starlette) | ⚠️ Moderate | ⚠️ Moderate |
| API Documentation | ✅ Auto OpenAPI | ❌ Manual | ❌ Manual |
| File Upload Handling | ✅ Excellent | ✅ Good | ✅ Good |

**Decision:** FastAPI is ideal because:
1. Native `async/await` support allows non-blocking file I/O
2. Built-in `BackgroundTasks` for simple async operations
3. Easy integration with `ProcessPoolExecutor` for CPU-bound work
4. Automatic request validation via Pydantic
5. Auto-generated OpenAPI docs for testing/integration

### 2.2 Conversion Pipeline: Why PPTX → PDF → Images?

We evaluated three approaches:

#### Option A: Direct PPTX → Images (python-pptx + Pillow)
```
❌ REJECTED
- python-pptx cannot render slides (read/write metadata only)
- Would require manual rendering of shapes, text, charts
- Poor fidelity for complex presentations
```

#### Option B: Direct PPTX → Images (LibreOffice)
```
⚠️ POSSIBLE BUT SUBOPTIMAL
- LibreOffice can export directly to images
- Command: soffice --convert-to png --outdir ...
- Issues: Limited DPI control, inconsistent quality
```

#### Option C: PPTX → PDF → Images (LibreOffice + Poppler) ✅
```
✅ RECOMMENDED
- Stage 1: LibreOffice converts PPTX to PDF (perfect fidelity)
- Stage 2: Poppler converts PDF pages to images (high quality, configurable DPI)
- Best of both worlds: LibreOffice's rendering + Poppler's image quality
```

**Why LibreOffice over alternatives:**

| Tool | License | PPT Support | PPTX Support | Fidelity | Headless |
|------|---------|-------------|--------------|----------|----------|
| LibreOffice | MPL-2.0 | ✅ Excellent | ✅ Excellent | ✅ High | ✅ Yes |
| Apache POI | Apache-2.0 | ⚠️ Partial | ⚠️ Partial | ❌ Low | ✅ Yes |
| Aspose | Commercial | ✅ | ✅ | ✅ | ✅ | ❌ Violates "No Paid SaaS" |
| unoconv | GPL | ✅ | ✅ | ✅ | ✅ | Wrapper around LibreOffice |

**LibreOffice is the clear winner** - it's the only open-source solution that handles both legacy `.ppt` and modern `.pptx` with near-perfect fidelity.

### 2.3 System Dependencies

| Dependency | Purpose | Installation |
|------------|---------|--------------|
| LibreOffice | PPTX/PPT → PDF conversion | `apt-get install libreoffice` |
| Poppler-utils | PDF → Image conversion | `apt-get install poppler-utils` |
| Fonts | Proper text rendering | `apt-get install fonts-liberation fonts-dejavu` |

### 2.4 Python Dependencies

```
fastapi>=0.109.0          # Web framework
uvicorn[standard]>=0.27.0 # ASGI server
python-multipart>=0.0.6   # File upload parsing
pdf2image>=1.16.3         # Poppler Python wrapper
aiofiles>=23.2.1          # Async file operations
pydantic>=2.5.0           # Data validation
pydantic-settings>=2.1.0  # Settings management
```

---

## 3. Architecture & Concurrency

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Container                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      FastAPI Server                        │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │  │
│  │  │   /convert  │───▶│  Job Queue  │───▶│ ProcessPool  │   │  │
│  │  │  (endpoint) │    │  (in-memory)│    │ (3 workers)  │   │  │
│  │  └─────────────┘    └─────────────┘    └──────┬───────┘   │  │
│  │         │                                      │           │  │
│  │         │              ┌───────────────────────┘           │  │
│  │         │              ▼                                   │  │
│  │         │     ┌────────────────┐     ┌────────────────┐   │  │
│  │         │     │  LibreOffice   │────▶│    Poppler     │   │  │
│  │         │     │  (PPTX → PDF)  │     │  (PDF → IMG)   │   │  │
│  │         │     └────────────────┘     └───────┬────────┘   │  │
│  │         │                                    │             │  │
│  │         ▼                                    ▼             │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              File System (uploads/)                  │  │  │
│  │  │   uploads/pptx-to-image/{job_id}/slide_{n}.jpg      │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Concurrency Strategy: ProcessPoolExecutor

**Why not other approaches?**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| `BackgroundTasks` | Simple, built-in | Runs in main thread, blocks event loop for CPU work | ❌ Not suitable |
| `asyncio.create_subprocess` | Non-blocking subprocess | Complex error handling, no worker limit | ⚠️ Possible |
| `ThreadPoolExecutor` | Good for I/O-bound | GIL limits CPU parallelism | ❌ Not ideal |
| **`ProcessPoolExecutor`** | True parallelism, bounded workers | Slightly more complex | ✅ **Recommended** |

**Our Strategy:**

```python
# Create a bounded process pool (limits concurrent conversions)
executor = ProcessPoolExecutor(max_workers=3)

# Submit conversion jobs without blocking the event loop
future = executor.submit(convert_pptx_sync, file_path, job_id)
```

**Why max_workers=3?**
- LibreOffice is memory-intensive (~200-500MB per instance)
- With 3 workers on a typical 4-core/8GB container, we balance throughput vs. resource exhaustion
- Configurable via environment variable for different deployment sizes

### 3.3 Request Flow

```
1. Client POST /api/v1/convert/pptx-to-image (multipart file)
          │
          ▼
2. FastAPI validates file (extension, size limit)
          │
          ▼
3. Generate job_id (UUID), save uploaded file to temp location
          │
          ▼
4. Submit to ProcessPoolExecutor (non-blocking)
          │
          ├─── Sync Mode: await result, return images
          │
          └─── Async Mode: return job_id immediately, poll /status/{job_id}

5. Worker Process:
   a. Run LibreOffice: pptx → pdf
   b. Run Poppler: pdf → images (one per page)
   c. Save to uploads/pptx-to-image/{job_id}/slide_{n}.jpg
   d. Update job status
          │
          ▼
6. Return JSON with image paths/URLs
```

### 3.4 Job State Management (In-Memory)

For low-traffic scenarios without Redis, we use a simple in-memory store:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import asyncio

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0  # 0-100
    images: List[str] = field(default_factory=list)
    error: Optional[str] = None

# Thread-safe job store
class JobStore:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = asyncio.Lock()
```

**Limitations (acceptable for low traffic):**
- Jobs lost on server restart (add persistence later if needed)
- Memory grows with jobs (implement TTL cleanup)

---

## 4. Implementation Plan

### 4.1 Project Structure

```
Media-converter/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Settings/configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # API router
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       └── convert.py  # Conversion endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── converter.py        # PptxConverter class
│   │   └── job_manager.py      # Job state management
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py       # File handling utilities
├── uploads/                    # Generated files (gitignored)
├── tests/
│   ├── __init__.py
│   ├── test_converter.py
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### 4.2 Dockerfile

```dockerfile
# =============================================================================
# Multi-stage Dockerfile for Media Converter Service
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base image with system dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # LibreOffice for document conversion
    libreoffice \
    # Poppler for PDF to image conversion
    poppler-utils \
    # Fonts for proper text rendering
    fonts-liberation \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    # Clean up apt cache to reduce image size
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*

# -----------------------------------------------------------------------------
# Stage 2: Python dependencies
# -----------------------------------------------------------------------------
FROM base AS dependencies

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 3: Final production image
# -----------------------------------------------------------------------------
FROM dependencies AS production

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser ./app ./app

# Create uploads directory with correct permissions
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app/uploads

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    MAX_WORKERS=3 \
    UPLOAD_DIR=/app/uploads

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.3 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  media-converter:
    build:
      context: .
      target: production
    ports:
      - "8000:8000"
    volumes:
      # Persist uploads between container restarts
      - ./uploads:/app/uploads
    environment:
      - APP_ENV=development
      - MAX_WORKERS=3
      - MAX_FILE_SIZE_MB=100
      - IMAGE_DPI=200
      - IMAGE_FORMAT=JPEG
      - LOG_LEVEL=INFO
    # Resource limits to prevent runaway processes
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 1G
    restart: unless-stopped
```

### 4.4 Configuration (config.py)

```python
# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration with environment variable support."""

    # Application
    app_name: str = "Media Converter"
    app_env: Literal["development", "production", "testing"] = "development"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # File handling
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 100  # Maximum upload size in MB
    allowed_extensions: set = {".ppt", ".pptx"}

    # Conversion settings
    image_dpi: int = Field(default=200, ge=72, le=600)
    image_format: Literal["JPEG", "PNG"] = "JPEG"
    jpeg_quality: int = Field(default=90, ge=1, le=100)

    # Concurrency
    max_workers: int = Field(default=3, ge=1, le=10)
    job_timeout_seconds: int = 300  # 5 minutes max per job

    # Cleanup
    job_ttl_hours: int = 24  # Clean up jobs older than this

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
```

### 4.5 Pydantic Models (schemas.py)

```python
# app/models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversionRequest(BaseModel):
    """Request model for conversion (used for documentation)."""
    file: str = Field(..., description="The PPTX/PPT file to convert")


class ConversionResponse(BaseModel):
    """Response model for successful conversion."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Human-readable status message")
    total_slides: int = Field(..., description="Number of slides converted")
    images: List[str] = Field(..., description="List of image paths/URLs")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "message": "Successfully converted 5 slides",
                "total_slides": 5,
                "images": [
                    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_001.jpg",
                    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_002.jpg"
                ],
                "processing_time_ms": 3450
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status queries."""
    job_id: str
    status: JobStatus
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    message: str
    images: Optional[List[str]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str
    job_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ConversionError",
                "detail": "Failed to convert PPTX: LibreOffice process timed out",
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    libreoffice_available: bool
    poppler_available: bool
```

### 4.6 PptxConverter Service Class

```python
# app/services/converter.py
import os
import subprocess
import shutil
import tempfile
import logging
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError

from app.config import get_settings

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Custom exception for conversion failures."""
    pass


@dataclass
class ConversionResult:
    """Result of a conversion operation."""
    success: bool
    images: List[str]
    slide_count: int
    error: str = None


class PptxConverter:
    """
    Handles PPTX/PPT to Image conversion using LibreOffice and Poppler.

    Conversion Pipeline:
    1. PPTX/PPT → PDF (via LibreOffice headless)
    2. PDF → Images (via Poppler/pdf2image)
    """

    def __init__(self):
        self.settings = get_settings()
        self._validate_dependencies()

    def _validate_dependencies(self) -> None:
        """Verify that required system binaries are available."""
        # Check LibreOffice
        try:
            result = subprocess.run(
                ["soffice", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            logger.info(f"LibreOffice version: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise ConversionError(f"LibreOffice not available: {e}")

        # Check Poppler (pdftoppm)
        try:
            result = subprocess.run(
                ["pdftoppm", "-v"],
                capture_output=True,
                text=True,
                timeout=10
            )
            logger.info(f"Poppler available: {result.stderr.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise ConversionError(f"Poppler not available: {e}")

    def convert(self, input_path: str, job_id: str) -> ConversionResult:
        """
        Convert a PPTX/PPT file to images.

        This is a SYNCHRONOUS method designed to run in a ProcessPoolExecutor.

        Args:
            input_path: Path to the input PPTX/PPT file
            job_id: Unique job identifier for output directory

        Returns:
            ConversionResult with success status and image paths
        """
        input_path = Path(input_path)

        if not input_path.exists():
            return ConversionResult(
                success=False,
                images=[],
                slide_count=0,
                error=f"Input file not found: {input_path}"
            )

        # Create output directory
        output_dir = Path(self.settings.upload_dir) / "pptx-to-image" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Stage 1: Convert PPTX to PDF
            pdf_path = self._convert_to_pdf(input_path, output_dir)

            # Stage 2: Convert PDF to Images
            images = self._convert_pdf_to_images(pdf_path, output_dir)

            # Clean up intermediate PDF
            pdf_path.unlink(missing_ok=True)

            return ConversionResult(
                success=True,
                images=images,
                slide_count=len(images),
                error=None
            )

        except ConversionError as e:
            logger.error(f"Conversion failed for job {job_id}: {e}")
            return ConversionResult(
                success=False,
                images=[],
                slide_count=0,
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"Unexpected error in job {job_id}")
            return ConversionResult(
                success=False,
                images=[],
                slide_count=0,
                error=f"Unexpected error: {e}"
            )

    def _convert_to_pdf(self, input_path: Path, output_dir: Path) -> Path:
        """
        Convert PPTX/PPT to PDF using LibreOffice.

        Args:
            input_path: Path to input file
            output_dir: Directory for output PDF

        Returns:
            Path to generated PDF file
        """
        logger.info(f"Converting {input_path.name} to PDF...")

        # LibreOffice command for headless PDF conversion
        cmd = [
            "soffice",
            "--headless",                    # No GUI
            "--invisible",                   # Don't show splash screen
            "--nologo",                      # No logo
            "--nofirststartwizard",          # Skip first-run wizard
            "--convert-to", "pdf",           # Output format
            "--outdir", str(output_dir),     # Output directory
            str(input_path)                  # Input file
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.settings.job_timeout_seconds,
                cwd=output_dir  # Set working directory
            )

            if result.returncode != 0:
                raise ConversionError(
                    f"LibreOffice conversion failed: {result.stderr}"
                )

            # LibreOffice creates PDF with same base name
            pdf_path = output_dir / f"{input_path.stem}.pdf"

            if not pdf_path.exists():
                raise ConversionError(
                    f"PDF not created. LibreOffice output: {result.stdout} {result.stderr}"
                )

            logger.info(f"PDF created: {pdf_path}")
            return pdf_path

        except subprocess.TimeoutExpired:
            raise ConversionError(
                f"LibreOffice conversion timed out after {self.settings.job_timeout_seconds}s"
            )

    def _convert_pdf_to_images(self, pdf_path: Path, output_dir: Path) -> List[str]:
        """
        Convert PDF pages to images using Poppler.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for output images

        Returns:
            List of image file paths (relative to upload directory)
        """
        logger.info(f"Converting PDF to images (DPI: {self.settings.image_dpi})...")

        try:
            # Convert PDF to PIL Images
            images = convert_from_path(
                pdf_path,
                dpi=self.settings.image_dpi,
                fmt=self.settings.image_format.lower(),
                thread_count=2,  # Parallel page processing
                use_pdftocairo=True,  # Better quality than pdftoppm
            )

            image_paths = []

            for idx, image in enumerate(images, start=1):
                # Generate filename: slide_001.jpg, slide_002.jpg, etc.
                filename = f"slide_{idx:03d}.{self.settings.image_format.lower()}"
                filepath = output_dir / filename

                # Save image with quality settings
                save_kwargs = {}
                if self.settings.image_format == "JPEG":
                    save_kwargs["quality"] = self.settings.jpeg_quality
                    save_kwargs["optimize"] = True
                elif self.settings.image_format == "PNG":
                    save_kwargs["optimize"] = True

                image.save(filepath, self.settings.image_format, **save_kwargs)

                # Store relative path for API response
                relative_path = str(filepath.relative_to(self.settings.upload_dir))
                image_paths.append(f"/uploads/{relative_path}")

                logger.debug(f"Saved slide {idx}: {filepath}")

            logger.info(f"Created {len(image_paths)} images")
            return image_paths

        except PDFInfoNotInstalledError:
            raise ConversionError("Poppler (pdfinfo) not installed")
        except PDFPageCountError:
            raise ConversionError("Could not determine PDF page count")
        except Exception as e:
            raise ConversionError(f"PDF to image conversion failed: {e}")


# Standalone function for ProcessPoolExecutor (must be picklable)
def convert_pptx_sync(input_path: str, job_id: str) -> ConversionResult:
    """
    Synchronous conversion function for use with ProcessPoolExecutor.

    This function is defined at module level to be picklable.
    """
    converter = PptxConverter()
    return converter.convert(input_path, job_id)
```

### 4.7 Job Manager

```python
# app/services/job_manager.py
import asyncio
from concurrent.futures import ProcessPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum
import logging

from app.config import get_settings
from app.services.converter import convert_pptx_sync, ConversionResult

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Represents a conversion job."""
    id: str
    input_path: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    images: List[str] = field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    processing_time_ms: int = 0


class JobManager:
    """
    Manages conversion jobs with in-memory state storage.

    Uses ProcessPoolExecutor for CPU-bound conversion work,
    allowing the async event loop to remain responsive.
    """

    _instance: Optional["JobManager"] = None

    def __new__(cls):
        """Singleton pattern for shared executor."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.settings = get_settings()
        self._jobs: Dict[str, Job] = {}
        self._futures: Dict[str, Future] = {}
        self._lock = asyncio.Lock()
        self._executor = ProcessPoolExecutor(
            max_workers=self.settings.max_workers
        )
        self._initialized = True
        logger.info(f"JobManager initialized with {self.settings.max_workers} workers")

    async def submit_job(self, job_id: str, input_path: str) -> Job:
        """
        Submit a new conversion job.

        Args:
            job_id: Unique job identifier
            input_path: Path to input PPTX file

        Returns:
            Job instance
        """
        async with self._lock:
            job = Job(id=job_id, input_path=input_path)
            self._jobs[job_id] = job

            # Submit to process pool
            future = self._executor.submit(convert_pptx_sync, input_path, job_id)
            self._futures[job_id] = future

            # Add callback for completion
            future.add_done_callback(
                lambda f: asyncio.create_task(self._handle_completion(job_id, f))
            )

            job.status = JobStatus.PROCESSING
            logger.info(f"Job {job_id} submitted for processing")
            return job

    async def _handle_completion(self, job_id: str, future: Future) -> None:
        """Handle job completion callback."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            try:
                result: ConversionResult = future.result()

                if result.success:
                    job.status = JobStatus.COMPLETED
                    job.images = result.images
                    job.progress = 100
                else:
                    job.status = JobStatus.FAILED
                    job.error = result.error

            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                logger.exception(f"Job {job_id} failed with exception")

            job.completed_at = datetime.utcnow()
            job.processing_time_ms = int(
                (job.completed_at - job.created_at).total_seconds() * 1000
            )

            # Clean up future reference
            self._futures.pop(job_id, None)
            logger.info(f"Job {job_id} completed with status: {job.status}")

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    async def wait_for_job(self, job_id: str, timeout: float = None) -> Optional[Job]:
        """
        Wait for job completion (for synchronous API mode).

        Args:
            job_id: Job identifier
            timeout: Maximum wait time in seconds

        Returns:
            Completed Job or None if timeout
        """
        timeout = timeout or self.settings.job_timeout_seconds
        start = datetime.utcnow()

        while True:
            job = await self.get_job(job_id)
            if not job:
                return None

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                return job

            # Check timeout
            elapsed = (datetime.utcnow() - start).total_seconds()
            if elapsed >= timeout:
                job.status = JobStatus.FAILED
                job.error = f"Job timed out after {timeout}s"
                return job

            # Poll interval
            await asyncio.sleep(0.5)

    async def cleanup_old_jobs(self, max_age_hours: int = None) -> int:
        """Remove jobs older than max_age_hours."""
        max_age = max_age_hours or self.settings.job_ttl_hours
        cutoff = datetime.utcnow() - timedelta(hours=max_age)

        async with self._lock:
            old_jobs = [
                jid for jid, job in self._jobs.items()
                if job.created_at < cutoff
            ]
            for jid in old_jobs:
                del self._jobs[jid]

            if old_jobs:
                logger.info(f"Cleaned up {len(old_jobs)} old jobs")
            return len(old_jobs)

    def shutdown(self):
        """Gracefully shutdown the executor."""
        self._executor.shutdown(wait=True)
        logger.info("JobManager shutdown complete")


# Convenience function to get manager instance
def get_job_manager() -> JobManager:
    return JobManager()
```

### 4.8 API Endpoint

```python
# app/api/v1/endpoints/convert.py
import os
import uuid
import aiofiles
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from app.config import get_settings, Settings
from app.models.schemas import (
    ConversionResponse,
    JobStatusResponse,
    ErrorResponse,
    JobStatus
)
from app.services.job_manager import get_job_manager, JobManager

logger = logging.getLogger(__name__)
router = APIRouter()


def get_settings_dep() -> Settings:
    return get_settings()


def get_job_manager_dep() -> JobManager:
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
    description="Upload a PowerPoint file and convert each slide to a JPEG image."
)
async def convert_pptx_to_image(
    file: UploadFile = File(..., description="PPTX or PPT file to convert"),
    wait: bool = Query(
        default=True,
        description="Wait for conversion to complete (sync mode)"
    ),
    settings: Settings = Depends(get_settings_dep),
    job_manager: JobManager = Depends(get_job_manager_dep)
) -> ConversionResponse:
    """
    Convert a PowerPoint presentation to images.

    - **file**: The .pptx or .ppt file to convert
    - **wait**: If true, waits for conversion and returns images.
                If false, returns job_id immediately for polling.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_ext}'. Allowed: {settings.allowed_extensions}"
        )

    # Check file size (read content-length or check after upload)
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Create temp directory for upload
    upload_dir = Path(settings.upload_dir) / "temp" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename and save
    safe_filename = f"input{file_ext}"
    input_path = upload_dir / safe_filename

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
                        detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
                    )
                await f.write(chunk)

        logger.info(f"Received file: {file.filename} ({total_size} bytes) -> Job {job_id}")

        # Submit conversion job
        job = await job_manager.submit_job(job_id, str(input_path))

        # Sync mode: wait for completion
        if wait:
            job = await job_manager.wait_for_job(job_id)

            if job.status == JobStatus.FAILED:
                raise HTTPException(
                    status_code=500,
                    detail=job.error or "Conversion failed"
                )

            return ConversionResponse(
                job_id=job_id,
                status=job.status,
                message=f"Successfully converted {len(job.images)} slides",
                total_slides=len(job.images),
                images=job.images,
                processing_time_ms=job.processing_time_ms
            )

        # Async mode: return immediately
        return ConversionResponse(
            job_id=job_id,
            status=job.status,
            message="Conversion job submitted. Poll /status endpoint for results.",
            total_slides=0,
            images=[],
            processing_time_ms=0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Conversion endpoint error for job {job_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get Job Status",
    description="Check the status of a conversion job."
)
async def get_job_status(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager_dep)
) -> JobStatusResponse:
    """Get the status of a conversion job by ID."""
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        message=_get_status_message(job),
        images=job.images if job.status == JobStatus.COMPLETED else None,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at
    )


def _get_status_message(job) -> str:
    """Generate human-readable status message."""
    if job.status == JobStatus.PENDING:
        return "Job is queued for processing"
    elif job.status == JobStatus.PROCESSING:
        return "Conversion in progress..."
    elif job.status == JobStatus.COMPLETED:
        return f"Successfully converted {len(job.images)} slides"
    else:
        return f"Conversion failed: {job.error}"
```

### 4.9 Main Application Entry

```python
# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1.endpoints import convert
from app.services.job_manager import get_job_manager
from app.models.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.app_name}...")

    # Initialize job manager (creates process pool)
    job_manager = get_job_manager()

    # Mount static files for serving images
    from pathlib import Path
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

    logger.info(f"Server ready. Upload directory: {upload_path}")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down...")
    job_manager.shutdown()


# Create FastAPI application
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Self-hosted media conversion service. Convert PPTX to images and more.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check service health and dependencies."""
    import subprocess

    # Check LibreOffice
    try:
        subprocess.run(["soffice", "--version"], capture_output=True, timeout=5)
        lo_available = True
    except Exception:
        lo_available = False

    # Check Poppler
    try:
        subprocess.run(["pdftoppm", "-v"], capture_output=True, timeout=5)
        poppler_available = True
    except Exception:
        poppler_available = False

    return HealthResponse(
        status="healthy" if (lo_available and poppler_available) else "degraded",
        version="1.0.0",
        libreoffice_available=lo_available,
        poppler_available=poppler_available
    )


# Include API routers
app.include_router(
    convert.router,
    prefix="/api/v1/convert",
    tags=["Conversion"]
)


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs"
    }
```

### 4.10 Requirements File

```
# requirements.txt

# Web Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# File Handling
python-multipart>=0.0.6
aiofiles>=23.2.1

# PDF/Image Processing
pdf2image>=1.16.3
Pillow>=10.2.0

# Configuration
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Development/Testing (optional)
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
```

---

## 5. Scalability Notes

### 5.1 Current Architecture Limitations

| Aspect | Current Design | Limitation |
|--------|----------------|------------|
| Job Storage | In-memory dict | Lost on restart, single-instance only |
| Task Queue | ProcessPoolExecutor | No persistence, no retry logic |
| Scaling | Vertical only | Can't distribute across machines |
| Monitoring | Basic logging | No job metrics/dashboards |

### 5.2 Migration Path to Redis/Celery

When traffic increases, the migration to a distributed architecture is straightforward:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FUTURE ARCHITECTURE                               │
│                                                                          │
│  ┌──────────────┐     ┌─────────────┐     ┌──────────────────────────┐  │
│  │   FastAPI    │────▶│    Redis    │────▶│   Celery Workers (N)     │  │
│  │   (API)      │     │   (Broker)  │     │   ┌────────────────────┐ │  │
│  └──────────────┘     └─────────────┘     │   │ Worker 1           │ │  │
│         │                    │            │   │ (LibreOffice)      │ │  │
│         │                    │            │   └────────────────────┘ │  │
│         │                    ▼            │   ┌────────────────────┐ │  │
│         │            ┌─────────────┐      │   │ Worker 2           │ │  │
│         └───────────▶│    Redis    │      │   │ (LibreOffice)      │ │  │
│                      │  (Results)  │◀─────│   └────────────────────┘ │  │
│                      └─────────────┘      │   ┌────────────────────┐ │  │
│                                           │   │ Worker N           │ │  │
│                                           │   │ (LibreOffice)      │ │  │
│                                           │   └────────────────────┘ │  │
│                                           └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Code Changes Required

**1. Add Celery Task (minimal changes to converter.py):**

```python
# app/tasks/convert_tasks.py
from celery import Celery
from app.services.converter import PptxConverter, ConversionResult

celery_app = Celery('tasks', broker='redis://redis:6379/0')

@celery_app.task(bind=True, max_retries=3)
def convert_pptx_task(self, input_path: str, job_id: str) -> dict:
    """Celery task wrapper for PPTX conversion."""
    try:
        converter = PptxConverter()
        result = converter.convert(input_path, job_id)
        return result.__dict__
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
```

**2. Update Job Manager:**

```python
# Replace ProcessPoolExecutor submission with:
async def submit_job(self, job_id: str, input_path: str) -> Job:
    # Instead of: future = self._executor.submit(...)
    # Use: task = convert_pptx_task.delay(input_path, job_id)

    job = Job(id=job_id, input_path=input_path, celery_task_id=task.id)
    await self._store_job(job)  # Now stores in Redis
    return job
```

**3. Add docker-compose services:**

```yaml
# docker-compose.prod.yml
services:
  redis:
    image: redis:7-alpine

  celery-worker:
    build: .
    command: celery -A app.tasks worker --loglevel=info --concurrency=2
    depends_on:
      - redis
    deploy:
      replicas: 3  # Scale workers horizontally
```

### 5.4 Summary of Changes

| Component | Current | Future (Redis/Celery) |
|-----------|---------|----------------------|
| Job Storage | `Dict[str, Job]` | Redis Hash |
| Task Submission | `executor.submit()` | `task.delay()` |
| Task Execution | ProcessPoolExecutor | Celery Workers |
| Result Retrieval | `future.result()` | `AsyncResult.get()` |
| Scaling | `max_workers=3` | `replicas: N` |

**Estimated effort:** ~2-4 hours to migrate, with ~90% of code unchanged.

---

## 6. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LibreOffice memory leak | High | Medium | Process pool auto-restarts workers; add periodic restart |
| Large file OOM | High | Low | Stream uploads, enforce size limits |
| LibreOffice rendering issues | Medium | Low | Test with diverse PPTX files; maintain font packages |
| Concurrent LibreOffice conflicts | Medium | Medium | Each worker uses separate temp dirs |
| Job loss on crash | Medium | Low | Acceptable for low traffic; add Redis for persistence later |

---

## Appendix A: API Reference

### POST /api/v1/convert/pptx-to-image

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/convert/pptx-to-image" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@presentation.pptx" \
  -F "wait=true"
```

**Response (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Successfully converted 5 slides",
  "total_slides": 5,
  "images": [
    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_001.jpg",
    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_002.jpg",
    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_003.jpg",
    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_004.jpg",
    "/uploads/pptx-to-image/550e8400-e29b-41d4-a716-446655440000/slide_005.jpg"
  ],
  "processing_time_ms": 3450
}
```

### GET /api/v1/convert/status/{job_id}

**Request:**
```bash
curl "http://localhost:8000/api/v1/convert/status/550e8400-e29b-41d4-a716-446655440000"
```

**Response (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "message": "Successfully converted 5 slides",
  "images": ["..."],
  "error": null,
  "created_at": "2026-01-15T10:30:00Z",
  "completed_at": "2026-01-15T10:30:03Z"
}
```

---

## Appendix B: Testing Checklist

- [ ] Unit tests for PptxConverter class
- [ ] Integration tests for API endpoints
- [ ] Test with various PPTX files (simple, complex, with animations)
- [ ] Test with legacy .ppt files
- [ ] Load test with 5 concurrent uploads
- [ ] Test file size limits
- [ ] Test invalid file handling
- [ ] Test timeout behavior
- [ ] Docker build and run verification

---

*Document End*
