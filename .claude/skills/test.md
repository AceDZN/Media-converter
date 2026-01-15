# /test - Run Tests

Execute the test suite for the Media Converter service.

## Instructions

1. **Check test dependencies:**
   ```bash
   pip install -r requirements-dev.txt 2>/dev/null || pip install pytest pytest-asyncio httpx pytest-cov
   ```

2. **Run the appropriate tests based on arguments:**

### Default: Run all tests
```bash
pytest tests/ -v
```

### With coverage report
```bash
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html
```

### Unit tests only
```bash
pytest tests/test_converter.py -v
```

### API tests only
```bash
pytest tests/test_api.py -v
```

### Specific test
```bash
pytest tests/test_converter.py::test_convert_pptx -v
```

3. **Report results:**
   - Show pass/fail summary
   - If failures, show the failing test details
   - If coverage requested, show coverage percentage

## Arguments

- `--coverage` or `-c`: Include coverage report
- `--unit` or `-u`: Run only unit tests
- `--api` or `-a`: Run only API integration tests
- `--verbose` or `-v`: Extra verbose output
- `<test_name>`: Run specific test by name

## Common Issues

- **Missing test fixtures:** Check `tests/fixtures/` directory
- **Import errors:** Ensure PYTHONPATH includes project root
- **Async test failures:** Verify `pytest-asyncio` is installed
