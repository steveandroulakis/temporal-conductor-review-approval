# Temporal Sample Application — Code Agent Runbook (Python)

**Purpose:** A strict, end‑to‑end checklist and reference to ensure an agent not only writes code, but **runs it live** against a Temporal dev server and validates behavior before finishing.

---

## 0) Golden Rules (Do Not Skip)

* ✅ **You must run the app end‑to‑end, potentially multiple times to cover multiple uses and scenarios**: start the Temporal dev server → start `worker.py` → run `starter.py` → (if applicable) send a **signal** → verify results → cleanly stop the worker.
* ✅ Prefer **`uv run`** for execution and **PID files** for lifecycle control.
* ✅ **Temporal CLI must be installed and verified before starting development**: Check `temporal --version` succeeds. If not installed, see §2.2 for installation instructions. This is REQUIRED, not optional.
* ✅ Fail fast: use timeouts and non‑zero exit codes if anything can't connect or errors.

---

## Migration Scenarios

### Migrating from Netflix Conductor

**If you are migrating a Conductor JSON workflow definition to Temporal**, follow the comprehensive migration guide:

➡️ **See [CONDUCTOR_TO_TEMPORAL.md](./CONDUCTOR_TO_TEMPORAL.md)** for complete migration instructions.

**Quick detection**: You're in a migration scenario if:
- You have a Conductor JSON workflow definition file (`.json`)
- The task is to "migrate", "convert", or "translate" from Conductor to Temporal
- You're working with Conductor task types (SIMPLE, HTTP, FORK_JOIN, SWITCH, etc.)

**Migration approach overview**:
1. **Analyze** the Conductor JSON to understand workflow structure and control flow
2. **Generate** complete Temporal Python project with activities, workflows, worker, and tests
3. **Validate** with syntax checking, type checking (mypy --strict), and unit tests
4. **Execute** end-to-end test against Temporal dev server
5. **Document** with comprehensive setup instructions and Conductor comparison

**Key differences from building from scratch**:
- Start with existing Conductor workflow definition rather than requirements
- Follow structured 10-phase migration process
- Generate comprehensive tests and documentation automatically
- Focus on faithful translation of Conductor logic to Temporal patterns

**The rest of this document (AGENTS.md) applies to both migration and from-scratch scenarios** for general Temporal development practices, execution guidelines, and troubleshooting.

---

## 1) Repository / File Layout (required)

```
_your_app_name_here_/ (or choose an appropriate name)
  shared.py          # dataclasses and shared types
  activities.py      # activity defs only
  workflow.py        # workflow defs only
  worker.py          # long‑running worker (PID + logging)
  starter.py         # workflow starter client (timeouts + exit codes)
tests/
  __init__.py
  test_workflow.py   # automated workflow tests (see §7)
AGENTS.md            # this file
pyproject.toml
```

> **Imports:** Use relative imports inside `_your_app_name_here_` (e.g., `from activities import compose_greeting`). This keeps things executable via `uv run` without extra PYTHONPATH setup.

---

## 2) Prerequisites

### 2.1 UV (Python package/runtime manager)

```bash
uv --version
```

If missing:

* **macOS:** `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
* **Windows:** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
* **Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`

Useful checks:

```bash
uv --version
uv python list
```

### 2.2 Temporal CLI + Dev Server (REQUIRED)

> 🚨 **CRITICAL PREREQUISITE**
>
> The Temporal CLI is **REQUIRED** for all development and testing. You **MUST** install it before proceeding with any code execution. Without it, you cannot run the dev server, execute workflows, or validate your implementation.

**Step 1: Verify Temporal CLI is installed**

Run this command and verify you see a version number:
```bash
temporal --version
```

**Expected output**: `temporal version 1.0.0` (or similar version number)

**If the command fails** (command not found / not recognized):

**You MUST install the Temporal CLI now:**

- **macOS**:
  ```bash
  brew install temporal
  ```

- **Windows amd64**:
  Download and install from: https://temporal.download/cli/archive/latest?platform=windows&arch=amd64

