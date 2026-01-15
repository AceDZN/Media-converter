# /add-converter - Add a New File Converter

Scaffold a new file converter module following the project's established patterns.

## Instructions

1. **Gather requirements:**
   Ask the user:
   - What input format? (e.g., DOCX, XLSX, PDF)
   - What output format? (e.g., PDF, Images, Text)
   - Any special requirements?

2. **Create the service class:**

   Create `app/services/{format}_converter.py`:
   ```python
   import logging
   from pathlib import Path
   from typing import List
   from dataclasses import dataclass

   from app.config import get_settings

   logger = logging.getLogger(__name__)


   @dataclass
   class ConversionResult:
       success: bool
       output_files: List[str]
       error: str = None


   class {Format}Converter:
       """
       Converts {INPUT} files to {OUTPUT}.
       """

       def __init__(self):
           self.settings = get_settings()
           self._validate_dependencies()

       def _validate_dependencies(self) -> None:
           # Check required system binaries
           pass

       def convert(self, input_path: str, job_id: str) -> ConversionResult:
           # Implementation
           pass


   # Module-level function for ProcessPoolExecutor
   def convert_{format}_sync(input_path: str, job_id: str) -> ConversionResult:
       converter = {Format}Converter()
       return converter.convert(input_path, job_id)
   ```

3. **Create the API endpoint:**

   Add to `app/api/v1/endpoints/convert.py` or create new file:
   ```python
   @router.post("/{input}-to-{output}")
   async def convert_{input}_to_{output}(
       file: UploadFile = File(...),
       wait: bool = Query(default=True),
       settings: Settings = Depends(get_settings_dep),
       job_manager: JobManager = Depends(get_job_manager_dep)
   ):
       # Follow existing endpoint pattern
       pass
   ```

4. **Add schema models:**

   Update `app/models/schemas.py` if needed with new response models.

5. **Create tests:**

   Create `tests/test_{format}_converter.py`:
   ```python
   import pytest
   from app.services.{format}_converter import {Format}Converter

   class Test{Format}Converter:
       def test_convert_valid_file(self):
           pass

       def test_convert_invalid_file(self):
           pass
   ```

6. **Update configuration:**
   - Add new settings to `app/config.py` if needed
   - Update `.env.example` with new variables

7. **Update documentation:**
   - Add endpoint to CLAUDE.md
   - Update API reference in design docs

## Files to Create/Modify

- `app/services/{format}_converter.py` (new)
- `app/api/v1/endpoints/convert.py` (modify)
- `app/models/schemas.py` (modify if needed)
- `app/config.py` (modify if needed)
- `tests/test_{format}_converter.py` (new)
