"""Shared data structures for the schema approval workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

DEFAULT_TASK_QUEUE = "schema-approval-task-queue"


@dataclass(slots=True)
class SchemaSubmission:
    """Payload describing a schema submission to be reviewed."""

    schema_id: str
    version: int
    description: str
    content_uri: str
    submitted_by: str


@dataclass(slots=True)
class ReviewAssignment:
    """Details delivered to a reviewer via an activity call."""

    stage: str
    reviewer: str
    submission: SchemaSubmission
    instructions: str


@dataclass(slots=True)
class UploadSummary:
    """Result returned by the ``upload_schema`` activity."""

    schema_id: str
    version: int
    storage_location: str
    uploaded_by: str


@dataclass(slots=True)
class ReviewDecision:
    """Signal payload capturing the decision of a reviewer."""

    stage: str
    reviewer: str
    submission_version: int
    approved: bool
    comment: Optional[str] = None
    requires_additional_review: Optional[bool] = None


@dataclass(slots=True)
class RevisionRequest:
    """Information recorded when a submission needs another revision."""

    submission: SchemaSubmission
    reason: str
    requested_by_stage: str


@dataclass(slots=True)
class SchemaApprovalWorkflowInput:
    """Workflow input containing reviewer roster and initial submission."""

    initial_submission: SchemaSubmission
    stage_one_reviewers: Sequence[str]
    stage_two_reviewer: str
    stage_three_reviewer: str


@dataclass(slots=True)
class SchemaApprovalResult:
    """Returned value when the workflow finishes successfully."""

    schema_id: str
    approved_version: int
    attempts: int
    approvers: Dict[str, str]
    completed_at: datetime


@dataclass(slots=True)
class ReviewRoundSnapshot:
    """Snapshot describing the current review round."""

    round_name: str
    submission_version: int
    awaiting_reviewers: Sequence[str] = field(default_factory=list)
    collected_decisions: Dict[str, ReviewDecision] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowStatus:
    """Returned by the workflow query method for observability."""

    current_round: Optional[ReviewRoundSnapshot]
    awaiting_resubmission: bool
    attempts: int
    history: List[str]
