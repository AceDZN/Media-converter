# /build - Build Docker Image

Build the Media Converter Docker image with all dependencies (LibreOffice, Poppler, Python packages).

## Instructions

1. **Check for Dockerfile existence:**
   - Verify `Dockerfile` exists in the project root
   - If missing, inform the user and offer to create it from the design document

2. **Build the image:**
   ```bash
   docker build -t media-converter:latest .
   ```

3. **Report build results:**
   - If successful, show the image size and tag
   - If failed, analyze the error and suggest fixes

4. **Optional: Run a quick verification:**
   ```bash
   docker run --rm media-converter:latest python -c "import fastapi; print('FastAPI OK')"
   docker run --rm media-converter:latest soffice --version
   docker run --rm media-converter:latest pdftoppm -v
   ```

## Common Issues

- **Missing Dockerfile:** Create from `docs/design/PPTX_TO_IMAGE_DESIGN.md` section 4.2
- **Build failures:** Check network connectivity for apt-get, pip install
- **Large image size:** Ensure multi-stage build is being used
