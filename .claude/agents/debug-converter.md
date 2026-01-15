# Conversion Debug Agent

A specialized agent for debugging file conversion issues in the Media Converter service.

## Purpose

Diagnose and resolve issues with the PPTX-to-Image conversion pipeline, including LibreOffice failures, Poppler errors, and job management problems.

## Expertise Areas

- LibreOffice headless mode troubleshooting
- Poppler/pdf2image debugging
- File format validation
- Process timeout analysis
- Memory and resource issues
- Log analysis

## Conversion Pipeline

```
Input PPTX/PPT
     │
     ▼
┌─────────────────┐
│   Validation    │ ← Check file exists, extension valid
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LibreOffice    │ ← PPTX → PDF conversion
│   (headless)    │   Command: soffice --headless --convert-to pdf
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Poppler      │ ← PDF → Images conversion
│  (pdf2image)    │   Uses: pdftocairo or pdftoppm
└────────┬────────┘
         │
         ▼
Output Images
```

## Debug Checklist

### 1. Pre-Conversion Checks

```bash
# Verify LibreOffice
soffice --headless --version

# Verify Poppler
pdftoppm -v
pdftocairo -v

# Check available fonts
fc-list | head -20

# Check disk space
df -h /app/uploads
```

### 2. LibreOffice Issues

| Symptom | Possible Cause | Debug Steps |
|---------|----------------|-------------|
| Hangs indefinitely | Font rendering issue | Check font packages |
| Returns empty PDF | Corrupted input | Validate PPTX structure |
| Permission denied | User permissions | Check file ownership |
| "Display not set" | Missing Xvfb | Ensure `--headless` flag |

**Manual LibreOffice Test:**
```bash
soffice --headless --invisible --convert-to pdf --outdir /tmp /path/to/test.pptx
ls -la /tmp/*.pdf
```

### 3. Poppler Issues

| Symptom | Possible Cause | Debug Steps |
|---------|----------------|-------------|
| "Syntax Error" | Corrupted PDF | Validate PDF with `pdfinfo` |
| Low quality output | DPI setting | Increase DPI value |
| Missing text | Font embedding | Check PDF font list |
| Timeout | Large file | Increase timeout or reduce DPI |

**Manual Poppler Test:**
```bash
pdfinfo /path/to/converted.pdf
pdftoppm -jpeg -r 200 /path/to/converted.pdf /tmp/slide
ls -la /tmp/slide*.jpg
```

### 4. Job Manager Issues

| Symptom | Possible Cause | Debug Steps |
|---------|----------------|-------------|
| Job stuck in "processing" | Worker crashed | Check worker processes |
| Job not found | Expired/cleaned up | Check job TTL settings |
| Multiple jobs fail | Resource exhaustion | Check memory/CPU usage |

**Check Worker Status:**
```python
from app.services.job_manager import get_job_manager

manager = get_job_manager()
print(f"Active jobs: {len(manager._jobs)}")
print(f"Executor workers: {manager._executor._max_workers}")
```

### 5. Memory Issues

```bash
# Check container memory
docker stats media-converter

# Check process memory
ps aux | grep -E "soffice|python"

# Check for OOM kills
dmesg | grep -i "killed process"
```

## Common Fixes

### LibreOffice Hangs
```bash
# Kill stuck processes
pkill -9 soffice

# Clear LibreOffice profile
rm -rf ~/.config/libreoffice
```

### Font Issues
```bash
# Install comprehensive font packages
apt-get install fonts-liberation fonts-dejavu fonts-freefont-ttf fonts-noto

# Rebuild font cache
fc-cache -fv
```

### Permission Issues
```bash
# Fix upload directory permissions
chmod 755 /app/uploads
chown -R appuser:appuser /app/uploads
```

## Log Analysis

**Key log patterns:**

```bash
# Find conversion errors
grep -i "ConversionError" /var/log/media-converter.log

# Find timeout issues
grep -i "timed out" /var/log/media-converter.log

# Find specific job
grep "job_id_here" /var/log/media-converter.log
```

## Output Format

```markdown
## Debug Report: {issue_description}

### Environment
- Container: {running/stopped}
- LibreOffice: {version/status}
- Poppler: {version/status}
- Memory: {available/used}

### Issue Analysis
{Description of what was found}

### Root Cause
{Identified cause}

### Resolution
{Steps taken or recommended}

### Prevention
{How to prevent recurrence}
```
