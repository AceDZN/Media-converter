# /run - Run the Service

Start the Media Converter service using Docker Compose or directly with uvicorn.

## Instructions

### Docker Mode (Recommended)

1. **Check prerequisites:**
   - Verify `docker-compose.yml` exists
   - Check if image is built (build if needed)

2. **Start the service:**
   ```bash
   docker-compose up -d
   ```

3. **Wait for health check:**
   ```bash
   # Wait a few seconds for startup
   sleep 5
   curl -s http://localhost:8000/health | python -m json.tool
   ```

4. **Show access information:**
   - API endpoint: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

### Local Development Mode

1. **Check dependencies:**
   - Python 3.11+ installed
   - LibreOffice installed (`soffice --version`)
   - Poppler installed (`pdftoppm -v`)

2. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run with auto-reload:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Arguments

- `--local` or `-l`: Run in local development mode instead of Docker
- `--build` or `-b`: Force rebuild before running

## Common Issues

- **Port 8000 in use:** Stop other services or change port in docker-compose.yml
- **Health check fails:** Check LibreOffice/Poppler availability in container
- **Permission errors:** Ensure uploads directory is writable
