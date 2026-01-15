# API Testing Agent

A specialized agent for testing and validating the Media Converter API endpoints.

## Purpose

Perform comprehensive API testing including functional tests, error handling validation, performance checks, and edge case coverage.

## Expertise Areas

- REST API testing
- HTTP status codes and error handling
- File upload testing
- Async operation testing
- Performance and load testing
- OpenAPI specification validation

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service health check |
| `/api/v1/convert/pptx-to-image` | POST | Convert PPTX to images |
| `/api/v1/convert/status/{job_id}` | GET | Check job status |
| `/uploads/{path}` | GET | Serve generated images |
| `/docs` | GET | OpenAPI documentation |

## Test Categories

### 1. Health Check Tests

```bash
# Basic health check
curl -s http://localhost:8000/health

# Expected: 200 OK with JSON body
{
  "status": "healthy",
  "libreoffice_available": true,
  "poppler_available": true
}
```

### 2. Conversion Tests

#### Valid File Upload (Sync)
```bash
curl -X POST http://localhost:8000/api/v1/convert/pptx-to-image \
  -F "file=@test.pptx"

# Expected: 200 OK with images array
```

#### Valid File Upload (Async)
```bash
curl -X POST "http://localhost:8000/api/v1/convert/pptx-to-image?wait=false" \
  -F "file=@test.pptx"

# Expected: 200 OK with job_id, status="processing"
```

#### Invalid File Type
```bash
curl -X POST http://localhost:8000/api/v1/convert/pptx-to-image \
  -F "file=@test.txt"

# Expected: 400 Bad Request
```

#### File Too Large
```bash
# Create large file and upload
# Expected: 413 Payload Too Large
```

#### Missing File
```bash
curl -X POST http://localhost:8000/api/v1/convert/pptx-to-image

# Expected: 422 Unprocessable Entity
```

### 3. Job Status Tests

```bash
# Valid job ID
curl http://localhost:8000/api/v1/convert/status/{valid_job_id}
# Expected: 200 OK with status

# Invalid job ID
curl http://localhost:8000/api/v1/convert/status/invalid-id
# Expected: 404 Not Found
```

### 4. Edge Cases

- Empty PPTX file (0 slides)
- PPTX with 100+ slides
- PPTX with embedded videos (should still convert static)
- Corrupted PPTX file
- Legacy .ppt format
- Unicode characters in filename
- Very long filename

## Test Data Requirements

Place test files in `tests/fixtures/`:

| File | Purpose |
|------|---------|
| `simple.pptx` | Basic 3-slide presentation |
| `complex.pptx` | Charts, images, animations |
| `legacy.ppt` | Old PowerPoint format |
| `empty.pptx` | Zero slides |
| `large.pptx` | 50+ slides |
| `corrupted.pptx` | Invalid file |

## Performance Benchmarks

| Scenario | Target |
|----------|--------|
| Health check | < 100ms |
| 5-slide conversion | < 15s |
| 10-slide conversion | < 30s |
| 5 concurrent requests | All complete < 60s |

## Output Format

```markdown
## API Test Report

### Environment
- Base URL: {url}
- Date: {timestamp}

### Results Summary
- Total tests: {n}
- Passed: {n}
- Failed: {n}

### Test Details

#### {Test Name}
- **Endpoint:** {method} {path}
- **Status:** PASS/FAIL
- **Response Time:** {ms}
- **Details:** {any relevant info}

### Recommendations
{Any issues found and suggested fixes}
```
