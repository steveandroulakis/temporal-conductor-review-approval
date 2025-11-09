# Temporal Sample Application — Code Agent Runbook (Python)

**Purpose:** A strict, end‑to‑end checklist and reference to ensure an agent not only writes code, but **runs it live** against a Temporal dev server and validates behavior before finishing.

---

## 0) Golden Rules (Do Not Skip)

* ✅ **You must run the app end‑to‑end, potentially multiple times to cover multiple uses and scenarios**: start the Temporal dev server → start `worker.py` → run `starter.py` → (if applicable) send a **signal** → verify results → cleanly stop the worker.
* ✅ Prefer **`uv run`** for execution and **PID files** for lifecycle control.
* ✅ Fail fast: use timeouts and non‑zero exit codes if anything can’t connect or errors.

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
AGENTS.md            # this file
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

### 2.2 Temporal CLI + Dev Server

Check if available.
```bash
temporal --version
```

If not installed:
- **Mac**: `brew install temporal`
- **Windows amd64**: https://temporal.download/cli/archive/latest?platform=windows&arch=amd64
- **Windows arm64**: https://temporal.download/cli/archive/latest?platform=windows&arch=arm64
- **Linux amd64**: https://temporal.download/cli/archive/latest?platform=linux&arch=amd64
- **Linux arm64**: https://temporal.download/cli/archive/latest?platform=linux&arch=arm64

**Start/verify dev server is running:**

```bash
temporal operator namespace describe default >/dev/null 2>&1 || temporal server start-dev &
```

> Keep this running in a separate terminal while developing.

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
uv add temporalio --dev ruff mypy pytest
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
uv add --dev pytest ruff mypy

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
dev = ["pytest>=7.0.0", "ruff>=0.1.0", "mypy>=1.0.0"]

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

### 4.1 Start/ensure Temporal dev server is running

```bash
temporal operator namespace describe default >/dev/null 2>&1 || temporal server start-dev &
```

### 4.2 Start the Worker

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

### 4.3 Run the Workflow Starter (note: workflows may take many seconds to run, or may wait for input e.g. signals, or hang due to bugs)

```bash
# Example invocation; customize argument as needed
uv run starter.py "CodeAgent"
```

**Expected:** the starter prints `Result: Hello, CodeAgent!` and exits with code 0.

### 4.4 Validate Execution with Temporal CLI
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

### 4.5 (If applicable to the use case) Send a Signal, Then Verify

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

### 4.6 Gather results
You should collect the results of your executions ready to give them to me. So I know what you ran succeeded.

### 4.7 Cleanly Stop the Worker

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

if ! temporal operator namespace describe default >/dev/null 2>&1; then
  echo "Starting Temporal dev server..."
  temporal server start-dev &
  sleep 5
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

```python
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from activities import compose_greeting
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

## 7) Development Loop

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

## 8) Troubleshooting Quick Hits

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

## 9) Success Checklist (agent must confirm)

* [ ] Temporal dev server reachable on `localhost:7233`.
* [ ] Worker started, wrote `worker.pid`, and is polling the task queue.
* [ ] Starter completed and printed the expected result.
* [ ] (If applicable) Signal sent and verified via query or follow‑up run.
* [ ] Worker shutdown was clean and PID file removed.

> Only mark complete if you executed every step above.
