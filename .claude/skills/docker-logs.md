# /docker-logs - View Service Logs

View and analyze logs from the Media Converter Docker container.

## Instructions

1. **Check if container is running:**
   ```bash
   docker-compose ps
   ```

2. **View logs based on arguments:**

### Default: Last 100 lines
```bash
docker-compose logs --tail=100 media-converter
```

### Follow logs in real-time
```bash
docker-compose logs -f media-converter
```

### Logs from specific time
```bash
docker-compose logs --since="1h" media-converter
```

### All logs
```bash
docker-compose logs media-converter
```

3. **Filter for specific patterns:**
   ```bash
   docker-compose logs media-converter 2>&1 | grep -i "error\|exception\|failed"
   ```

4. **Analyze common issues:**
   - Look for LibreOffice errors
   - Check for memory issues (OOM)
   - Identify conversion timeouts
   - Find failed job IDs

## Arguments

- `--follow` or `-f`: Follow log output in real-time
- `--tail <n>`: Show last n lines (default 100)
- `--since <time>`: Show logs since timestamp (e.g., "1h", "30m", "2024-01-15")
- `--errors`: Filter for error messages only
- `--job <id>`: Filter logs for specific job ID

## Log Patterns to Watch

| Pattern | Meaning |
|---------|---------|
| `Job .* submitted` | New conversion started |
| `Job .* completed` | Conversion finished successfully |
| `Job .* failed` | Conversion failed |
| `LibreOffice conversion failed` | PPTX to PDF stage failed |
| `PDF to image conversion failed` | PDF to images stage failed |
| `timed out` | Process exceeded timeout |
| `OOM` or `Killed` | Memory exhaustion |
