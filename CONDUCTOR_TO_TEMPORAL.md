# Netflix Conductor to Temporal Python Migration Guide

## Introduction

This guide provides comprehensive instructions for migrating Netflix Conductor JSON workflow definitions to production-ready Temporal Python projects.

**Use this guide when:**
- You have a Conductor JSON workflow definition file
- You want to migrate from Conductor's declarative JSON DSL to Temporal's code-first Python approach
- You need a complete, tested, and documented Temporal project as output

**What this migration produces:**
- Complete Python project with workflows, activities, and worker
- Comprehensive unit and integration tests
- Type-safe code with mypy strict validation
- Full documentation and setup instructions
- End-to-end validated working implementation

---

## Quick Start (TL;DR)

For experienced users who understand both Conductor and Temporal:

1. **Ensure prerequisites**: Python 3.11+, Temporal CLI, UV, jq
2. **Validate Conductor JSON**: `jq empty workflow.json`
3. **Follow migration phases**: Analyze → Generate → Validate → Test
4. **Key mappings**: SIMPLE→Activity, FORK_JOIN→asyncio.gather, SWITCH→if/elif, DO_WHILE→while
5. **Run end-to-end**: Start dev server → Start worker → Execute workflow → Validate
6. **Success criteria**: All tests pass, mypy strict passes, workflow executes successfully

For detailed instructions, continue reading.

---

## Conductor vs Temporal: Architectural Concepts

### Core Architectural Shift

| Aspect | Conductor | Temporal |
|--------|-----------|----------|
| **Definition Style** | Declarative JSON DSL | Imperative Python code |
| **Workflow Location** | JSON file separate from code | Code decorated with @workflow.defn |
| **State Management** | External metadata store | Event sourcing (automatic) |
| **Execution Model** | Workers poll for tasks | Workers execute activities and workflows |
| **Data Passing** | JSONPath expressions | Native Python objects |
| **Control Flow** | JSON task types | Native Python constructs |

### Task Type Mappings

| Conductor Task Type | Temporal Equivalent | Python Implementation |
|---------------------|---------------------|----------------------|
| **SIMPLE** | Activity | `@activity.defn` function |
| **HTTP** | HTTP Activity | `@activity.defn` with httpx |
| **SET_VARIABLE** | Variable Assignment | Direct Python variable assignment |
| **WAIT** | Signal + Wait Condition | `@workflow.signal` + `workflow.wait_condition()` |
| **INLINE** | Inline Python | Direct Python code in workflow |
| **SUB_WORKFLOW** | Child Workflow | `workflow.execute_child_workflow()` |
| **FORK_JOIN** + **JOIN** | Parallel Execution | `asyncio.gather()` |
| **DO_WHILE** | While Loop | Python `while` loop |
| **SWITCH** | Conditional Logic | Python `if/elif/else` |
| **DYNAMIC_FORK** | Dynamic Parallel | List comprehension + `asyncio.gather()` |

### Control Flow Pattern Translation

#### Sequential Execution
**Conductor:**
```json
{
  "tasks": [
    {"name": "task1", "type": "SIMPLE"},
    {"name": "task2", "type": "SIMPLE"}
  ]
}
```

**Temporal:**
```python
result1 = await workflow.execute_activity(activities.task1, ...)
result2 = await workflow.execute_activity(activities.task2, args=[result1], ...)
```

#### Parallel Execution (FORK_JOIN)
**Conductor:**
```json
{
  "name": "fork_task",
  "type": "FORK_JOIN",
  "forkTasks": [
    [{"name": "task_a", "type": "SIMPLE"}],
    [{"name": "task_b", "type": "SIMPLE"}]
  ]
}
```

**Temporal:**
```python
result_a, result_b = await asyncio.gather(
    workflow.execute_activity(activities.task_a, ...),
    workflow.execute_activity(activities.task_b, ...)
)
```

#### Conditional Logic (SWITCH)
**Conductor:**
```json
{
  "name": "decision",
  "type": "SWITCH",
  "switchCaseValue": "${approval.status}",
  "decisionCases": {
    "APPROVED": [{"name": "proceed", "type": "SIMPLE"}],
    "REJECTED": [{"name": "notify", "type": "SIMPLE"}]
  }
}
```

**Temporal:**
```python
status = approval_result.status
if status == "APPROVED":
    await workflow.execute_activity(activities.proceed, ...)
elif status == "REJECTED":
    await workflow.execute_activity(activities.notify, ...)
```

#### Loops (DO_WHILE)
**Conductor:**
```json
{
  "name": "retry_loop",
  "type": "DO_WHILE",
  "loopCondition": "$.approved == false",
  "loopOver": [{"name": "check_approval", "type": "SIMPLE"}]
}
```