- **Windows arm64**:
  Download and install from: https://temporal.download/cli/archive/latest?platform=windows&arch=arm64

- **Linux amd64**:
  ```bash
  curl -sSf https://temporal.download/cli.sh | sh
  ```
  Or download from: https://temporal.download/cli/archive/latest?platform=linux&arch=amd64

- **Linux arm64**:
  Download and install from: https://temporal.download/cli/archive/latest?platform=linux&arch=arm64

**Step 2: Verify installation succeeded**

After installation, verify the CLI works:
```bash
temporal --version || {
    echo "❌ ERROR: Temporal CLI installation failed"
    echo "Please install manually and verify before proceeding"
    exit 1
}
```

You MUST see a version number. If not, troubleshoot the installation before continuing.

**Step 3: Start/verify dev server is running**

The dev server will be auto-started in Section 4 pre-flight checks, but you can start it manually:

```bash
temporal operator namespace describe default >/dev/null 2>&1 || temporal server start-dev &
```

> 💡 **Note**: The dev server will run in the background. You can view it at http://localhost:8233

---

## 3) Project Setup (new projects)

```bash
uv init _your_app_name_here_
cd _your_app_name_here_
mkdir _your_app_name_here_ # (or choose an appropriate name)
```

**Dependencies**

```bash
uv venv
uv add temporalio
uv add --dev ruff mypy pytest pytest-asyncio

# CRITICAL: Sync all dependencies including dev extras
uv sync --all-extras

# Verify all packages installed
uv pip list
```

### Setup Virtual Environment and Dependencies
```bash
# Create local virtual environment (recommended)
uv venv

# Activate environment (optional - uv run handles this automatically)
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate     # Windows

# Install core Temporal dependencies
uv add temporalio

# Add development dependencies
uv add --dev pytest pytest-asyncio ruff mypy

# Sync all dependencies including dev extras
uv sync --all-extras

# Verify installation
uv pip list
```

**Recommended `pyproject.toml` setup**

```toml
[project]
name = "_your_app_name_here_"
version = "0.1.0"
description = "Temporal workflow sample application"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "temporalio>=1.7.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "pytest-asyncio>=0.21.0", "ruff>=0.1.0", "mypy>=1.0.0"]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
```

---

## 4) End‑to‑End Execution (MANDATORY)

> Follow these exact steps. Do not stop after static checks or imports.

### 4.0 Pre-flight: Verify Prerequisites

**CRITICAL**: Before running any code, verify all prerequisites are met:

**Step 1: Verify Temporal CLI is installed**

```bash
# Check if Temporal CLI is available
temporal --version || {
    echo "❌ ERROR: Temporal CLI is not installed"
    echo "📖 Installation is REQUIRED to proceed"
    echo "👉 See Section 2.2 for installation instructions:"
    echo "   - macOS: brew install temporal"
    echo "   - Linux: curl -sSf https://temporal.download/cli.sh | sh"
    echo "   - Windows: Download from https://temporal.download/cli/archive/latest"
    exit 1
}

echo "✓ Temporal CLI is installed: $(temporal --version)"
```

**Step 2: Ensure all dependencies are synced**

```bash
# Sync all dependencies including dev extras
uv sync --all-extras

# Verify critical packages are present
uv pip list | grep -E "(temporalio|pytest)" || {
    echo "❌ ERROR: Required dependencies missing"
    echo "Run: uv sync --all-extras"
    exit 1
}

echo "✓ Dependencies synced"
```

**Step 3: Auto-start Temporal dev server if not running**

```bash
# Check if dev server is already running
if temporal operator namespace describe default >/dev/null 2>&1; then
    echo "✓ Temporal dev server is already running"
else
    echo "⚠️  Temporal dev server not running - starting it now..."
    temporal server start-dev &
    sleep 5

    # Verify it started successfully
    if temporal operator namespace describe default >/dev/null 2>&1; then
        echo "✓ Temporal dev server started successfully"
        echo "📊 Web UI available at: http://localhost:8233"
    else
        echo "❌ ERROR: Failed to start Temporal dev server"
        exit 1
    fi
fi
```

