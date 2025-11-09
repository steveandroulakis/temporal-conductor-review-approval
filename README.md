# Schema Approval Workflow

This project translates the Conductor `review_approval` workflow into a Temporal Python implementation.

## Project Layout

```
schema_approval/
  __init__.py
  activities.py
  shared.py
  starter.py
  worker.py
  workflow.py
tests/
  test_activities.py
  test_workflow.py
pyproject.toml
```

## Development Tasks

1. Install dependencies with [uv](https://docs.astral.sh/uv/):
   ```bash
   uv sync --all-extras
   ```
2. Run static checks:
   ```bash
   uv run python -m py_compile schema_approval/*.py
   uv run mypy schema_approval --strict
   ```
3. Execute tests:
   ```bash
   uv run pytest -v
   ```

## End-to-End Execution

1. Start the Temporal development server:
   ```bash
   temporal server start-dev
   ```
2. In another terminal, run the worker module:
   ```bash
   uv run python -m schema_approval.worker
   ```
3. Launch the workflow starter module:
   ```bash
   uv run python -m schema_approval.starter
   ```

The starter prints the final approval report along with the full iteration history.
