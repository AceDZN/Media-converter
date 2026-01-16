"""FastAPI application entry point."""

import logging
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.v1.endpoints import convert
from app.config import get_settings
from app.models.schemas import HealthResponse
from app.services.job_manager import get_job_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{__version__}...")

    # Initialize job manager (creates process pool lazily)
    get_job_manager()

    # Create and mount uploads directory
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

    logger.info(f"Server ready. Upload directory: {upload_path.absolute()}")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down...")
    job_manager = get_job_manager()
    job_manager.shutdown()
    logger.info("Shutdown complete")


# Create FastAPI application
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Self-hosted media conversion service. Convert PPTX presentations to images and more.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Check service health and dependency availability.

    Returns the service status and whether LibreOffice and Poppler are available.
    """
    lo_available = False
    poppler_available = False

    # Check LibreOffice
    try:
        result = subprocess.run(
            ["soffice", "--version"],
            capture_output=True,
            timeout=5,
        )
        lo_available = result.returncode == 0
    except Exception:
        pass

    # Check Poppler
    try:
        result = subprocess.run(
            ["pdftoppm", "-v"],
            capture_output=True,
            timeout=5,
        )
        poppler_available = True  # pdftoppm returns non-zero but works
    except Exception:
        pass

    status = "healthy" if (lo_available and poppler_available) else "degraded"

    return HealthResponse(
        status=status,
        version=__version__,
        libreoffice_available=lo_available,
        poppler_available=poppler_available,
    )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/test.html", tags=["System"], include_in_schema=False)
async def test_page():
    """Serve the test HTML page."""
    # Try multiple locations (local dev vs Docker)
    possible_paths = [
        Path(__file__).parent.parent / "test.html",  # Local: repo root
        Path("/app/test.html"),  # Docker: mounted volume
    ]
    for test_file in possible_paths:
        if test_file.exists():
            return FileResponse(test_file, media_type="text/html")
    return {"error": "Test page not found"}


# Include API routers
app.include_router(
    convert.router,
    prefix="/api/v1/convert",
    tags=["Conversion"],
)
