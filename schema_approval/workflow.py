"""Workflow definition for the schema approval process."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import List

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from .activities import complete_review, perform_review, upload_schema
from .shared import (
    CompleteReviewRequest,
    ReviewDecisionPlan,
    ReviewIterationResult,
    ReviewOutcome,
    ReviewRequest,
    ReviewRoundPlan,
    ReviewStageName,
    SchemaApprovalInput,
    SchemaApprovalResult,
    SchemaSubmission,
)

_ACTIVITY_TIMEOUT = timedelta(seconds=30)
_RETRY_POLICY = RetryPolicy(maximum_attempts=3)


@workflow.defn(name="schema_approval_workflow")
class SchemaApprovalWorkflow:
    """Temporal workflow translated from the Conductor review_approval definition."""

    def __init__(self) -> None:
        self._history: List[ReviewIterationResult] = []

    @workflow.run
    async def run(self, request: SchemaApprovalInput) -> SchemaApprovalResult:
        iteration = 0
        for iteration, round_plan in enumerate(request.rounds, start=1):
            submission = await self._upload(round_plan, iteration)
            primary_review, secondary_review = await self._perform_first_reviews(
                round_plan, iteration
            )
            if not (primary_review.approved and secondary_review.approved):
                self._record_iteration(
                    iteration=iteration,
                    submission=submission,
                    primary=primary_review,
                    secondary=secondary_review,
                    second_level=None,
                    final=None,
                    approved=False,
                )
                continue

            review2_outcome = await self._execute_review_stage(
                stage="Review2",
                iteration=iteration,
                decision=round_plan.review2,
            )
            if not review2_outcome.approved:
                self._record_iteration(
                    iteration=iteration,
                    submission=submission,
                    primary=primary_review,
                    secondary=secondary_review,
                    second_level=review2_outcome,
                    final=None,
                    approved=False,
                )
                continue

            requires_review3 = (
                round_plan.requires_review3 and review2_outcome.requires_follow_up
            )
            final_review: ReviewOutcome | None = None
            if requires_review3:
                if round_plan.review3 is None:
                    raise ApplicationError(
                        "Review3 plan missing despite requirement"
                    )
                final_review = await self._execute_review_stage(
                    stage="Review3",
                    iteration=iteration,
                    decision=round_plan.review3,
                )
                if not final_review.approved:
                    self._record_iteration(
                        iteration=iteration,
                        submission=submission,
                        primary=primary_review,
                        secondary=secondary_review,
                        second_level=review2_outcome,
                        final=final_review,
                        approved=False,
                    )
                    continue

            completion = await workflow.execute_activity(
                complete_review,
                CompleteReviewRequest(
                    submission=submission,
                    iteration=iteration,
                    approvals=self._collect_approvals(
                        primary_review,
                        secondary_review,
                        review2_outcome,
                        final_review,
                    ),
                ),
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )
            self._record_iteration(
                iteration=iteration,
                submission=submission,
                primary=primary_review,
                secondary=secondary_review,
                second_level=review2_outcome,
                final=final_review,
                approved=True,
            )
            return SchemaApprovalResult(
                final_report=completion,
                history=tuple(self._history),
            )

        raise ApplicationError(
            f"Schema was not approved after {iteration} iteration(s)"
        )

    async def _upload(
        self, plan: ReviewRoundPlan, iteration: int
    ) -> SchemaSubmission:
        return await workflow.execute_activity(
            upload_schema,
            args=[plan, iteration],
            start_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )

    async def _perform_first_reviews(
        self, plan: ReviewRoundPlan, iteration: int
    ) -> tuple[ReviewOutcome, ReviewOutcome]:
        primary_request = ReviewRequest(
            stage="Review1.a",
            iteration=iteration,
            decision=plan.review1_primary,
        )
        secondary_request = ReviewRequest(
            stage="Review1.b",
            iteration=iteration,
            decision=plan.review1_secondary,
        )
        primary_review, secondary_review = await asyncio.gather(
            workflow.execute_activity(
                perform_review,
                primary_request,
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            ),
            workflow.execute_activity(
                perform_review,
                secondary_request,
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            ),
        )
        return primary_review, secondary_review

    async def _execute_review_stage(
        self,
        *,
        stage: ReviewStageName,
        iteration: int,
        decision: ReviewDecisionPlan,
    ) -> ReviewOutcome:
        request = ReviewRequest(
            stage=stage,
            iteration=iteration,
            decision=decision,
        )
        return await workflow.execute_activity(
            perform_review,
            request,
            start_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )

    def _collect_approvals(
        self,
        primary: ReviewOutcome,
        secondary: ReviewOutcome,
        review2: ReviewOutcome,
        review3: ReviewOutcome | None,
    ) -> tuple[ReviewOutcome, ...]:
        approvals = [primary, secondary, review2]
        if review3 is not None:
            approvals.append(review3)
        return tuple(approvals)

    def _record_iteration(
        self,
        *,
        iteration: int,
        submission: SchemaSubmission,
        primary: ReviewOutcome,
        secondary: ReviewOutcome,
        second_level: ReviewOutcome | None,
        final: ReviewOutcome | None,
        approved: bool,
    ) -> None:
        self._history.append(
            ReviewIterationResult(
                iteration=iteration,
                submission=submission,
                primary_review=primary,
                secondary_review=secondary,
                second_level_review=second_level,
                final_review=final,
                approved=approved,
            )
        )
