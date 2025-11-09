# Schema Approval Temporal Workflow

This project contains a Temporal Python SDK implementation of the `schema_approval` workflow
originally defined for Netflix Conductor in
[`conductor-definitions/review_approval.json`](conductor-definitions/review_approval.json).
The workflow orchestrates a multi-stage schema review process with parallel reviewers, a
conditional escalation round, and revision loops until the submission is approved.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management and running the scripts
- A Temporal Server instance reachable at `localhost:7233` (e.g., `temporal server start-dev`)
- Temporal CLI (`temporal`) for sending signals from the command line

## Project layout

```
schema_approval/
  activities.py       # Activity implementations (upload, notifications, bookkeeping)
  shared.py           # Dataclasses and shared constants
  starter.py          # Utility to start a workflow execution
  worker.py           # Worker that hosts the workflow and activities
  workflow.py         # Temporal workflow implementation
pyproject.toml        # Project metadata and dependencies
README.md             # This guide
```

## Installation

The repository is ready to use with uv:

```bash
uv sync --all-extras
```

The command provisions a virtual environment, installs the Temporal SDK, and the optional
linting/type-checking tools defined in `pyproject.toml`.

## Running the worker

Start the worker so it can process workflow and activity tasks:

```bash
uv run schema_approval/worker.py
```

The worker registers the workflow and the following activities on the
`schema-approval-task-queue`:

- `upload_schema`
- `dispatch_review_request`
- `record_revision_request`
- `finalize_review`

## Starting a workflow execution

In a separate terminal, start a workflow execution with the starter utility. The positional
argument is the schema identifier; additional flags let you customise reviewers and metadata:

```bash
uv run schema_approval/starter.py inventory-service \
  --version 1 \
  --description "Initial schema for the inventory service" \
  --content-uri https://example.com/schemas/inventory-v1.json \
  --submitted-by owner@example.com \
  --reviewer-a alice@example.com \
  --reviewer-b bob@example.com \
  --senior-reviewer carol@example.com \
  --compliance-reviewer dave@example.com
```

The starter prints the workflow identifier and handy CLI snippets for sending signals. Because
the workflow contains human approvals, it does **not** complete immediately—reviewers must
provide their decisions through signals.

## Sending review decisions

Each reviewer sends a `record_review_decision` signal. Replace values with the actual workflow
identifier and reviewer details:

```bash
temporal workflow signal --workflow-id <workflow-id> \
  --name record_review_decision \
  --input '{"stage": "Review1.a", "reviewer": "alice@example.com", "submission_version": 1, "approved": true}'

temporal workflow signal --workflow-id <workflow-id> \
  --name record_review_decision \
  --input '{"stage": "Review1.b", "reviewer": "bob@example.com", "submission_version": 1, "approved": true}'
```

After the parallel stage succeeds, the round-two reviewer decides whether the submission should
move to compliance review by toggling `requires_additional_review`:

```bash
temporal workflow signal --workflow-id <workflow-id> \
  --name record_review_decision \
  --input '{"stage": "Review2", "reviewer": "carol@example.com", "submission_version": 1, "approved": true, "requires_additional_review": false}'
```

If compliance review is required, the third reviewer must also approve:

```bash
temporal workflow signal --workflow-id <workflow-id> \
  --name record_review_decision \
  --input '{"stage": "Review3", "reviewer": "dave@example.com", "submission_version": 1, "approved": true}'
```

## Requesting revisions / resubmitting

If any reviewer rejects the submission the workflow waits for a resubmission. Use the
`submit_schema` signal to provide a higher version and restart the review loop:

```bash
temporal workflow signal --workflow-id <workflow-id> \
  --name submit_schema \
  --input '{"schema_id": "inventory-service", "version": 2, "description": "Updated schema", "content_uri": "https://example.com/schemas/inventory-v2.json", "submitted_by": "owner@example.com"}'
```

Version numbers determine the current review attempt; older versions are automatically ignored.

## Inspecting workflow status

The workflow exposes a `status` query that reports the active review round, pending reviewers,
and a textual history of notable events:

```bash
temporal workflow query --workflow-id <workflow-id> --type status
```

## Mapping Conductor tasks to Temporal components

| Conductor task                    | Temporal translation                                                |
|----------------------------------|---------------------------------------------------------------------|
| `upload_schema` (SIMPLE)         | `upload_schema` activity                                            |
| `Review1.a`, `Review1.b`         | `dispatch_review_request` activities + `record_review_decision` signals |
| `Review1Check` (SWITCH)          | Workflow logic checking both parallel decisions                     |
| `Review2` (SIMPLE)               | `dispatch_review_request` activity for the senior reviewer          |
| `Review2Check` (SWITCH)          | Workflow branch on `requires_additional_review` flag                |
| `Review3` (SIMPLE)               | `dispatch_review_request` activity for compliance reviewer          |
| `Review3Check` (SWITCH)          | Workflow logic verifying the compliance decision                    |
| `CompleteReview` (SIMPLE)        | `finalize_review` activity                                          |
| `repeat_until_approved` (DO_WHILE) | Workflow loop waiting for `submit_schema` signals when rejected      |

## Configuration

Key configuration values live in `schema_approval/shared.py`:

- `DEFAULT_TASK_QUEUE`: task queue used by both worker and starter
- `SchemaApprovalWorkflowInput`: dataclass describing reviewer roster and initial submission

Adjust logging verbosity by setting the `PYTHONLOGGING` environment variable before running
scripts, e.g. `PYTHONLOGGING=DEBUG uv run schema_approval/worker.py`.

## Troubleshooting

- Ensure the Temporal Server is running and reachable at `localhost:7233`.
- Use `temporal workflow list` to confirm the workflow execution is active.
- Decisions referencing an outdated submission version are ignored—double-check the
  `submission_version` property when signaling.
- Run `uv sync --all-extras` again if you see import errors for `temporalio`.

## Development utilities

Optional quality checks are configured in `pyproject.toml`:

```bash
uv run ruff check schema_approval/
uv run mypy schema_approval/
```

These tools are not required for execution but help maintain code quality.