**Temporal:**
```python
approved = False
while not approved:
    result = await workflow.execute_activity(activities.check_approval, ...)
    approved = result.approved
```

### Data Passing Translation

| Conductor Expression | Temporal Python Equivalent |
|----------------------|---------------------------|
| `${workflow.input.field}` | `input.field` |
| `${task_ref.output.field}` | `result_variable.field` |
| `${workflow.variables.var}` | `var` (local variable) |
| `$.some.path` (JSONPath) | `data.some.path` or `data["some"]["path"]` |

---

## Migration Phases Overview

The migration process consists of 10 sequential phases. Each phase builds on the previous one and includes verification steps.

| Phase | Name | Purpose | Key Outputs |
|-------|------|---------|-------------|
| **1** | Analyze Conductor JSON | Parse and understand workflow structure | conductor-analysis.json |
| **2** | Create Project Structure | Set up Python project skeleton | Project directory, pyproject.toml, shared.py |
| **3** | Generate Activities | Translate tasks to activities | activities.py with @activity.defn functions |
| **4** | Generate Workflow | Translate control flow to Python | workflow.py with @workflow.defn class |
| **5** | Generate Worker | Create worker registration | worker.py |
| **6** | Generate Starter | Create workflow execution client | starter.py |
| **7** | Generate Tests | Create unit and integration tests | test_*.py files |
| **8** | Setup and Validation | Install dependencies and validate | All tests pass, mypy passes |
| **9** | End-to-End Test | Run workflow against Temporal | Workflow executes successfully |
| **10** | Documentation | Create comprehensive docs | README.md, comparison docs |

**Estimated Time**: 30-60 minutes depending on workflow complexity

---

## Prerequisites

### Required Tools

1. **Python 3.11+**
   ```bash
   python3 --version | grep -q 'Python 3\\.1[1-9]\\|Python 3\\.[2-9][0-9]'
   ```

2. **UV (Python package manager)**
   ```bash
   # macOS
   brew install uv
   # or
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Temporal CLI**
   ```bash
   # macOS
   brew install temporal

   # Windows/Linux: See https://docs.temporal.io/cli#install
   ```

4. **jq (JSON processor)**
   ```bash
   # macOS
   brew install jq

   # Linux
   apt-get install jq  # or equivalent for your distro
   ```

5. **Valid Conductor JSON workflow file**
   ```bash
   # Validate your Conductor JSON
   jq empty your-workflow.json
   ```

### Optional Tools

- **Temporal dev server** (for Phase 9 end-to-end testing)
  ```bash
  temporal server start-dev
  ```

---

## Generated Project Structure

The migration produces a complete Python project:

```
{project_name}/
  __init__.py              # Package marker
  shared.py                # Dataclasses for workflow/activity I/O
  activities.py            # Activity implementations (@activity.defn)
  workflow.py              # Workflow definition (@workflow.defn)
  worker.py                # Worker registration and execution
  starter.py               # Workflow starter client
  test_workflow.py         # Workflow unit tests (pytest)
  test_activities.py       # Activity unit tests (pytest)
  pyproject.toml           # Dependencies and project metadata
  setup.sh                 # Automated setup script
  README.md                # Setup and usage instructions
  CONDUCTOR_COMPARISON.md  # Side-by-side Conductor vs Temporal examples
  CONDUCTOR_MIGRATION_NOTES.md  # Migration-specific notes
  .gitignore               # Python gitignore