### 4.1 Start the Worker

```bash
# ENSURE THE TEMPORAL SERVICE IS RUNNING FIRST
# ENSURE NO WORKER IS CURRENTLY RUNNING ALREADY, IF SO: KILL THE OLD ONE
cd _your_app_name_here_ # or your app name
uv run worker.py > worker.log 2>&1 &
WORKER_PID=$!; echo $WORKER_PID > worker.pid
sleep 3
ps -p $WORKER_PID > /dev/null || { echo "ERROR: Worker failed to start"; exit 1; }
```

> The worker must log a ready message (e.g., “Worker started … polling …”). Check `worker.log` if unsure.

### 4.2 Run the Workflow Starter (note: workflows may take many seconds to run, or may wait for input e.g. signals, or hang due to bugs)

```bash
# Example invocation; customize argument as needed
uv run starter.py "CodeAgent"
```

**Expected:** the starter prints `Result: Hello, CodeAgent!` and exits with code 0.

### 4.3 Validate Execution with Temporal CLI
**NOTE:** You can ALWAYS validate your executions and behavior of workflows by using these commands.

After the starter completes, verify the workflow execution history using the Temporal CLI.

**List recent workflows:**

```bash
temporal workflow list --namespace default --output json
```

This command shows all recent workflow executions. Look for your workflow ID (e.g., `hello-activity-workflow-CodeAgent`) and confirm its status is `WORKFLOW_EXECUTION_STATUS_COMPLETED`.

**Show specific workflow history:**

```bash
# Replace the workflow ID with the one from your run
temporal workflow show --workflow-id "hello-activity-workflow-CodeAgent"
```

This command provides a detailed event history for the specified workflow, confirming that all steps (e.g., `ActivityTaskCompleted`) executed as expected.

### 4.4 (If applicable to the use case) Send a Signal, Then Verify

To make signaling testable, add a signal to your workflow (see §6). Once added, either:

* **Python client snippet** (preferred during dev):

  ```bash
  uv run - <<'PY'
  import asyncio, sys
  from temporalio.client import Client
  async def main():
      client = await Client.connect("localhost:7233")
      handle = client.get_workflow_handle("hello-activity-workflow-CodeAgent")
      await handle.signal("update_greeting", "Howdy")
      print("Signal sent")
  asyncio.run(main())
  PY
  ```
* Or execute another workflow that exercises the signaled behavior.

Then **query** or run another execution to verify the changed behavior (see §6 for a query example).

### 4.5 Gather results
You should collect the results of your executions ready to give them to me. So I know what you ran succeeded.

### 4.6 Cleanly Stop the Worker

```bash
kill $(cat worker.pid)
wait $(cat worker.pid) 2>/dev/null || true
rm -f worker.pid
```

> **Success criteria:** server reachable, worker stayed alive and polled, starter completed, CLI validation passed, optional signal processed, worker shut down cleanly.

---

## 5) One‑Command E2E Script (copy/paste)

