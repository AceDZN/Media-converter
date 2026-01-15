# Implementation Agent

A specialized agent for implementing new features in the Media Converter project following established patterns and best practices.

## Purpose

Guide the implementation of new converters, API endpoints, and features while maintaining consistency with the existing codebase architecture.

## Project Architecture Reference

```
app/
├── main.py              # FastAPI app, lifespan, routers
├── config.py            # Pydantic Settings class
├── api/v1/endpoints/    # API endpoint handlers
├── services/            # Business logic (converters)
├── models/              # Pydantic schemas
└── utils/               # Helper functions
```

## Implementation Patterns

### 1. New Converter Service

**File:** `app/services/{format}_converter.py`

```python
import subprocess
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Custom exception for conversion failures."""
    pass


@dataclass
class ConversionResult:
    """Standard result format for all converters."""
    success: bool
    output_files: List[str]
    file_count: int
    error: Optional[str] = None


class {Format}Converter:
    """
    Converts {input_format} to {output_format}.

    Pipeline: {describe conversion steps}
    """

    def __init__(self):
        self.settings = get_settings()
        self._validate_dependencies()

    def _validate_dependencies(self) -> None:
        """Verify required system binaries are available."""
        try:
            result = subprocess.run(
                ["binary", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            logger.info(f"Dependency version: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise ConversionError(f"Dependency not available: {e}")

    def convert(self, input_path: str, job_id: str) -> ConversionResult:
        """
        Main conversion method. MUST be synchronous for ProcessPoolExecutor.

        Args:
            input_path: Absolute path to input file
            job_id: Unique job identifier

        Returns:
            ConversionResult with success status and output paths
        """
        input_path = Path(input_path)

        if not input_path.exists():
            return ConversionResult(
                success=False,
                output_files=[],
                file_count=0,
                error=f"Input file not found: {input_path}"
            )

        # Create output directory
        output_dir = Path(self.settings.upload_dir) / "{format}-output" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Stage 1: First conversion step
            intermediate = self._stage_one(input_path, output_dir)

            # Stage 2: Second conversion step (if needed)
            outputs = self._stage_two(intermediate, output_dir)

            # Cleanup intermediate files
            intermediate.unlink(missing_ok=True)

            return ConversionResult(
                success=True,
                output_files=outputs,
                file_count=len(outputs)
            )

        except ConversionError as e:
            logger.error(f"Conversion failed for job {job_id}: {e}")
            return ConversionResult(
                success=False,
                output_files=[],
                file_count=0,
                error=str(e)
            )

    def _stage_one(self, input_path: Path, output_dir: Path) -> Path:
        """First conversion stage."""
        # Implementation
        pass

    def _stage_two(self, input_path: Path, output_dir: Path) -> List[str]:
        """Second conversion stage."""
        # Implementation
        pass


# REQUIRED: Module-level function for ProcessPoolExecutor (must be picklable)
def convert_{format}_sync(input_path: str, job_id: str) -> ConversionResult:
    """Synchronous wrapper for ProcessPoolExecutor."""
    converter = {Format}Converter()
    return converter.convert(input_path, job_id)
```

### 2. API Endpoint

**File:** `app/api/v1/endpoints/convert.py` (add to existing)

```python
@router.post(
    "/{input}-to-{output}",
    response_model=ConversionResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Convert {INPUT} to {OUTPUT}",
    description="Upload a {input} file and convert to {output}."
)
async def convert_{input}_to_{output}(
    file: UploadFile = File(...),
    wait: bool = Query(default=True),
    settings: Settings = Depends(get_settings_dep),
    job_manager: JobManager = Depends(get_job_manager_dep)
) -> ConversionResponse:
    """Convert {input} to {output}."""

    # 1. Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    ext = Path(file.filename).suffix.lower()
    allowed = {".ext1", ".ext2"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid type. Allowed: {allowed}")

    # 2. Generate job ID and save file
    job_id = str(uuid.uuid4())
    upload_dir = Path(settings.upload_dir) / "temp" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    input_path = upload_dir / f"input{ext}"

    # 3. Stream upload to disk
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    total_size = 0

    async with aiofiles.open(input_path, "wb") as f:
        while chunk := await file.read(64 * 1024):
            total_size += len(chunk)
            if total_size > max_bytes:
                input_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large")
            await f.write(chunk)

    # 4. Submit job
    job = await job_manager.submit_job(job_id, str(input_path))

    # 5. Handle sync/async modes
    if wait:
        job = await job_manager.wait_for_job(job_id)
        if job.status == JobStatus.FAILED:
            raise HTTPException(status_code=500, detail=job.error)

    return ConversionResponse(
        job_id=job_id,
        status=job.status,
        message="..." ,
        total_files=len(job.output_files),
        files=job.output_files,
        processing_time_ms=job.processing_time_ms
    )
```

### 3. Configuration Addition

**File:** `app/config.py` (add fields)

```python
class Settings(BaseSettings):
    # Existing fields...

    # New converter settings
    {format}_enabled: bool = True
    {format}_output_format: str = "pdf"
    {format}_timeout: int = 300
```

### 4. Test Structure

**File:** `tests/test_{format}_converter.py`

```python
import pytest
from pathlib import Path
from app.services.{format}_converter import {Format}Converter, ConversionResult


class Test{Format}Converter:
    @pytest.fixture
    def converter(self):
        return {Format}Converter()

    @pytest.fixture
    def sample_file(self, tmp_path):
        # Create or copy sample file
        pass

    def test_convert_valid_file(self, converter, sample_file):
        result = converter.convert(str(sample_file), "test-job-id")
        assert result.success
        assert result.file_count > 0

    def test_convert_missing_file(self, converter):
        result = converter.convert("/nonexistent/file.ext", "test-job-id")
        assert not result.success
        assert "not found" in result.error

    def test_convert_invalid_file(self, converter, tmp_path):
        invalid = tmp_path / "invalid.ext"
        invalid.write_text("not a valid file")
        result = converter.convert(str(invalid), "test-job-id")
        assert not result.success
```

## Checklist for New Features

- [ ] Service class in `app/services/`
- [ ] Module-level sync function for ProcessPoolExecutor
- [ ] API endpoint in `app/api/v1/endpoints/`
- [ ] Pydantic schemas if needed
- [ ] Configuration settings if needed
- [ ] Unit tests for service
- [ ] Integration tests for API
- [ ] Update CLAUDE.md with new endpoint
- [ ] Update API reference in docs

## Output Format

When implementing:

```markdown
## Implementation: {feature_name}

### Files Created/Modified
- `{path}`: {description}

### Testing
```bash
{commands to test the implementation}
```

### Documentation Updates Needed
- {list of docs to update}
```
