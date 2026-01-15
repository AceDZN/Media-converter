# Media Converter

A self-hosted media transformation service that converts files between formats without relying on third-party paid APIs.

## Features

- **PPTX to Image Conversion** - Convert PowerPoint presentations to high-quality images (JPEG/PNG)
- **REST API** - Simple API for easy integration
- **Async Support** - Both synchronous and asynchronous conversion modes
- **Docker Ready** - Single command deployment with all dependencies included
- **No External APIs** - All processing done locally using LibreOffice and Poppler

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/AceDZN/Media-converter.git
cd Media-converter

# Start the service
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Local Development

**Prerequisites:**
- Python 3.11+
- LibreOffice (`apt install libreoffice`)
- Poppler (`apt install poppler-utils`)

```bash
# Clone the repository
git clone https://github.com/AceDZN/Media-converter.git
cd Media-converter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Usage

### Convert PPTX to Images

```bash
# Synchronous (wait for result)
curl -X POST http://localhost:8000/api/v1/convert/pptx-to-image \
  -F "file=@presentation.pptx"

# Asynchronous (get job ID, poll for status)
curl -X POST "http://localhost:8000/api/v1/convert/pptx-to-image?wait=false" \
  -F "file=@presentation.pptx"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Successfully converted 5 slides",
  "total_slides": 5,
  "images": [
    "/uploads/pptx-to-image/550e8400.../slide_001.jpg",
    "/uploads/pptx-to-image/550e8400.../slide_002.jpg"
  ],
  "processing_time_ms": 3450
}
```

### Check Job Status

```bash
curl http://localhost:8000/api/v1/convert/status/{job_id}
```

### Health Check

```bash
curl http://localhost:8000/health
```

## API Documentation

Interactive API documentation is available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Configuration

Configure via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | development | Environment mode |
| `MAX_WORKERS` | 3 | Concurrent conversion workers |
| `MAX_FILE_SIZE_MB` | 100 | Maximum upload size |
| `IMAGE_DPI` | 200 | Output image resolution |
| `IMAGE_FORMAT` | JPEG | Output format (JPEG/PNG) |
| `JPEG_QUALITY` | 90 | JPEG compression quality |
| `JOB_TIMEOUT_SECONDS` | 300 | Max conversion time |

Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

## Project Structure

```
Media-converter/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── api/v1/endpoints/    # API endpoints
│   ├── services/            # Business logic
│   │   ├── converter.py     # PPTX conversion
│   │   └── job_manager.py   # Job queue management
│   └── models/              # Pydantic schemas
├── tests/                   # Test suite
├── docs/                    # Documentation
│   ├── PRD.md              # Product requirements
│   └── design/             # Technical designs
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Development

### Run Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Linting

```bash
ruff check app/ tests/
ruff format app/ tests/
```

### Build Docker Image

```bash
docker build -t media-converter:latest .
```

## Tech Stack

- **FastAPI** - Web framework
- **LibreOffice** - PPTX/PPT to PDF conversion
- **Poppler** - PDF to image conversion
- **ProcessPoolExecutor** - Concurrent processing

## License

MIT