```bash
#!/usr/bin/env bash
set -euo pipefail
cd _your_app_name_here_ # or your app name

# Check if Temporal CLI is installed
if ! command -v temporal &> /dev/null; then
    echo "❌ ERROR: Temporal CLI is not installed"
    echo "📖 Installation is REQUIRED to proceed"
    echo "👉 See Section 2.2 for installation instructions:"
    echo "   - macOS: brew install temporal"
    echo "   - Linux: curl -sSf https://temporal.download/cli.sh | sh"
    echo "   - Windows: Download from https://temporal.download/cli/archive/latest"
    exit 1
fi

echo "✓ Temporal CLI is installed: $(temporal --version)"

# Start Temporal dev server if not running
if ! temporal operator namespace describe default >/dev/null 2>&1; then
  echo "⚠️  Starting Temporal dev server..."
  temporal server start-dev &
  sleep 5
  echo "✓ Temporal dev server started"
fi

echo "Starting worker..."
uv run worker.py > worker.log 2>&1 &
WORKER_PID=$!; echo $WORKER_PID > worker.pid
sleep 3
ps -p $WORKER_PID >/dev/null || { echo "Worker failed to start"; tail -n 200 worker.log; exit 1; }

echo "Running starter..."
uv run starter.py "CodeAgent"

echo "Validating workflow execution..."
# Give the server a moment to register the completion
sleep 2
temporal workflow show --workflow-id "hello-activity-workflow-CodeAgent"
# Check for completion status in the list view
if ! temporal workflow list --query "WorkflowId = 'hello-activity-workflow-CodeAgent'" | grep -q "COMPLETED"; then
    echo "Validation failed: Workflow did not complete successfully."
    temporal workflow show --workflow-id "hello-activity-workflow-CodeAgent" --output json | tail -n 200
    exit 1
fi
echo "Validation successful."

# Optional signal block (requires §6 changes to workflow)
# python - <<'PY'
# import asyncio
# from temporalio.client import Client
# async def main():
#   c = await Client.connect("localhost:7233")
#   h = c.get_workflow_handle("hello-activity-workflow-CodeAgent")
#   await h.signal("update_greeting", "Howdy")
#   print("Signal sent")
# asyncio.run(main())
# PY

echo "Shutting down worker..."
kill "$WORKER_PID"
wait "$WORKER_PID" 2>/dev/null || true
rm -f worker.pid

echo "E2E: OK"
```

---

## 6) Reference Code (minimal; add signals/queries for live validation)

### 6.1 `shared.py`

```python
from dataclasses import dataclass

@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str
```

### 6.2 `activities.py`

```python
from temporalio import activity
from shared import ComposeGreetingInput

@activity.defn
def compose_greeting(input: ComposeGreetingInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    return f"{input.greeting}, {input.name}!"
```

### 6.3 `workflow.py` (with **signal** + **query**)

> ⚠️ **WORKFLOW SANDBOX WARNING**
>
> **Import Pattern**: This example imports a specific activity function (`from activities import compose_greeting`), which is CORRECT.
>
> **DO NOT** import the entire activities module (`from . import activities` or `import activities`) if your activities.py contains non-deterministic imports like httpx, random, or I/O libraries. Doing so will violate the workflow sandbox.
>
> **Safe pattern**: Import specific functions by name
> **Unsafe pattern**: Import entire module when it has non-deterministic dependencies

```python
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy  # NOTE: Import from .common, NOT .workflow
from activities import compose_greeting  # Import specific function, not entire module
from shared import ComposeGreetingInput

@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self._greeting = "Hello"

    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running workflow with parameter %s" % name)
        default_retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=100),
            maximum_attempts=0,
        )
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput(self._greeting, name),
            schedule_to_close_timeout=timedelta(seconds=20),
            retry_policy=default_retry_policy,
        )

    @workflow.signal
    def update_greeting(self, new_greeting: str) -> None:
        self._greeting = new_greeting

    @workflow.query
    def current_greeting(self) -> str:
        return self._greeting
```

### 6.4 `worker.py`

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["temporalio>=1.7.0"]
# ///
import asyncio, logging, os
from concurrent.futures import ThreadPoolExecutor
from temporalio.client import Client
from temporalio.worker import Worker
from activities import compose_greeting
from workflow import GreetingWorkflow

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    with open("worker.pid", "w") as f:
        f.write(str(os.getpid()))
    logger.info("Worker starting")
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="hello-activity-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        activity_executor=ThreadPoolExecutor(5),
    ):
        logger.info("Worker ready — polling: hello-activity-task-queue")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Worker shutting down…")

if __name__ == "__main__":
    asyncio.run(main())
```

### 6.5 `starter.py`

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["temporalio>=1.7.0"]
# ///
import asyncio, logging, sys
from temporalio.client import Client
from workflow import GreetingWorkflow

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    try:
        client = await Client.connect("localhost:7233")
        logger.info(f"Starting workflow for name: {name}")
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            name,
            id=f"hello-activity-workflow-{name}",
            task_queue="hello-activity-task-queue",
        )
        print(f"Result: {result}")
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

**Validate signal & query (after a run):**

```bash
# Send a signal to update greeting
python - <<'PY'
import asyncio
from temporalio.client import Client
async def main():
  c = await Client.connect("localhost:7233")
  h = c.get_workflow_handle("hello-activity-workflow-CodeAgent")
  await h.signal("update_greeting", "Howdy")
  print("Signal sent")
