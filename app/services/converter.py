"""PPTX to Image converter service using LibreOffice and Poppler."""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

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
    error: Optional[str] = None


class PptxConverter:
    """
    Handles PPTX/PPT to Image conversion using LibreOffice and Poppler.

    Conversion Pipeline:
    1. PPTX/PPT -> PDF (via LibreOffice headless)
    2. PDF -> Images (via Poppler/pdf2image)
    """

    def __init__(self):
        self.settings = get_settings()

    def _validate_dependencies(self) -> tuple[bool, bool]:
        """
        Verify that required system binaries are available.

        Returns:
            Tuple of (libreoffice_available, poppler_available)
        """
        lo_available = False
        poppler_available = False

        # Check LibreOffice
        try:
            result = subprocess.run(
                ["soffice", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                lo_available = True
                logger.debug(f"LibreOffice version: {result.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("LibreOffice not available")

        # Check Poppler (pdftoppm)
        try:
            result = subprocess.run(
                ["pdftoppm", "-v"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # pdftoppm outputs version to stderr
            poppler_available = True
            logger.debug(f"Poppler available: {result.stderr.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Poppler not available")

        return lo_available, poppler_available

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
                error=f"Input file not found: {input_path}",
            )

        # Create output directory
        output_dir = Path(self.settings.upload_dir) / "pptx-to-image" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Stage 1: Convert PPTX to PDF
            logger.info(f"Job {job_id}: Converting {input_path.name} to PDF...")
            pdf_path = self._convert_to_pdf(input_path, output_dir)

            # Stage 2: Convert PDF to Images
            logger.info(f"Job {job_id}: Converting PDF to images...")
            images = self._convert_pdf_to_images(pdf_path, output_dir)

            # Clean up intermediate PDF
            pdf_path.unlink(missing_ok=True)

            logger.info(f"Job {job_id}: Successfully created {len(images)} images")
            return ConversionResult(
                success=True,
                images=images,
                slide_count=len(images),
                error=None,
            )

        except ConversionError as e:
            logger.error(f"Job {job_id}: Conversion failed - {e}")
            return ConversionResult(
                success=False,
                images=[],
                slide_count=0,
                error=str(e),
            )
        except Exception as e:
            logger.exception(f"Job {job_id}: Unexpected error")
            return ConversionResult(
                success=False,
                images=[],
                slide_count=0,
                error=f"Unexpected error: {e}",
            )

    def _convert_to_pdf(self, input_path: Path, output_dir: Path) -> Path:
        """
        Convert PPTX/PPT to PDF using LibreOffice.

        Args:
            input_path: Path to input file
            output_dir: Directory for output PDF

        Returns:
            Path to generated PDF file

        Raises:
            ConversionError: If conversion fails
        """
        # LibreOffice command for headless PDF conversion
        cmd = [
            "soffice",
            "--headless",
            "--invisible",
            "--nologo",
            "--nofirststartwizard",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(input_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.settings.job_timeout_seconds,
                cwd=str(output_dir),
            )

            if result.returncode != 0:
                raise ConversionError(f"LibreOffice conversion failed: {result.stderr}")

            # LibreOffice creates PDF with same base name
            pdf_path = output_dir / f"{input_path.stem}.pdf"

            if not pdf_path.exists():
                raise ConversionError(
                    f"PDF not created. LibreOffice output: {result.stdout} {result.stderr}"
                )

            logger.debug(f"PDF created: {pdf_path}")
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
            List of image file paths (relative URLs)

        Raises:
            ConversionError: If conversion fails
        """
        try:
            # Convert PDF to PIL Images
            images = convert_from_path(
                pdf_path,
                dpi=self.settings.image_dpi,
                fmt=self.settings.image_format.lower(),
                thread_count=2,
                use_pdftocairo=True,
            )

            image_paths = []

            for idx, image in enumerate(images, start=1):
                # Generate filename: slide_001.jpg, slide_002.jpg, etc.
                ext = self.settings.image_format.lower()
                if ext == "jpeg":
                    ext = "jpg"
                filename = f"slide_{idx:03d}.{ext}"
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
                relative_path = filepath.relative_to(self.settings.upload_dir)
                image_paths.append(f"/uploads/{relative_path}")

                logger.debug(f"Saved slide {idx}: {filepath}")

            return image_paths

        except PDFInfoNotInstalledError:
            raise ConversionError("Poppler (pdfinfo) not installed")
        except PDFPageCountError:
            raise ConversionError("Could not determine PDF page count - file may be corrupted")
        except Exception as e:
            raise ConversionError(f"PDF to image conversion failed: {e}")


def convert_pptx_sync(input_path: str, job_id: str) -> ConversionResult:
    """
    Synchronous conversion function for use with ProcessPoolExecutor.

    This function is defined at module level to be picklable.

    Args:
        input_path: Path to the input PPTX/PPT file
        job_id: Unique job identifier

    Returns:
        ConversionResult with success status and image paths
    """
    converter = PptxConverter()
    return converter.convert(input_path, job_id)


class PdfConverter:
    """
    Handles PDF to Image conversion using Poppler.

    Conversion Pipeline:
    PDF -> Images (via Poppler/pdf2image)
    """

    def __init__(self):
        self.settings = get_settings()

    def convert(self, input_path: str, job_id: str) -> ConversionResult:
        """
        Convert a PDF file to images.

        This is a SYNCHRONOUS method designed to run in a ProcessPoolExecutor.

        Args:
            input_path: Path to the input PDF file
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
                error=f"Input file not found: {input_path}",
            )

        # Create output directory
        output_dir = Path(self.settings.upload_dir) / "pdf-to-image" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Job {job_id}: Converting PDF to images...")
            images = self._convert_pdf_to_images(input_path, output_dir)

            logger.info(f"Job {job_id}: Successfully created {len(images)} images")
            return ConversionResult(
                success=True,
                images=images,
                slide_count=len(images),
                error=None,
            )

        except ConversionError as e:
            logger.error(f"Job {job_id}: Conversion failed - {e}")
            return ConversionResult(
                success=False,
                images=[],
                slide_count=0,
                error=str(e),
            )
        except Exception as e:
            logger.exception(f"Job {job_id}: Unexpected error")
            return ConversionResult(
                success=False,
                images=[],
                slide_count=0,
                error=f"Unexpected error: {e}",
            )

    def _convert_pdf_to_images(self, pdf_path: Path, output_dir: Path) -> List[str]:
        """
        Convert PDF pages to images using Poppler.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for output images

        Returns:
            List of image file paths (relative URLs)

        Raises:
            ConversionError: If conversion fails
        """
        try:
            # Convert PDF to PIL Images
            images = convert_from_path(
                pdf_path,
                dpi=self.settings.image_dpi,
                fmt=self.settings.image_format.lower(),
                thread_count=2,
                use_pdftocairo=True,
            )

            image_paths = []

            for idx, image in enumerate(images, start=1):
                # Generate filename: page_001.jpg, page_002.jpg, etc.
                ext = self.settings.image_format.lower()
                if ext == "jpeg":
                    ext = "jpg"
                filename = f"page_{idx:03d}.{ext}"
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
                relative_path = filepath.relative_to(self.settings.upload_dir)
                image_paths.append(f"/uploads/{relative_path}")

                logger.debug(f"Saved page {idx}: {filepath}")

            return image_paths

        except PDFInfoNotInstalledError:
            raise ConversionError("Poppler (pdfinfo) not installed")
        except PDFPageCountError:
            raise ConversionError("Could not determine PDF page count - file may be corrupted")
        except Exception as e:
            raise ConversionError(f"PDF to image conversion failed: {e}")


def convert_pdf_sync(input_path: str, job_id: str) -> ConversionResult:
    """
    Synchronous PDF conversion function for use with ProcessPoolExecutor.

    This function is defined at module level to be picklable.

    Args:
        input_path: Path to the input PDF file
        job_id: Unique job identifier

    Returns:
        ConversionResult with success status and image paths
    """
    converter = PdfConverter()
    return converter.convert(input_path, job_id)
