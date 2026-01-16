"""Converter service tests."""

import pytest

from app.config import get_settings
from app.services.converter import ConversionResult, PptxConverter


class TestPptxConverter:
    """Tests for PptxConverter class."""

    def test_converter_initialization(self):
        """Test converter initializes with settings."""
        converter = PptxConverter()
        assert converter.settings is not None
        assert converter.settings.image_dpi > 0

    def test_validate_dependencies(self):
        """Test dependency validation returns tuple."""
        converter = PptxConverter()
        lo_available, poppler_available = converter._validate_dependencies()
        assert isinstance(lo_available, bool)
        assert isinstance(poppler_available, bool)

    def test_convert_missing_file(self):
        """Test conversion fails gracefully for missing file."""
        converter = PptxConverter()
        result = converter.convert("/nonexistent/file.pptx", "test-job-id")

        assert isinstance(result, ConversionResult)
        assert result.success is False
        assert result.slide_count == 0
        assert "not found" in result.error.lower()

    def test_conversion_result_dataclass(self):
        """Test ConversionResult dataclass structure."""
        result = ConversionResult(
            success=True,
            images=["/uploads/test/slide_001.jpg"],
            slide_count=1,
            error=None,
        )

        assert result.success is True
        assert len(result.images) == 1
        assert result.slide_count == 1
        assert result.error is None


class TestSettings:
    """Tests for application settings."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = get_settings()

        assert settings.app_name == "Media Converter"
        assert settings.max_file_size_mb == 100
        assert settings.image_dpi == 200
        assert settings.image_format in ["JPEG", "PNG"]
        assert settings.max_workers >= 1

    def test_allowed_extensions(self):
        """Test allowed file extensions."""
        settings = get_settings()

        assert ".pptx" in settings.allowed_extensions
        assert ".ppt" in settings.allowed_extensions
        assert ".txt" not in settings.allowed_extensions