asyncio.run(main())
PY

# Query current greeting
python - <<'PY'
import asyncio
from temporalio.client import Client
async def main():
  c = await Client.connect("localhost:7233")
  h = c.get_workflow_handle("hello-activity-workflow-CodeAgent")
  print(await h.query("current_greeting"))
asyncio.run(main())
PY
```

---

## 7) Testing Workflows

> 🎯 **Core Principle**: Focus on **integration tests** that run real workflows with mock activities. This approach is the most effective way to find critical bugs in workflow logic.

### Why Write Tests?

The end-to-end execution from Section 4 validates that your workflow *can* run, but automated tests ensure:
- **Workflow logic** (branching, loops, error handling) works correctly
- **State management** (signals, queries) behaves as expected
- **Edge cases** are handled properly
- **Regression prevention** when making changes

### 7.1 The Time-Skipping Test Environment

**Problem**: Workflows often wait (using `workflow.sleep`, `workflow.wait_condition`, or timers). If your test runs in real-time, it will hang or timeout.

**Solution**: Use `WorkflowEnvironment.start_time_skipping()` to fast-forward time. Workflows that should run for days complete in seconds.

```python
from temporalio.testing import WorkflowEnvironment

async def test_my_workflow():
    # This environment fast-forwards all workflow-level time
    env = await WorkflowEnvironment.start_time_skipping()
    # ... your test logic ...
    await env.shutdown()
```

> ⚠️ **Common Mistake**: Do NOT use `async with await` on `start_time_skipping()`. See §9.1 for the correct pattern.

### 7.2 Mock Your Activities

**Problem**: If you use real activities, tests might fail due to external issues (network, databases) unrelated to workflow logic.

**Solution**: Create mock implementations of your activities. Simply make a function with the same name and signature, decorate with `@activity.defn`, and pass to the `Worker`.

```python
from temporalio import activity

# Your real activity (in activities.py)
@activity.defn(name="upload_schema")
async def upload_schema(input: SchemaInput) -> UploadResult:
    # Real implementation that hits external API
    ...

# Mock for testing (in test_workflow.py)
@activity.defn(name="upload_schema")
async def upload_schema_mock(input: SchemaInput) -> UploadResult:
    # Return fake result instantly
    return UploadResult(success=True, message="Mocked upload")
```

### 7.3 Configure Pytest for Module Imports

**Problem**: `ModuleNotFoundError` when running tests - pytest can't find your workflow module.

**Solution**: Add `pythonpath` to your `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = [
    ".",
]
```

### 7.4 Complete Test Example

Here's a full integration test following best practices:

**File: `tests/test_greeting_workflow.py`**

```python
import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from workflow import GreetingWorkflow
from shared import ComposeGreetingInput

# Mock activity
@activity.defn(name="compose_greeting")
async def compose_greeting_mock(input: ComposeGreetingInput) -> str:
    # Return predictable result for testing
    return f"{input.greeting}, {input.name}!"

@pytest.mark.asyncio
async def test_greeting_workflow_basic():
    """Test basic workflow execution with default greeting"""
    # Create time-skipping environment
    env = await WorkflowEnvironment.start_time_skipping()

    try:
        # Start worker with workflow and mock activities
        async with Worker(
            env.client,
            task_queue="test-task-queue",
            workflows=[GreetingWorkflow],
            activities=[compose_greeting_mock],
        ):
            # Execute workflow
            result = await env.client.execute_workflow(
                GreetingWorkflow.run,
                "TestUser",
                id="test-workflow-basic",
                task_queue="test-task-queue",
            )

            # Assert expected result
            assert result == "Hello, TestUser!"
    finally:
        await env.shutdown()

