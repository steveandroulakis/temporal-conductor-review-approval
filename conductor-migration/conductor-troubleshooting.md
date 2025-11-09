# Conductor to Temporal: Troubleshooting Guide

> **Part of the [Conductor to Temporal Migration Guide](./README.md)**

This document provides solutions to common migration issues, documented pitfalls from real migrations, and guidance for next steps after migration.

---

## Table of Contents

- [Common Migration Issues](#common-migration-issues)
- [Critical Documented Pitfalls](#critical-documented-pitfalls)
- [Quick Diagnostic Checklist](#quick-diagnostic-checklist)
- [Next Steps After Migration](#next-steps-after-migration)
- [Reference: Complete Migration Script](#reference-complete-migration-script)
- [Getting Additional Help](#getting-additional-help)

---

## Common Migration Issues

### Conductor JSON Parsing Errors
**Symptom**: jq fails to parse Conductor file

**Solution**: Validate JSON syntax with `jq empty file.json`, fix any JSON errors

---

### Complex JSONPath Expressions
**Symptom**: Difficulty translating complex JSONPath to Python

**Solution**: Break down into intermediate variables, document complex transformations

**Example**:
```python
# Instead of complex nested access
result = data["response"]["body"]["items"][0]["value"]

# Break it down
response_body = data.get("response", {}).get("body", {})
items = response_body.get("items", [])
value = items[0]["value"] if items else None
```

---

### Nested Control Flow
**Symptom**: Difficult to translate nested FORK_JOIN + SWITCH combinations

**Solution**: Create helper functions, carefully preserve execution order, add detailed comments

**Example**:
```python
# Original nested Conductor: FORK_JOIN -> SWITCH in each branch

# Translated to Temporal with helper function
async def process_approval_branch(workflow_input: WorkflowInput) -> str:
    """Helper for approval processing branch."""
    result = await workflow.execute_activity(check_approval, ...)
    if result.status == "APPROVED":
        return await workflow.execute_activity(send_approval, ...)
    else:
        return await workflow.execute_activity(send_rejection, ...)

# Main workflow uses parallel execution with helper
approval_result, notification_result = await asyncio.gather(
    process_approval_branch(input),
    workflow.execute_activity(send_notification, ...)
)
```

---

### Activity Timeout Issues
**Symptom**: Activities timing out during execution

**Solution**: Increase `start_to_close_timeout`, check activity implementation performance

```python
# For long-running activities, use appropriate timeout
result = await workflow.execute_activity(
    long_running_task,
    args=[data],
    start_to_close_timeout=timedelta(minutes=10),  # Increased from default
    heartbeat_timeout=timedelta(seconds=30)         # Add heartbeat for long tasks
)
```

---

### Type Checking Errors
**Symptom**: mypy strict mode fails

**Solution**: Add explicit type hints, avoid `Any`, use Optional for nullable fields

```python
# ❌ WRONG
def process(data):
    return data["result"]

# ✓ CORRECT
from typing import Dict, Any, Optional

def process(data: Dict[str, Any]) -> Optional[str]:
    return data.get("result")
```

---

### Test Failures
**Symptom**: Unit tests fail after generation

**Solution**: Review test assertions, ensure mock data matches actual behavior, fix activity implementations

---

### Worker Connection Errors
**Symptom**: Worker can't connect to Temporal server

**Solution**: Ensure dev server is running on localhost:7233, unset Temporal environment variables

```bash
# Unset all Temporal environment variables
unset TEMPORAL_CLI_ADDRESS TEMPORAL_CLI_NAMESPACE TEMPORAL_CLI_TLS_CERT \
      TEMPORAL_CLI_TLS_KEY TEMPORAL_CERT_PATH TEMPORAL_KEY_PATH \
      TEMPORAL_NAMESPACE TEMPORAL_ADDRESS TEMPORAL_API_KEY \
      TEMPORAL_HOST_PORT TEMPORAL_TLS_CERT TEMPORAL_TLS_KEY

# Verify Temporal server is running
temporal workflow list --namespace default
```

---

### Workflow Hangs During Execution
**Symptom**: Workflow starts but never completes

**Solution**:
- Check worker.log for errors
- Use `temporal workflow show` to see progress
- Look for bugs in workflow logic (infinite loops, missing signals)
- Check if activities are registered correctly
- For workflows waiting on signals/updates: See [Human Interaction Patterns guide](./conductor-human-interaction.md) for proper implementation

```bash
# Check workflow status
temporal workflow show --workflow-id <workflow_id>

# Check workflow history
temporal workflow show --workflow-id <workflow_id> --output json | jq '.events'

# Check worker logs
tail -f worker.log
```

---

## Critical Documented Pitfalls

These issues were encountered during actual migrations and have specific, tested solutions.

### Issue 1: Test Dependency Not Found

**Symptom**: `ModuleNotFoundError: No module named 'temporalio'` or `ModuleNotFoundError: No module named 'pytest_asyncio'` when running pytest

**Root Cause**: Dev dependencies not fully installed or synced

**Solution**:
```bash
# Always sync all extras after installing dependencies
uv sync --all-extras

# Verify all required packages are present
uv pip list | grep -E "(temporalio|pytest|pytest-asyncio|mypy)"
```

**Prevention**: Always run `uv sync --all-extras` after modifying pyproject.toml or before running tests

**Detection**: Run `uv pip list` and check for all required packages

---

### Issue 2: Workflow Sandbox Violation (CRITICAL)

**Symptom**: `RuntimeError: Failed validating workflow {WorkflowName}` when starting worker or during test execution

**Root Cause**: Workflow imports activity module that contains non-deterministic code (httpx, random, datetime.now(), file I/O, database connections, etc.)

**Example of problematic code**:
```python
# ❌ WRONG - This will fail if activities.py imports httpx
with workflow.unsafe.imports_passed_through():
    from . import activities
```

**Solution**:
```python
# ✓ CORRECT - Import specific activity functions only
with workflow.unsafe.imports_passed_through():
    from .activities import activity1, activity2, activity3
```

**Prevention**:
- NEVER use `from . import activities` when activities.py imports I/O libraries
- ALWAYS import specific activity function names
- Review activities.py imports before importing in workflow.py

**Detection**:
```bash
# This will catch sandbox violations early
python3 -c "import sys; sys.path.insert(0, '.'); from {project_name}.workflow import YourWorkflow; print('Sandbox OK')"
```

**Why this happens**: The Temporal workflow sandbox enforces deterministic execution. When you import an activity module that contains non-deterministic code (like httpx), those imports are evaluated at module load time and violate the sandbox rules, even if you're not using that code in the workflow.

---

### Issue 3: Incorrect Test Environment API

**Symptom**: `TypeError: 'coroutine' object does not support the asynchronous context manager protocol` or `AttributeError: '_EphemeralServerWorkflowEnvironment' object has no attribute 'create_worker'`

**Root Cause**: Using incorrect pattern for WorkflowEnvironment API

**Example of problematic code**:
```python
# ❌ WRONG - This syntax is incorrect
async with await WorkflowEnvironment.start_time_skipping() as env:
    async with Worker(env.client, ...):
        ...
```

**Solution**:
```python
# ✓ CORRECT - Await first, then use the environment
env = await WorkflowEnvironment.start_time_skipping()
async with Worker(env.client, task_queue="test-queue", workflows=[...], activities=[...]):
    result = await env.client.execute_workflow(...)
```

**Prevention**: Always follow the two-step pattern: await environment creation, then create worker with env.client

**Detection**: Run `uv run pytest test_workflow.py -v` - will fail immediately with TypeError if using wrong pattern

---

### Issue 4: Wrong RetryPolicy Import

**Symptom**: `AttributeError: module 'temporalio.workflow' has no attribute 'RetryPolicy'`

**Root Cause**: Importing RetryPolicy from wrong module

**Example of problematic code**:
```python
# ❌ WRONG
from temporalio import workflow
retry_policy = workflow.RetryPolicy(...)  # RetryPolicy doesn't exist in workflow module
```

**Solution**:
```python
# ✓ CORRECT
from temporalio.common import RetryPolicy

# Then use it in workflow
retry_policy = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0
)
```

**Prevention**: Always import RetryPolicy from `temporalio.common`, NOT from `temporalio.workflow`

**Detection**: Syntax check will catch this:
```bash
python3 -m py_compile {project_name}/workflow.py
```

---

## Quick Diagnostic Checklist

If your migration is failing, check these in order:

1. ✓ **Dependencies installed**: `uv pip list | grep -E "(temporalio|pytest|pytest-asyncio)"`
2. ✓ **Syntax valid**: `python3 -m py_compile {project_name}/*.py`
3. ✓ **Sandbox compliance**: `python3 -c 'from {project_name}.workflow import YourWorkflow'`
4. ✓ **Correct imports**: `grep "from temporalio.common import RetryPolicy" {project_name}/workflow.py`
5. ✓ **Test pattern**: `grep "env = await WorkflowEnvironment.start_time_skipping()" {project_name}/test_workflow.py`
6. ✓ **Worker starts**: `uv run worker.py` (should not crash on startup)
7. ✓ **Tests pass**: `uv run pytest -v`

---

## Next Steps After Migration

### 1. Customize Activity Implementations
- Replace placeholder logic with actual business logic
- Add error handling
- Configure appropriate timeouts

**Example**:
```python
@activity.defn
async def fetch_user_data(user_id: str) -> Dict[str, Any]:
    """Fetch user data from external API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.example.com/users/{user_id}",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        activity.logger.error(f"HTTP error fetching user {user_id}: {e}")
        raise
    except httpx.RequestError as e:
        activity.logger.error(f"Request failed for user {user_id}: {e}")
        raise
```

---

### 2. Enhance Input Validation
- Add input validation in WorkflowInput dataclass
- Implement custom validators

**Example**:
```python
from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class WorkflowInput:
    """Input parameters for the workflow."""
    email: str
    amount: float

    def __post_init__(self):
        """Validate inputs after initialization."""
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", self.email):
            raise ValueError(f"Invalid email format: {self.email}")

        # Validate amount
        if self.amount <= 0:
            raise ValueError(f"Amount must be positive: {self.amount}")
```

---

### 3. Production Readiness
- Configure production Temporal server connection
- Set up monitoring and observability
- Add metrics and logging
- Configure deployment (Docker, Kubernetes, etc.)

**Example production worker configuration**:
```python
# worker.py - Production configuration
client = await Client.connect(
    os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
    namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
    tls=TLSConfig(
        client_cert=load_cert(os.environ["TEMPORAL_TLS_CERT"]),
        client_private_key=load_key(os.environ["TEMPORAL_TLS_KEY"])
    ) if os.environ.get("TEMPORAL_TLS_CERT") else False
)
```

---

### 4. Optimize Performance
- Tune activity timeouts
- Configure retry policies based on failure patterns
- Add caching where appropriate

**Example optimized retry policy**:
```python
# Different retry strategies for different activity types

# Fast-failing for validation activities
validation_retry = RetryPolicy(
    maximum_attempts=2,
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=5),
    backoff_coefficient=2.0
)

# Persistent for external API calls
api_retry = RetryPolicy(
    maximum_attempts=10,
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(minutes=5),
    backoff_coefficient=2.0
)
```

---

### 5. Extend Testing
- Add more edge case tests
- Add performance tests
- Add chaos engineering tests

**Example edge case test**:
```python
@pytest.mark.asyncio
async def test_workflow_with_empty_input():
    """Test workflow handles empty input gracefully."""
    env = await WorkflowEnvironment.start_time_skipping()
    async with Worker(env.client, task_queue="test", workflows=[MyWorkflow], activities=[...]):
        with pytest.raises(ValueError, match="Input cannot be empty"):
            await env.client.execute_workflow(
                MyWorkflow.run,
                WorkflowInput(data=""),
                id="test-empty",
                task_queue="test"
            )
```

---

## Reference: Complete Migration Script

For automated migration, use this one-command script template:

```bash
#!/usr/bin/env bash
set -euo pipefail

CONDUCTOR_FILE="$1"
PROJECT_NAME="${2:-$(basename "$CONDUCTOR_FILE" .json | tr '[:upper:]' '[:lower:]' | tr ' ' '_')}"

echo "Migrating Conductor workflow to Temporal Python..."
echo "Conductor file: $CONDUCTOR_FILE"
echo "Project name: $PROJECT_NAME"

# Phase 1: Analyze
echo "Phase 1: Analyzing Conductor JSON..."
jq empty "$CONDUCTOR_FILE" || { echo "Invalid JSON"; exit 1; }

# Extract workflow name
WORKFLOW_NAME=$(jq -r '.name' "$CONDUCTOR_FILE")
echo "Workflow name: $WORKFLOW_NAME"

# Create analysis file
cat > conductor-analysis.json <<EOF
{
  "analysis_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "conductor_file": "$CONDUCTOR_FILE",
  "workflow_metadata": {
    "name": "$WORKFLOW_NAME",
    "version": $(jq '.version // 1' "$CONDUCTOR_FILE"),
    "description": $(jq '.description // ""' "$CONDUCTOR_FILE")
  },
  "project_config": {
    "project_name": "$PROJECT_NAME",
    "task_queue": "${PROJECT_NAME}-task-queue"
  }
}
EOF

echo "✓ Analysis complete: conductor-analysis.json"

# Phase 2-10: Execute migration phases
# [Implementation based on detailed phase instructions in migration guide]

echo ""
echo "Migration complete! Project created at: $PROJECT_NAME"
echo ""
echo "Next steps:"
echo "1. cd $PROJECT_NAME"
echo "2. ./setup.sh"
echo "3. temporal server start-dev  # In separate terminal"
echo "4. uv run worker.py            # In separate terminal"
echo "5. uv run starter.py"
```

**Note**: This is a template. See the [Migration Guide](./conductor-migration-guide.md) for detailed implementation of each phase.

---

## Getting Additional Help

### Documentation Resources
- **[Migration Guide](./conductor-migration-guide.md)**: Detailed phase-by-phase instructions
- **[Architecture Guide](./conductor-architecture.md)**: Conductor vs Temporal concepts
- **[Quality Assurance](./conductor-quality-assurance.md)**: Testing and validation standards
- **Temporal Documentation**: https://docs.temporal.io/
- **Temporal Python SDK**: https://github.com/temporalio/sdk-python
- **Temporal Samples**: https://github.com/temporalio/samples-python
- **Conductor Documentation**: https://conductor.netflix.com/

### Community Support
- **Temporal Community Slack**: https://temporal.io/slack
- **Temporal Community Forum**: https://community.temporal.io/
- **Stack Overflow**: Tag questions with `temporalio` and `python`

### Professional Support
- **Temporal Cloud Support**: For Temporal Cloud customers
- **Enterprise Support**: Contact Temporal for enterprise support options

### Debugging Tips

1. **Enable Debug Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Use Temporal CLI for Workflow Inspection**
   ```bash
   # Show workflow execution details
   temporal workflow show --workflow-id <id>

   # Show workflow history (all events)
   temporal workflow show --workflow-id <id> --output json | jq '.events'

   # Describe workflow execution
   temporal workflow describe --workflow-id <id>
   ```

3. **Check Worker Health**
   ```bash
   # View worker logs
   tail -f worker.log

   # Check if worker is running
   ps aux | grep worker.py

   # Check worker process
   cat worker.pid
   ps -p $(cat worker.pid)
   ```

4. **Validate Workflow Registration**
   ```python
   # In Python REPL
   from {project_name}.workflow import MyWorkflow
   print(MyWorkflow.run)  # Should show workflow.run method
   ```

---

**[← Back to Main Guide](./README.md)**
