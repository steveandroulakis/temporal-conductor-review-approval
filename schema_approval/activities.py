"""Activity implementations for the schema approval workflow."""

from __future__ import annotations

import logging
from datetime import datetime

from temporalio import activity

from .shared import (
    RevisionRequest,
    ReviewAssignment,
    SchemaApprovalResult,
    SchemaSubmission,
    UploadSummary,
)

logger = logging.getLogger(__name__)


@activity.defn(name="upload_schema")
async def upload_schema(submission: SchemaSubmission) -> UploadSummary:
    """Persist the submitted schema and return a summary."""

    logger.info(
        "Uploading schema %s version %s from %s",
        submission.schema_id,
        submission.version,
        submission.submitted_by,
    )
    storage_location = f"s3://schemas/{submission.schema_id}/v{submission.version}.json"
    return UploadSummary(
        schema_id=submission.schema_id,
        version=submission.version,
        storage_location=storage_location,
        uploaded_by=submission.submitted_by,
    )


@activity.defn(name="dispatch_review_request")
async def dispatch_review_request(assignment: ReviewAssignment) -> None:
    """Send a review request notification to a reviewer."""

    logger.info(
        "Dispatching %s review to %s for schema %s v%s",
        assignment.stage,
        assignment.reviewer,
        assignment.submission.schema_id,
        assignment.submission.version,
    )
    logger.debug("Instructions: %s", assignment.instructions)


@activity.defn(name="record_revision_request")
async def record_revision_request(request: RevisionRequest) -> None:
    """Log that a revision is required for the submission."""

    logger.warning(
        "Revision requested after stage %s for schema %s v%s: %s",
        request.requested_by_stage,
        request.submission.schema_id,
        request.submission.version,
        request.reason,
    )


@activity.defn(name="finalize_review")
async def finalize_review(result: SchemaApprovalResult) -> None:
    """Record the successful completion of the review."""

    logger.info(
        "Schema %s approved at version %s after %s attempts",
        result.schema_id,
        result.approved_version,
        result.attempts,
    )
    approver_summary = ", ".join(
        f"{stage} -> {reviewer}" for stage, reviewer in sorted(result.approvers.items())
    )
    logger.info("Approvers: %s", approver_summary)
    logger.info("Completed at %s", datetime.isoformat(result.completed_at))