```

### Key Dependencies

- `temporalio>=1.5.0` - Temporal Python SDK
- `httpx>=0.26.0` - HTTP client for HTTP activities
- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `mypy>=1.7.0` - Type checking

---

## Detailed Phase Instructions

<details>
<summary><strong>Phase 1: Analyze Conductor JSON</strong></summary>

### Objectives
- Parse the Conductor workflow JSON file
- Extract workflow metadata (name, version, description, inputs, outputs)
- Analyze all tasks and their types
- Map control flow patterns (sequential, parallel, conditional, loops)
- Analyze data flow and dependencies
- Generate structured analysis file

### Tasks

1. **Load Conductor JSON file**
   ```bash
   jq . your-conductor-workflow.json
   ```

2. **Extract workflow metadata**
   - Workflow name and version
   - Input parameters array
   - Output parameters (if defined)
   - Timeout configuration
   - Description

3. **Analyze each task** in the workflow:
   - Task name and type (SIMPLE, HTTP, SWITCH, etc.)
   - Input parameters (including JSONPath expressions)
   - Output parameters
   - Task-specific configuration
   - Dependencies on other tasks

4. **Map control flow patterns**
   - Sequential task chains
   - Parallel execution blocks (FORK_JOIN + JOIN)
   - Conditional branches (SWITCH with decisionCases)
   - Loops (DO_WHILE with loopCondition)
   - Dynamic parallel execution (DYNAMIC_FORK)
   - Sub-workflow calls (SUB_WORKFLOW)

5. **Analyze data flow**
   - Which tasks use workflow inputs
   - Which tasks depend on other task outputs
   - Variable usage and dependencies
   - JSONPath expressions to translate

6. **Generate analysis file**: `conductor-analysis.json`
   ```json
   {
     "analysis_date": "ISO 8601 timestamp",
     "conductor_file": "path/to/conductor.json",
     "workflow_metadata": { ... },
     "project_config": {
       "project_name": "derived_name",
       "project_name_snake": "derived_name",
       "task_queue": "derived-task-queue"
     },
     "tasks": [ ... ],
     "control_flow_patterns": { ... },
     "data_flow": { ... },
     "external_interactions": { ... },
     "translation_notes": [ ... ]
   }
   ```

### Verification
```bash
test -f conductor-analysis.json
jq empty conductor-analysis.json
jq -e '.workflow_metadata.name' conductor-analysis.json
jq -e '.tasks | length > 0' conductor-analysis.json
```

### Common Issues
- **Invalid JSON**: Ensure Conductor file is valid JSON
- **Missing fields**: Some Conductor workflows omit optional fields (handle gracefully)
- **Complex JSONPath**: Document complex expressions for manual review

</details>

<details>
<summary><strong>Phase 2: Create Project Structure</strong></summary>

### Objectives
- Create Python project directory structure
- Generate basic dataclasses for workflow I/O
- Set up pyproject.toml with dependencies
- Create README.md skeleton
- Create .gitignore

### Tasks

1. **Read analysis file**
   ```bash
   jq -r '.project_config.project_name_snake' conductor-analysis.json
   ```

2. **Create project directory**
   ```bash
   mkdir {project_name}
   cd {project_name}
   ```

3. **Create package files**
   - `__init__.py` (package marker, can be empty)
   - `shared.py` with basic dataclasses:
     ```python
     from dataclasses import dataclass
     from typing import Optional, List, Dict, Any

     @dataclass
     class WorkflowInput:
         """Input parameters for the workflow."""
         # Fields based on Conductor input_parameters
         param1: str
         param2: int
         # ... etc

     @dataclass
     class WorkflowOutput:
         """Output from the workflow."""
         # Fields based on Conductor output or final task results
         result: Any
     ```

4. **Create pyproject.toml**
   ```toml
   [project]
   name = "{project_name}"
   version = "0.1.0"
   description = "Temporal workflow migrated from Conductor"
   requires-python = ">=3.11"
   dependencies = [
       "temporalio>=1.5.0",
       "httpx>=0.26.0",
   ]

   [project.optional-dependencies]
   dev = [
       "pytest>=7.4.0",
       "pytest-asyncio>=0.21.0",
       "mypy>=1.7.0",
   ]

   [build-system]
   requires = ["setuptools>=68.0"]
   build-backend = "setuptools.build_meta"
   ```

5. **Create .gitignore**
   ```
   __pycache__/
   *.py[cod]
   *$py.class
   .pytest_cache/
   .mypy_cache/
   *.egg-info/
   dist/
   build/
   .venv/
   venv/
   worker.pid
   worker.log
   ```

6. **Create README.md skeleton**
   ```markdown
   # {Workflow Name} - Temporal Migration

   Migrated from Conductor workflow: `{conductor_file}`

   ## Prerequisites
   - Python 3.11+
   - Temporal dev server

   ## Setup
   See setup instructions below...
   ```

### Verification
```bash
test -d {project_name}
test -f {project_name}/shared.py
test -f {project_name}/pyproject.toml
python3 -m py_compile {project_name}/shared.py
```

</details>

<details>
<summary><strong>Phase 3: Generate Activities</strong></summary>

### Objectives
- Translate Conductor tasks to Temporal activities
- Generate activity functions with proper decorators
- Handle HTTP tasks with httpx
- Create activity input/output dataclasses
- Add comprehensive docstrings

### Tasks

1. **Identify tasks that become activities**
   - SIMPLE tasks → `@activity.defn` functions
   - HTTP tasks → `@activity.defn` with httpx
   - Custom task types → `@activity.defn` functions
   - **Skip these** (handled in workflow logic):
     - INLINE tasks (inline Python code)
     - SET_VARIABLE tasks (variable assignment)
     - WAIT tasks (signals)
     - Control flow tasks (SWITCH, DO_WHILE, FORK_JOIN, JOIN)

2. **Create activities.py**
   ```python
   from dataclasses import dataclass
   from typing import Optional, List, Dict, Any
   import httpx
   from temporalio import activity

   @activity.defn
   async def simple_task_activity(input_param: str) -> Dict[str, Any]:
       """
       Activity migrated from Conductor SIMPLE task: {task_name}

       Args:
           input_param: Description of parameter

       Returns:
           Dict containing task results
       """
       activity.logger.info(f"Running activity with parameter: {input_param}")
       # TODO: Implement actual activity logic
       return {"status": "success", "result": input_param}

   @activity.defn
   async def http_task_activity(uri: str, method: str = "GET",
                                 headers: Optional[Dict[str, str]] = None,
                                 body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
       """
       HTTP activity migrated from Conductor HTTP task: {task_name}

       Args:
           uri: HTTP endpoint URL
           method: HTTP method (GET, POST, etc.)
           headers: Optional HTTP headers
           body: Optional request body

       Returns:
           Dict containing HTTP response
       """
       activity.logger.info(f"{method} {uri}")
       async with httpx.AsyncClient() as client:
           response = await client.request(
               method, uri, headers=headers or {}, json=body
           )
           return {
               "status_code": response.status_code,
               "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
           }
   ```

3. **Update shared.py** with activity-specific dataclasses if needed

4. **Extract configuration from Conductor tasks**
   - Document timeout requirements
   - Note retry policies needed
   - Identify special task configurations

### Verification
```bash
test -f {project_name}/activities.py
python3 -m py_compile {project_name}/activities.py
grep -q '@activity.defn' {project_name}/activities.py
```

### Common Issues
- **HTTP authentication**: Document if HTTP tasks require auth headers
- **Complex input transformations**: May need custom dataclasses
- **External dependencies**: Document third-party services called

</details>

<details>
<summary><strong>Phase 4: Generate Workflow</strong></summary>

### Objectives
- Create workflow class with @workflow.defn
- Translate Conductor control flow to Python
- Implement activity execution with proper timeouts
- Handle data passing between tasks
- Configure retry policies

### Tasks

1. **Create workflow.py**
   ```python
   import asyncio
   from datetime import timedelta
   from dataclasses import dataclass
   from typing import Optional, List, Dict, Any
   from temporalio import workflow
   from temporalio.common import RetryPolicy

   with workflow.unsafe.imports_passed_through():
       from .shared import WorkflowInput, WorkflowOutput
       from . import activities

   @workflow.defn
   class MyWorkflow:
       """
       Temporal workflow migrated from Conductor workflow: {workflow_name}

       Original Conductor file: {conductor_file}
       """

       @workflow.run
       async def run(self, input: WorkflowInput) -> WorkflowOutput:
           """
           Execute the workflow.

           Args:
               input: Workflow input parameters

           Returns:
               WorkflowOutput containing workflow results
           """
           workflow.logger.info(f"Starting workflow with input: {input}")

           # Translate Conductor tasks to activity executions
           # See control flow patterns below

           return WorkflowOutput(result="success")
   ```

2. **Translate control flow patterns** (see examples in Architectural Concepts section):
   - **Sequential**: Chain activities with await
   - **Parallel (FORK_JOIN)**: Use `asyncio.gather()`
   - **Conditional (SWITCH)**: Use `if/elif/else`
   - **Loops (DO_WHILE)**: Use `while` loop
   - **Dynamic parallel (DYNAMIC_FORK)**: List comprehension + `asyncio.gather()`
   - **Sub-workflows (SUB_WORKFLOW)**: Use `workflow.execute_child_workflow()`

3. **Implement WAIT tasks** with signals:
   ```python
   def __init__(self):
       self.received_data = None

   @workflow.signal
   async def receive_data(self, data: Dict[str, Any]):
       """Signal handler for external data."""
       self.received_data = data

   # In run method:
   await workflow.wait_condition(lambda: self.received_data is not None)
   ```

4. **Configure activity execution**
   ```python
   result = await workflow.execute_activity(
       activities.my_activity,
       args=[input.param],
       start_to_close_timeout=timedelta(seconds=300),
       retry_policy=RetryPolicy(
           maximum_attempts=3,
           initial_interval=timedelta(seconds=10),
           backoff_coefficient=2.0,
           maximum_interval=timedelta(seconds=100)
       )
   )
   ```

5. **Translate data passing**
   - Conductor `${workflow.input.field}` → `input.field`
   - Conductor `${task_name.output.field}` → `task_name_result.field`
   - Conductor `${workflow.variables.var}` → `var` (local variable)

### Verification
```bash
test -f {project_name}/workflow.py
python3 -m py_compile {project_name}/workflow.py
grep -q '@workflow.defn' {project_name}/workflow.py
grep -q '@workflow.run' {project_name}/workflow.py
```

### Common Issues
- **Nested control flow**: Carefully preserve execution order
- **Complex data transformations**: May need helper functions
- **Timeouts**: Ensure activity timeouts are appropriate for task duration

</details>

<details>
<summary><strong>Phase 5: Generate Worker</strong></summary>

### Objectives
- Create worker registration script
- Register workflows and activities
- Configure task queue
- Add proper logging

### Tasks

1. **Create worker.py**
   ```python
   #!/usr/bin/env -S uv run --script
   # /// script
   # requires-python = ">=3.11"
   # dependencies = ["temporalio>=1.7.0"]
   # ///
   import asyncio
   import logging
   import os
   from concurrent.futures import ThreadPoolExecutor
   from temporalio.client import Client
   from temporalio.worker import Worker

   from .workflow import MyWorkflow
   from . import activities

   async def main() -> None:
       """Run Temporal worker."""
       logging.basicConfig(level=logging.INFO)
       logger = logging.getLogger(__name__)

       # Write PID for process management
       with open("worker.pid", "w") as f:
           f.write(str(os.getpid()))

       logger.info("Worker starting")

       # Connect to Temporal server
       client = await Client.connect("localhost:7233")

       # Create worker
       async with Worker(
           client,
           task_queue="{task_queue}",
           workflows=[MyWorkflow],
           activities=[
               activities.activity1,
               activities.activity2,
               # List all activities
           ],
           activity_executor=ThreadPoolExecutor(5)
       ):
           logger.info("Worker ready — polling: {task_queue}")
           try:
               while True:
                   await asyncio.sleep(1)
           except KeyboardInterrupt:
               logger.info("Worker shutting down…")

   if __name__ == "__main__":
       asyncio.run(main())
   ```

2. **List all activities** from Phase 3 analysis

3. **Configure task queue** from conductor-analysis.json

### Verification
```bash
test -f {project_name}/worker.py
python3 -m py_compile {project_name}/worker.py
grep -q 'Worker(' {project_name}/worker.py
```

</details>

<details>
<summary><strong>Phase 6: Generate Starter</strong></summary>

### Objectives
- Create workflow starter client
- Generate example input data
- Add workflow execution code
- Display results and workflow URL

### Tasks

1. **Create starter.py**
   ```python
   #!/usr/bin/env -S uv run --script
   # /// script
   # requires-python = ">=3.11"
   # dependencies = ["temporalio>=1.7.0"]
   # ///
   import asyncio
   import uuid
   import logging
   from datetime import timedelta
   from temporalio.client import Client

   from .workflow import MyWorkflow
   from .shared import WorkflowInput

   async def main() -> None:
       """Start workflow execution."""
       logging.basicConfig(level=logging.INFO)
       logger = logging.getLogger(__name__)

       # Connect to Temporal server
       client = await Client.connect("localhost:7233")

       # Create workflow input with example data
       workflow_input = WorkflowInput(
           param1="example_value",
           param2=123,
           # TODO: Customize input values
       )

       # Generate unique workflow ID
       workflow_id = f"{workflow_name}-{uuid.uuid4()}"

       logger.info(f"Starting workflow: {workflow_id}")

       # Start workflow
       handle = await client.start_workflow(
           MyWorkflow.run,
           workflow_input,
           id=workflow_id,
           task_queue="{task_queue}",
           execution_timeout=timedelta(hours=1)
       )

       print(f"Started workflow: {handle.id}")
       print(f"Workflow URL: http://localhost:8233/namespaces/default/workflows/{handle.id}")

       # Wait for workflow to complete
       result = await handle.result()
       print(f"Workflow result: {result}")

   if __name__ == "__main__":
       asyncio.run(main())
   ```

2. **Generate example input data** based on Conductor input_parameters

3. **Add comments** about customizing input values

### Verification
```bash
test -f {project_name}/starter.py
python3 -m py_compile {project_name}/starter.py
grep -q 'start_workflow(' {project_name}/starter.py
```

</details>

<details>
<summary><strong>Phase 7: Generate Tests</strong></summary>

### Objectives
- Create unit tests for activities
- Create integration tests for workflows
- Test control flow branches
- Use Temporal testing framework

### Tasks

1. **Create test_activities.py**
   ```python
   import pytest
   from .activities import *

   @pytest.mark.asyncio
   async def test_simple_activity():
       """Test simple activity function."""
       result = await simple_task_activity(input_param="test")
       assert result is not None
       assert result["status"] == "success"

   @pytest.mark.asyncio
   async def test_http_activity():
       """Test HTTP activity function."""
       # Mock httpx if needed or test against real endpoint
       result = await http_task_activity(
           uri="https://example.com/api/test",
           method="GET"
       )
       assert result is not None
       assert "status_code" in result
   ```

2. **Create test_workflow.py**
   ```python
   import pytest
   from temporalio.testing import WorkflowEnvironment
   from temporalio.worker import Worker

   from .workflow import MyWorkflow
   from .shared import WorkflowInput
   from . import activities

   @pytest.mark.asyncio
   async def test_workflow_happy_path():
       """Test workflow with valid input."""
       async with await WorkflowEnvironment.start_time_skipping() as env:
           async with Worker(
               env.client,
               task_queue="test-queue",
               workflows=[MyWorkflow],
               activities=[activities.activity1, activities.activity2]
           ):
               workflow_input = WorkflowInput(
                   param1="test_value",
                   param2=123
               )

               result = await env.client.execute_workflow(
                   MyWorkflow.run,
                   workflow_input,
                   id="test-workflow-id",
                   task_queue="test-queue"
               )

               assert result is not None
               # Add specific assertions

   @pytest.mark.asyncio
   async def test_workflow_conditional_branch():
       """Test workflow conditional logic."""
       # Test different branches of SWITCH statements
       pass
   ```

3. **Test control flow branches**
   - Test each SWITCH case
   - Test loop entry and exit conditions
   - Test parallel execution results

### Verification
```bash
test -f {project_name}/test_activities.py
test -f {project_name}/test_workflow.py
python3 -m py_compile {project_name}/test_*.py
```

</details>

<details>
<summary><strong>Phase 8: Setup and Validation</strong></summary>

### Objectives
- Install project dependencies
- Run syntax validation
- Run type checking with mypy strict
- Run all unit tests
- Create automated setup script

### Tasks

1. **Install dependencies**
   ```bash
   cd {project_name}
   uv venv
   uv add temporalio httpx
   uv add --dev pytest pytest-asyncio mypy
   ```

2. **Run syntax validation**
   ```bash
   python3 -m py_compile {project_name}/*.py
   ```

3. **Run mypy type checking**
   ```bash
   mypy {project_name} --strict --ignore-missing-imports
   ```
   Fix any type errors until mypy passes

4. **Run unit tests**
   ```bash
   pytest -v
   ```
   Fix any failing tests

5. **Create setup.sh**
   ```bash
   #!/bin/bash
   set -e

   echo "Setting up project..."

   # Unset Temporal environment variables
   unset TEMPORAL_CLI_ADDRESS TEMPORAL_CLI_NAMESPACE TEMPORAL_CLI_TLS_CERT \
         TEMPORAL_CLI_TLS_KEY TEMPORAL_CERT_PATH TEMPORAL_KEY_PATH \
         TEMPORAL_NAMESPACE TEMPORAL_ADDRESS TEMPORAL_API_KEY \
         TEMPORAL_HOST_PORT TEMPORAL_TLS_CERT TEMPORAL_TLS_KEY

   # Check Python version
   python3 --version | grep -q 'Python 3\\.1[1-9]\\|Python 3\\.[2-9][0-9]' || {
       echo "Error: Python 3.11+ required"
       exit 1
   }

   # Install dependencies
   echo "Installing dependencies..."
   uv venv
   uv add temporalio httpx
   uv add --dev pytest pytest-asyncio mypy

   # Run tests
   echo "Running tests..."
   pytest -v

   # Run type checking
   echo "Running type checking..."
   mypy {project_name} --strict --ignore-missing-imports

   echo "Setup complete!"
   echo ""
   echo "Next steps:"
   echo "1. Start Temporal dev server: temporal server start-dev"
   echo "2. Start worker: uv run worker.py"
   echo "3. Execute workflow: uv run starter.py"
   ```

6. **Make executable**
   ```bash
   chmod +x setup.sh
   ```

7. **Create CONDUCTOR_MIGRATION_NOTES.md**
   Document any:
   - Conductor features that couldn't be translated
   - Manual implementation steps required
   - Behavioral differences
   - Assumptions made during translation

### Verification
```bash
cd {project_name}
python3 -c 'import sys; sys.path.insert(0, "."); import workflow, activities, shared, worker, starter'
pytest -v
test -f setup.sh
test -x setup.sh
```

</details>

<details>
<summary><strong>Phase 9: End-to-End Test</strong></summary>

### Objectives
- Start Temporal dev server
- Start worker
- Execute workflow
- Verify workflow completion
- Validate results

### Tasks

1. **Unset Temporal environment variables**
   ```bash
   unset TEMPORAL_CLI_ADDRESS TEMPORAL_CLI_NAMESPACE TEMPORAL_CLI_TLS_CERT \
         TEMPORAL_CLI_TLS_KEY TEMPORAL_CERT_PATH TEMPORAL_KEY_PATH \
         TEMPORAL_NAMESPACE TEMPORAL_ADDRESS TEMPORAL_API_KEY \
         TEMPORAL_HOST_PORT TEMPORAL_TLS_CERT TEMPORAL_TLS_KEY
   ```
   This ensures connection to local dev server (localhost:7233)

2. **Check if Temporal dev server is running**
   ```bash
   temporal workflow list --namespace default >/dev/null 2>&1
   ```
   If not running:
   ```bash
   temporal server start-dev &
   sleep 5
   ```

3. **Start worker in background**
   ```bash
   cd {project_name}
   uv run worker.py > worker.log 2>&1 &
   WORKER_PID=$!
   echo $WORKER_PID > worker.pid
   sleep 3
   ps -p $WORKER_PID >/dev/null || { echo "ERROR: Worker failed"; tail worker.log; exit 1; }
   ```

4. **Execute workflow**
   ```bash
   uv run starter.py
   ```
   Capture workflow ID from output

5. **Verify workflow completion**
   ```bash
   temporal workflow show --workflow-id <workflow_id> --namespace default
   ```
   Check:
   - Status is COMPLETED
   - No errors in execution history
   - Result matches expectations

6. **Validate with Temporal CLI**
   ```bash
   # List recent workflows
   temporal workflow list --namespace default --output json

   # Show specific workflow details
   temporal workflow show --workflow-id <workflow_id>
   ```

7. **Clean up**
   ```bash
   kill $(cat worker.pid)
   rm worker.pid
   ```

8. **Document results**
   Create e2e-test-results.json with test outcomes

### Verification
```bash
test -f e2e-test-results.json
jq empty e2e-test-results.json
```

### Common Issues
- **Worker fails to start**: Check worker.log for connection errors
- **Workflow hangs**: Check for bugs in workflow logic, use `temporal workflow show` to see progress
- **Activity timeouts**: Increase start_to_close_timeout if tasks are slow

</details>

<details>
<summary><strong>Phase 10: Documentation and Finalization</strong></summary>

### Objectives
- Update README with comprehensive instructions
- Create Conductor comparison documentation
- Add inline code comments
- Generate migration summary report
- Finalize git status

### Tasks

1. **Update README.md**
   ```markdown
   # {Workflow Name} - Temporal Migration

   Migrated from Conductor workflow: `{conductor_file}`

   ## Overview
   [Brief description of what the workflow does]

   ## Prerequisites
   - Python 3.11+
   - Temporal dev server
   - UV package manager

   ## Setup

   1. Install dependencies:
      ```bash
      ./setup.sh
      ```

   2. Start Temporal dev server (in separate terminal):
      ```bash
      temporal server start-dev
      ```

   ## Running the Workflow

   1. Start the worker (in separate terminal):
      ```bash
      uv run worker.py
      ```

   2. Execute the workflow:
      ```bash
      uv run starter.py
      ```

   3. View workflow in Temporal Web UI:
      http://localhost:8233

   ## Testing

   Run unit tests:
   ```bash
   pytest -v
   ```

   Run type checking:
   ```bash
   mypy {project_name} --strict
   ```

   ## Project Structure

   - `shared.py` - Data models (dataclasses)
   - `activities.py` - Activity implementations
   - `workflow.py` - Workflow definition
   - `worker.py` - Worker registration
   - `starter.py` - Workflow starter
   - `test_*.py` - Unit tests

   ## Migration Notes

   See `CONDUCTOR_COMPARISON.md` for Conductor vs Temporal mapping details.
   See `CONDUCTOR_MIGRATION_NOTES.md` for migration-specific notes.

   ## Troubleshooting

   [Add common issues and solutions]
   ```

2. **Create CONDUCTOR_COMPARISON.md**
   Side-by-side examples of:
   - Each task type translation
   - Control flow pattern mappings
   - Data passing differences
   - Example from actual migrated workflow

3. **Add inline code comments**
   - Document complex control flow
   - Reference original Conductor task names
   - Explain data transformations

4. **Create migration-summary.json**
   ```json
   {
     "migration_date": "ISO 8601 timestamp",
     "conductor_file": "path/to/conductor.json",
     "workflow_name": "name",
     "project_name": "project_name",
     "statistics": {
       "total_conductor_tasks": 10,
       "activities_created": 5,
       "workflow_functions": 1,
       "test_functions": 8,
       "lines_of_code": 500
     },
     "task_type_mapping": {
       "SIMPLE": 5,
       "HTTP": 2,
       "SWITCH": 1,
       "FORK_JOIN": 1
     },
     "validation_results": {
       "syntax_valid": true,
       "type_checking_passed": true,
       "unit_tests_passed": true,
       "e2e_test_passed": true
     },
     "notes": []
   }
   ```

5. **Check git status**
   ```bash
   git status --porcelain
   ```

### Verification
```bash
test -f {project_name}/README.md
grep -q 'Setup' {project_name}/README.md
test -f {project_name}/CONDUCTOR_COMPARISON.md
test -f migration-summary.json
jq empty migration-summary.json
```

</details>

---

## Validation and Testing

### Syntax Validation
```bash
python3 -m py_compile {project_name}/*.py
```
All files must compile without errors.

### Type Checking
```bash
mypy {project_name} --strict --ignore-missing-imports
```
Must pass with no type errors.

### Unit Tests
```bash
cd {project_name}
pytest -v
```
All tests must pass.

### Integration Test (End-to-End)
```bash
# Terminal 1: Start Temporal dev server
temporal server start-dev

# Terminal 2: Start worker
uv run worker.py

# Terminal 3: Execute workflow
uv run starter.py

# Verify in Temporal Web UI
open http://localhost:8233
```

### Verification Checklist
- [ ] All Python files compile without syntax errors
- [ ] mypy --strict passes with no errors
- [ ] All unit tests pass
- [ ] Worker starts successfully and polls task queue
- [ ] Workflow executes and completes successfully
- [ ] Workflow result matches expectations
- [ ] No errors in Temporal Web UI execution history

---

## Migration Success Criteria

### Required Outcomes
✅ **Complete project structure** generated with all files
✅ **Syntax validation** passes for all Python files
✅ **Type checking** passes with mypy --strict
✅ **Unit tests** pass with good coverage
✅ **End-to-end execution** succeeds against Temporal dev server
✅ **Documentation** complete with setup and usage instructions
✅ **Code quality** follows Python best practices and PEP 8

### Quality Standards
- Type hints on all functions (strict mode)
- Comprehensive docstrings
- Proper error handling
- Appropriate timeouts and retry policies
- Clean separation of concerns (activities, workflows, data)

### Deliverables Checklist
- [ ] Working Temporal Python project
- [ ] All activities implemented
- [ ] Workflow logic correctly translated
- [ ] Worker and starter scripts functional
- [ ] Comprehensive test suite
- [ ] Complete documentation (README, comparison, migration notes)
- [ ] Setup script for easy installation
- [ ] Migration summary report

---

## Troubleshooting

### Common Migration Issues

#### Conductor JSON Parsing Errors
**Symptom**: jq fails to parse Conductor file
**Solution**: Validate JSON syntax with `jq empty file.json`, fix any JSON errors

#### Complex JSONPath Expressions
**Symptom**: Difficulty translating complex JSONPath to Python
**Solution**: Break down into intermediate variables, document complex transformations

#### Nested Control Flow
**Symptom**: Difficult to translate nested FORK_JOIN + SWITCH combinations
**Solution**: Create helper functions, carefully preserve execution order, add detailed comments

#### Activity Timeout Issues
**Symptom**: Activities timing out during execution
**Solution**: Increase `start_to_close_timeout`, check activity implementation performance

#### Type Checking Errors
**Symptom**: mypy strict mode fails
**Solution**: Add explicit type hints, avoid `Any`, use Optional for nullable fields

#### Test Failures
**Symptom**: Unit tests fail after generation
**Solution**: Review test assertions, ensure mock data matches actual behavior, fix activity implementations

#### Worker Connection Errors
**Symptom**: Worker can't connect to Temporal server
**Solution**: Ensure dev server is running on localhost:7233, unset Temporal environment variables

#### Workflow Hangs During Execution
**Symptom**: Workflow starts but never completes
**Solution**:
- Check worker.log for errors
- Use `temporal workflow show` to see progress
- Look for bugs in workflow logic (infinite loops, missing signals)
- Check if activities are registered correctly

### Getting Additional Help

- **AGENTS.md**: General Temporal development practices and patterns
- **Temporal Documentation**: https://docs.temporal.io/
- **Temporal Python SDK**: https://github.com/temporalio/sdk-python
- **Temporal Samples**: https://github.com/temporalio/samples-python
- **Conductor Documentation**: https://conductor.netflix.com/

---

## Next Steps After Migration

1. **Customize Activity Implementations**
   - Replace placeholder logic with actual business logic
   - Add error handling
   - Configure appropriate timeouts

2. **Enhance Input Validation**
   - Add input validation in WorkflowInput dataclass
   - Implement custom validators

3. **Production Readiness**
   - Configure production Temporal server connection
   - Set up monitoring and observability
   - Add metrics and logging
   - Configure deployment (Docker, Kubernetes, etc.)

4. **Optimize Performance**
   - Tune activity timeouts
   - Configure retry policies based on failure patterns
   - Add caching where appropriate

5. **Extend Testing**
   - Add more edge case tests
   - Add performance tests
   - Add chaos engineering tests

---

## Reference: Complete Migration Script

For automated migration, use this one-command script:

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
# [Continue with analysis logic]

# Phase 2-10: Execute migration phases
# [Implementation based on detailed phase instructions above]

echo "Migration complete! Project created at: $PROJECT_NAME"
echo "Run ./setup.sh to install and test."
```

---

For general Temporal development guidance and best practices, see **[AGENTS.md](./AGENTS.md)**.
