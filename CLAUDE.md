# CLAUDE.md - Media Converter Service

## Project Overview

Media Converter is a **self-hosted media transformation service** that converts files between formats without relying on third-party paid APIs. The service provides a REST API built with FastAPI, processes files locally using LibreOffice and Poppler, and runs in Docker.

**Current Module:** PPTX-to-Image conversion (Phase 1)

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.11+ |
| **Web Framework** | FastAPI + Uvicorn |
| **Document Conversion** | LibreOffice (headless) |
| **PDF to Image** | Poppler (via pdf2image) |
| **Async File I/O** | aiofiles |
| **Concurrency** | ProcessPoolExecutor (no Redis) |
| **Containerization** | Docker + docker-compose |

## Directory Structure

```
Media-converter/
├── CLAUDE.md                    # This file - project context for Claude
├── README.md                    # User-facing documentation
├── docs/
│   ├── PRD.md                   # Product Requirements Document
│   └── design/
│       └── PPTX_TO_IMAGE_DESIGN.md  # Technical design document
├── app/                         # Application source code
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic settings
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           └── convert.py   # Conversion endpoints
│   ├── services/
│   │   ├── converter.py         # PptxConverter class
│   │   └── job_manager.py       # Job state management
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   └── utils/
│       └── file_utils.py        # File handling utilities
├── tests/                       # Test suite
│   ├── conftest.py              # Pytest fixtures
│   ├── test_converter.py        # Unit tests for converter
│   └── test_api.py              # API integration tests
├── uploads/                     # Generated files (gitignored)
├── Dockerfile                   # Multi-stage Docker build
├── docker-compose.yml           # Local development setup
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Development dependencies
├── .env.example                 # Environment variable template
└── .claude/                     # Claude Code configuration
    ├── settings.json            # Claude settings
    └── skills/                  # Custom slash commands
```

## Key Design Decisions

1. **Conversion Pipeline:** `PPTX → PDF → Images` (two-stage for best fidelity)
2. **Concurrency:** `ProcessPoolExecutor` with bounded workers (default 3)
3. **Job Storage:** In-memory dict (acceptable for low traffic; Redis migration path exists)
4. **API Modes:** Synchronous (`wait=true`) and asynchronous (`wait=false`) processing

## Common Commands

### Development

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run locally (requires LibreOffice + Poppler installed)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=app --cov-report=html

# Type checking
mypy app/

# Linting
ruff check app/ tests/

# Formatting
ruff format app/ tests/
```

### Docker

```bash
# Build image
docker build -t media-converter:latest .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f media-converter

# Stop
docker-compose down

# Rebuild and run
docker-compose up -d --build
```

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Convert PPTX (synchronous)
curl -X POST http://localhost:8000/api/v1/convert/pptx-to-image \
  -F "file=@presentation.pptx"

# Convert PPTX (asynchronous)
curl -X POST "http://localhost:8000/api/v1/convert/pptx-to-image?wait=false" \
  -F "file=@presentation.pptx"

# Check job status
curl http://localhost:8000/api/v1/convert/status/{job_id}

# View API docs
open http://localhost:8000/docs
```

## Code Patterns

### Adding a New Converter

1. Create service class in `app/services/`:
```python
class NewFormatConverter:
    def __init__(self):
        self.settings = get_settings()

    def convert(self, input_path: str, job_id: str) -> ConversionResult:
        # Implementation
        pass

# Module-level function for ProcessPoolExecutor
def convert_new_format_sync(input_path: str, job_id: str) -> ConversionResult:
    converter = NewFormatConverter()
    return converter.convert(input_path, job_id)
```

2. Add endpoint in `app/api/v1/endpoints/convert.py`
3. Register router in `app/main.py`
4. Add tests in `tests/`

### Error Handling Pattern

```python
from fastapi import HTTPException

# Validation errors → 400
raise HTTPException(status_code=400, detail="Invalid file type")

# Size limits → 413
raise HTTPException(status_code=413, detail="File too large")

# Conversion failures → 500
raise HTTPException(status_code=500, detail=f"Conversion failed: {error}")
```

### Configuration Pattern

All settings via environment variables with Pydantic:
```python
from app.config import get_settings

settings = get_settings()
print(settings.max_file_size_mb)  # From MAX_FILE_SIZE_MB env var
```

## Testing Guidelines

- **Unit tests:** Test converter classes in isolation (mock subprocess calls)
- **Integration tests:** Test API endpoints with httpx AsyncClient
- **Use fixtures:** Common test files in `tests/fixtures/`
- **Async tests:** Use `@pytest.mark.asyncio` decorator

```python
@pytest.mark.asyncio
async def test_convert_endpoint(client: AsyncClient):
    response = await client.post(
        "/api/v1/convert/pptx-to-image",
        files={"file": ("test.pptx", pptx_content, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
    )
    assert response.status_code == 200
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | development | Environment mode |
| `MAX_WORKERS` | 3 | Concurrent conversion workers |
| `MAX_FILE_SIZE_MB` | 100 | Maximum upload size |
| `IMAGE_DPI` | 200 | Output image resolution |
| `IMAGE_FORMAT` | JPEG | Output format (JPEG/PNG) |
| `JPEG_QUALITY` | 90 | JPEG compression quality |
| `JOB_TIMEOUT_SECONDS` | 300 | Max conversion time |
| `UPLOAD_DIR` | ./uploads | Output directory |

## Important Files

| File | Purpose |
|------|---------|
| `docs/PRD.md` | Product requirements and user stories |
| `docs/design/PPTX_TO_IMAGE_DESIGN.md` | Technical architecture details |
| `app/services/converter.py` | Core conversion logic |
| `app/services/job_manager.py` | Job queue and state management |
| `app/api/v1/endpoints/convert.py` | API endpoint definitions |

## Troubleshooting

### LibreOffice Issues
- Ensure headless mode: `soffice --headless --version`
- Check font packages are installed
- Verify temp directory permissions

### Memory Issues
- Reduce `MAX_WORKERS` if OOM errors occur
- LibreOffice uses ~200-500MB per instance
- Consider file size limits

### Docker Issues
- Ensure sufficient memory allocated (4GB recommended)
- Check volume mounts for uploads directory
- Verify health check passes: `curl localhost:8000/health`

## Git Workflow

- Branch naming: `feature/`, `fix/`, `docs/`
- Commit messages: Conventional commits style
- PR required for main branch
- Tests must pass before merge
