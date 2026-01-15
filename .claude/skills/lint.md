# /lint - Run Linting and Formatting

Check code quality and optionally fix formatting issues.

## Instructions

1. **Install linting tools if needed:**
   ```bash
   pip install ruff mypy 2>/dev/null || echo "Installing linting tools..."
   pip install ruff mypy
   ```

2. **Run linting checks:**

### Ruff (linting)
```bash
ruff check app/ tests/
```

### Ruff (formatting check)
```bash
ruff format --check app/ tests/
```

### MyPy (type checking)
```bash
mypy app/ --ignore-missing-imports
```

3. **If `--fix` argument provided, auto-fix issues:**
```bash
ruff check app/ tests/ --fix
ruff format app/ tests/
```

4. **Report results:**
   - Show count of issues found
   - Group by type (formatting, linting, type errors)
   - Suggest fixes for common issues

## Arguments

- `--fix` or `-f`: Auto-fix formatting and linting issues
- `--type` or `-t`: Run only type checking (mypy)
- `--format` or `-F`: Run only format checking

## Common Issues

- **Import sorting:** Use `ruff check --select I --fix` to fix imports
- **Line length:** Default is 88 chars, configure in pyproject.toml if needed
- **Type stubs missing:** Install types packages (e.g., `types-aiofiles`)
