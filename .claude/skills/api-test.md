# /api-test - Test API Endpoints

Manually test the Media Converter API endpoints with sample requests.

## Instructions

1. **Check if service is running:**
   ```bash
   curl -s http://localhost:8000/health
   ```
   - If not running, inform user to run `/run` first

2. **Run health check:**
   ```bash
   curl -s http://localhost:8000/health | python -m json.tool
   ```

3. **Test conversion endpoint (if test file available):**
   - Look for sample PPTX files in `tests/fixtures/`
   - If no test files exist, inform user

   ```bash
   # Find a test file
   TEST_FILE=$(find tests/fixtures -name "*.pptx" -o -name "*.ppt" | head -1)

   if [ -n "$TEST_FILE" ]; then
     curl -X POST http://localhost:8000/api/v1/convert/pptx-to-image \
       -F "file=@$TEST_FILE" | python -m json.tool
   fi
   ```

4. **Test async mode:**
   ```bash
   # Submit job
   RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/convert/pptx-to-image?wait=false" \
     -F "file=@$TEST_FILE")

   JOB_ID=$(echo $RESPONSE | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

   # Poll status
   curl -s "http://localhost:8000/api/v1/convert/status/$JOB_ID" | python -m json.tool
   ```

5. **Show API documentation link:**
   - Interactive docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Arguments

- `--health`: Only run health check
- `--async`: Test async conversion mode
- `--file <path>`: Use specific file for testing

## Expected Responses

### Health Check (200 OK)
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "libreoffice_available": true,
  "poppler_available": true
}
```

### Conversion Success (200 OK)
```json
{
  "job_id": "uuid",
  "status": "completed",
  "total_slides": 5,
  "images": ["/uploads/pptx-to-image/uuid/slide_001.jpg", ...]
}
```