@pytest.mark.asyncio
async def test_greeting_workflow_with_signal():
    """Test workflow signal updates greeting"""
    env = await WorkflowEnvironment.start_time_skipping()

    try:
        async with Worker(
            env.client,
            task_queue="test-task-queue",
            workflows=[GreetingWorkflow],
            activities=[compose_greeting_mock],
        ):
            # Start workflow without waiting for completion
            handle = await env.client.start_workflow(
                GreetingWorkflow.run,
                "TestUser",
                id="test-workflow-signal",
                task_queue="test-task-queue",
            )

            # Send signal to update greeting
            await handle.signal("update_greeting", "Howdy")

            # Query current greeting
            current = await handle.query("current_greeting")
            assert current == "Howdy"

            # Complete workflow
            result = await handle.result()
            assert result == "Howdy, TestUser!"
    finally:
        await env.shutdown()
```

### 7.5 Running Tests

```bash
# Ensure dependencies are synced
uv sync --all-extras

# Run all tests with verbose output
uv run pytest -v

# Run specific test
uv run pytest tests/test_greeting_workflow.py::test_greeting_workflow_basic -v

# Run with coverage
uv run pytest --cov=your_app_name --cov-report=html
```

### 7.6 Test File Layout

Add a `tests/` directory to your project:

```
_your_app_name_here_/
  shared.py
  activities.py
  workflow.py
  worker.py
  starter.py
tests/
  __init__.py
  test_workflow.py
  test_activities.py (optional - for activity unit tests)
