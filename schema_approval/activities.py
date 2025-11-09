"""Activity implementations for the schema approval workflow."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Sequence

from temporalio import activity

from .shared import (
    CompleteReviewRequest,
    CompletionReport,
    ReviewOutcome,
    ReviewRequest,
    ReviewRoundPlan,
    SchemaSubmission,
)


@activity.defn
async def upload_schema(plan: ReviewRoundPlan, iteration: int) -> SchemaSubmission:
    """Upload the schema for the current iteration."""

    activity.logger.info(
        "Uploading schema %s for iteration %s", plan.schema_id, iteration
    )
    return SchemaSubmission(
        schema_id=plan.schema_id,
        body=plan.schema_body,
        iteration=iteration,
    )


@activity.defn
async def perform_review(request: ReviewRequest) -> ReviewOutcome:
    """Return the predetermined review outcome for a given stage."""

    if request.decision.skip_follow_up and request.stage != "Review2":
        raise ValueError(
            "skip_follow_up is only supported for the second level review"
        )
    activity.logger.info(
        "Review stage %s by %s approved=%s",
        request.stage,
        request.decision.reviewer,
        request.decision.approved,
    )
    return ReviewOutcome(
        stage=request.stage,
        reviewer=request.decision.reviewer,
        approved=request.decision.approved,
        comments=request.decision.comments,
        skip_additional_review=request.decision.skip_follow_up,
    )


@activity.defn
async def complete_review(request: CompleteReviewRequest) -> CompletionReport:
    """Finalize the review process when all reviewers have approved."""

    request.ensure_all_approved()
    summary_details: dict[str, Any] = {
        "submission": asdict(request.submission),
        "reviewers": [outcome.reviewer for outcome in request.approvals],
    }
    summary = (
        "Schema {schema_id} approved in iteration {iteration} by {reviewers}".format(
            schema_id=request.submission.schema_id,
            iteration=request.iteration,
            reviewers=", ".join(summary_details["reviewers"]),
        )
    )
    activity.logger.info("%s", summary)
    return CompletionReport(
        submission=request.submission,
        iteration=request.iteration,
        approved=True,
        summary=summary,
    )


def summarize_outcomes(outcomes: Sequence[ReviewOutcome]) -> Sequence[str]:
    """Return human readable summaries for the supplied outcomes."""

    return [
        f"{outcome.stage} ({outcome.reviewer}): {'approved' if outcome.approved else 'rejected'}"
        for outcome in outcomes
    ]