AGENTS.md
pyproject.toml
```

### 7.7 What to Test

**Essential tests for every workflow:**
1. **Happy path**: Basic execution with expected inputs
2. **Signal handling**: If workflow uses signals, test state changes
3. **Query handling**: If workflow exposes queries, verify responses
4. **Error handling**: Test how workflow handles activity failures
5. **Edge cases**: Empty inputs, boundary conditions, etc.

**Example test checklist for a review approval workflow:**
- ✅ Workflow completes when approved
- ✅ Workflow waits correctly for approval signal
- ✅ Workflow handles rejection signal
- ✅ Workflow times out after configured duration
- ✅ Query returns correct approval status

### 7.8 Common Testing Pitfalls

See **Section 9.1** for detailed solutions to common issues:
- **Wrong Test Environment Pattern** (using `async with await` incorrectly)
- **Workflow Sandbox Violations** (importing activities module incorrectly)
- **Test Dependencies Missing** (forgetting `uv sync --all-extras`)

---

## 8) Development Loop

1. **Stop existing worker**

   ```bash
   [ -f worker.pid ] && kill $(cat worker.pid) || true
   rm -f worker.pid
   pkill -f "worker.py" || true
   ```
2. **Start fresh worker**

   ```bash
   uv run worker.py &
   echo $! > worker.pid
   sleep 3
   ps -p $(cat worker.pid) >/dev/null || { echo "Worker failed"; exit 1; }
   ```
3. **Run starter + verify output**

   ```bash
   uv run starter.py "TestUpdatedCode"
   ```
4. **Clean up**

   ```bash
   kill $(cat worker.pid); wait $(cat worker.pid) 2>/dev/null || true; rm -f worker.pid
   ```

---

## 9) Troubleshooting Quick Hits

* **Worker won’t connect:** ensure dev server at `localhost:7233` is up.
* **Dependency woes:** `uv pip check`, `uv sync --reinstall`, `uv lock --upgrade`.
* **CI:** use `uv sync --frozen` for reproducible installs; cache UV downloads.
* **Unclear how to use SDK features or best practices** check out and examine https://github.com/temporalio/samples-python.git
* **You want to intentionally fail the workflow (e.g. a business specific exception)**: Raise a Temporal failure, typically ApplicationError. Any exception that is an instance of temporalio.exceptions.FailureError (e.g., ApplicationError) fails the Workflow Execution immediately. Non-Temporal exceptions (e.g. unexpected bugs) suspend instead of failing. Inside your workflow code: `raise ApplicationError("Customer lives outside the service area")`
* **Workflow Hangs:**
- REASON 1 (worker isn't running): check `worker.log`; confirm PID is alive and polling. List workflows using the Temporal CLI to be sure it's still running.
- REASON 2 (workflow task failed due to workflow code bug): 
NOTE: By default, a non-Temporal exception in a Python Workflow (e.g. a bug) fails the “workflow task” and suspends the Workflow in a retrying state. It keeps retrying until you deploy a code fix; it does not mark the Workflow Execution as failed. You will see the exception in the worker. You can `temporal workflow show...` to see the progress of the workflow so far. This workflow task failed behavior is intended to let you fix bad code (e.g., NPE, type errors) without losing in-flight workflows (SDK Python README – Exceptions). Identify and fix the offending code, then redeploy/restart the Worker; the Workflow will resume from its last progress point once the task is retried with the corrected code.
- REASON 3 (workflow waiting for something): await workflow.wait_condition will pause until the condition(s) are met. Workflows can pause forever waiting for e.g. a signal or some other input. Similarly, workflow timers like await asyncio.sleep allow a workflow to wait until the timer fires. This 'hung' workflow might not be an issue per se, but part of the happy-path business process.

---

## 9.1) Common Development Pitfalls (Documented from Real Issues)

These critical issues have been encountered in actual development and have proven solutions:

### Issue: Test Dependencies Missing
**Symptom**: `ModuleNotFoundError: No module named 'temporalio'` or `pytest-asyncio` errors

**Fix**:
```bash
uv sync --all-extras
uv pip list | grep -E "(temporalio|pytest|pytest-asyncio)"
```

**Prevention**: Always run `uv sync --all-extras` before executing code or tests

---

### Issue: Workflow Sandbox Violation (CRITICAL)
**Symptom**: `RuntimeError: Failed validating workflow` at worker startup

**Cause**: Importing activities module that has non-deterministic dependencies (httpx, boto3, I/O libraries)

**Wrong**:
```python
from . import activities  # ❌ Imports ALL module dependencies
```

**Correct**:
```python
from .activities import activity1, activity2  # ✓ Imports only functions
```

**Detection**:
```bash
python3 -c "from your_package.workflow import YourWorkflow"
```

**Why**: The workflow sandbox requires deterministic code. When you import an entire module, all its imports (including httpx, random, etc.) are loaded, violating sandbox rules.

---

### Issue: Wrong Test Environment Pattern
**Symptom**: `TypeError: 'coroutine' object does not support the asynchronous context manager protocol`

**Wrong**:
```python
async with await WorkflowEnvironment.start_time_skipping() as env:  # ❌
```

**Correct**:
```python
env = await WorkflowEnvironment.start_time_skipping()  # ✓
async with Worker(env.client, ...):
    result = await env.client.execute_workflow(...)
```

---

### Issue: Wrong RetryPolicy Import
**Symptom**: `AttributeError: module 'temporalio.workflow' has no attribute 'RetryPolicy'`

**Wrong**:
```python
from temporalio import workflow
retry_policy = workflow.RetryPolicy(...)  # ❌
```

**Correct**:
```python
from temporalio.common import RetryPolicy  # ✓
```

---

### Quick Diagnostic Commands

Run these in order when troubleshooting:

1. **Dependencies**: `uv pip list | grep -E "(temporalio|pytest)"`
2. **Syntax**: `python3 -m py_compile your_package/*.py`
3. **Sandbox**: `python3 -c 'from your_package.workflow import YourWorkflow'`
4. **Imports**: `grep "from temporalio.common import RetryPolicy" your_package/workflow.py`
5. **Worker**: Check `worker.log` for startup errors
6. **Tests**: `uv run pytest -v`

---

## 10) Success Checklist (agent must confirm)

* [ ] Temporal dev server reachable on `localhost:7233`.
* [ ] Worker started, wrote `worker.pid`, and is polling the task queue.
* [ ] Starter completed and printed the expected result.
* [ ] (If applicable) Signal sent and verified via query or follow‑up run.
* [ ] Worker shutdown was clean and PID file removed.

> Only mark complete if you executed every step above.
