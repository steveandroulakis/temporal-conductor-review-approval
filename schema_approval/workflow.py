"""Temporal workflow implementation for schema approval."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Dict, Optional, Sequence

from temporalio import workflow
from temporalio.common import RetryPolicy

from .activities import (
    dispatch_review_request,
    finalize_review,
    record_revision_request,
    upload_schema,
)
from .shared import (
    RevisionRequest,
    ReviewAssignment,
    ReviewDecision,
    ReviewRoundSnapshot,
    SchemaApprovalResult,
    SchemaApprovalWorkflowInput,
    SchemaSubmission,
    WorkflowStatus,
)

logger = workflow.logger

_ACTIVITY_TIMEOUT = timedelta(minutes=2)
_RETRY_POLICY = RetryPolicy(maximum_attempts=3)
_VALID_STAGES = {"Review1.a", "Review1.b", "Review2", "Review3"}


@workflow.defn
class SchemaApprovalWorkflow:
    """Workflow translating the Conductor schema_approval process."""

    def __init__(self) -> None:
        self.current_submission: Optional[SchemaSubmission] = None
        self.pending_submission: Optional[SchemaSubmission] = None
        self.decisions: Dict[str, ReviewDecision] = {}
        self.completed_decisions: Dict[str, ReviewDecision] = {}
        self.awaiting_resubmission = False
        self.attempts = 0
        self.history: list[str] = []
        self.current_round_name: Optional[str] = None
        self.expected_stages: Sequence[str] = ()

    @workflow.run
    async def run(self, config: SchemaApprovalWorkflowInput) -> SchemaApprovalResult:
        if len(config.stage_one_reviewers) != 2:
            raise ValueError("stage_one_reviewers must contain exactly two reviewers")

        self.current_submission = config.initial_submission
        self.history.append(
            f"Workflow started with submission v{config.initial_submission.version}"
        )

        while True:
            assert self.current_submission is not None
            self.attempts += 1
            attempt = self.attempts
            logger.info("Starting review attempt %s for schema %s", attempt, self.current_submission.schema_id)

            await self._upload_current_submission()
            await self._run_round_one(config)
            if not self._round_one_approved():
                await self._request_resubmission("Review1Check", "Round one reviewers requested changes")
                continue

            round_two_decision = await self._run_round_two(config)
            if not round_two_decision.approved:
                await self._request_resubmission(
                    "Review2Check", "Round two reviewer rejected the submission"
                )
                continue

            requires_more_review = bool(round_two_decision.requires_additional_review)
            if requires_more_review:
                round_three_decision = await self._run_round_three(config)
                if not round_three_decision.approved:
                    await self._request_resubmission(
                        "Review3Check", "Round three reviewer rejected the submission"
                    )
                    continue
                approvers = {
                    "Review1.a": self.completed_decisions["Review1.a"].reviewer,
                    "Review1.b": self.completed_decisions["Review1.b"].reviewer,
                    "Review2": round_two_decision.reviewer,
                    "Review3": round_three_decision.reviewer,
                }
            else:
                approvers = {
                    "Review1.a": self.completed_decisions["Review1.a"].reviewer,
                    "Review1.b": self.completed_decisions["Review1.b"].reviewer,
                    "Review2": round_two_decision.reviewer,
                }

            result = SchemaApprovalResult(
                schema_id=self.current_submission.schema_id,
                approved_version=self.current_submission.version,
                attempts=self.attempts,
                approvers=approvers,
                completed_at=workflow.now().replace(tzinfo=None),
            )
            await workflow.execute_activity(
                finalize_review,
                result,
                schedule_to_close_timeout=_ACTIVITY_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )
            logger.info(
                "Schema %s approved at version %s after %s attempts",
                result.schema_id,
                result.approved_version,
                result.attempts,
            )
            self.history.append(
                f"Approved submission v{self.current_submission.version} after {self.attempts} attempts"
            )
            return result

    async def _upload_current_submission(self) -> None:
        assert self.current_submission is not None
        summary = await workflow.execute_activity(
            upload_schema,
            self.current_submission,
            schedule_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )
        self.history.append(
            f"Uploaded schema version {summary.version} to {summary.storage_location}"
        )

    async def _run_round_one(self, config: SchemaApprovalWorkflowInput) -> None:
        assert self.current_submission is not None
        self.current_round_name = f"Round1:v{self.current_submission.version}"
        reviewers = list(config.stage_one_reviewers)
        self.expected_stages = ("Review1.a", "Review1.b")
        assignments = [
            ReviewAssignment(
                stage="Review1.a",
                reviewer=reviewers[0],
                submission=self.current_submission,
                instructions="Perform the first parallel review (A)",
            ),
            ReviewAssignment(
                stage="Review1.b",
                reviewer=reviewers[1],
                submission=self.current_submission,
                instructions="Perform the first parallel review (B)",
            ),
        ]
        await asyncio.gather(
            *[
                workflow.execute_activity(
                    dispatch_review_request,
                    assignment,
                    schedule_to_close_timeout=_ACTIVITY_TIMEOUT,
                    retry_policy=_RETRY_POLICY,
                )
                for assignment in assignments
            ]
        )
        await self._wait_for_stages(self.expected_stages)
        self.history.append(
            f"Collected round one decisions for version {self.current_submission.version}"
        )
        self.current_round_name = None
        self.expected_stages = ()

    def _round_one_approved(self) -> bool:
        decision_a = self.completed_decisions.get("Review1.a")
        decision_b = self.completed_decisions.get("Review1.b")
        return bool(decision_a and decision_a.approved and decision_b and decision_b.approved)

    async def _run_round_two(self, config: SchemaApprovalWorkflowInput) -> ReviewDecision:
        assert self.current_submission is not None
        self.current_round_name = f"Round2:v{self.current_submission.version}"
        self.expected_stages = ("Review2",)
        assignment = ReviewAssignment(
            stage="Review2",
            reviewer=config.stage_two_reviewer,
            submission=self.current_submission,
            instructions="Perform the senior schema review",
        )
        await workflow.execute_activity(
            dispatch_review_request,
            assignment,
            schedule_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )
        decisions = await self._wait_for_stages(self.expected_stages)
        decision = decisions["Review2"]
        self.history.append(
            f"Collected round two decision for version {self.current_submission.version}"
        )
        self.current_round_name = None
        self.expected_stages = ()
        return decision

    async def _run_round_three(self, config: SchemaApprovalWorkflowInput) -> ReviewDecision:
        assert self.current_submission is not None
        self.current_round_name = f"Round3:v{self.current_submission.version}"
        self.expected_stages = ("Review3",)
        assignment = ReviewAssignment(
            stage="Review3",
            reviewer=config.stage_three_reviewer,
            submission=self.current_submission,
            instructions="Perform the compliance review",
        )
        await workflow.execute_activity(
            dispatch_review_request,
            assignment,
            schedule_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )
        decisions = await self._wait_for_stages(self.expected_stages)
        decision = decisions["Review3"]
        self.history.append(
            f"Collected round three decision for version {self.current_submission.version}"
        )
        self.current_round_name = None
        self.expected_stages = ()
        return decision

    async def _wait_for_stages(self, stages: Sequence[str]) -> Dict[str, ReviewDecision]:
        await workflow.wait_condition(lambda: all(stage in self.decisions for stage in stages))
        decisions: Dict[str, ReviewDecision] = {}
        for stage in stages:
            decision = self.decisions.pop(stage)
            self.completed_decisions[stage] = decision
            decisions[stage] = decision
        return decisions

    async def _request_resubmission(self, stage: str, reason: str) -> None:
        assert self.current_submission is not None
        self.awaiting_resubmission = True
        await workflow.execute_activity(
            record_revision_request,
            RevisionRequest(
                submission=self.current_submission,
                reason=reason,
                requested_by_stage=stage,
            ),
            schedule_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )
        self.history.append(
            f"Awaiting resubmission after {stage} for version {self.current_submission.version}"
        )
        await workflow.wait_condition(lambda: self.pending_submission is not None)
        self.current_submission = self.pending_submission
        self.pending_submission = None
        self.decisions.clear()
        self.completed_decisions.clear()
        self.awaiting_resubmission = False
        self.current_round_name = None
        self.expected_stages = ()
        self.history.append(
            f"Received resubmission version {self.current_submission.version}"
        )

    @workflow.signal
    def submit_schema(self, submission: SchemaSubmission) -> None:
        if self.current_submission and submission.version <= self.current_submission.version:
            self.history.append(
                f"Ignored outdated submission v{submission.version}; current is v{self.current_submission.version}"
            )
            return
        self.pending_submission = submission
        logger.info(
            "Received schema resubmission version %s for %s",
            submission.version,
            submission.schema_id,
        )

    @workflow.signal
    def record_review_decision(self, decision: ReviewDecision) -> None:
        if not self.current_submission:
            logger.warning("Received decision before any submission available")
            return
        if decision.submission_version != self.current_submission.version:
            self.history.append(
                f"Ignored decision for version {decision.submission_version}; current is v{self.current_submission.version}"
            )
            return
        if decision.stage not in _VALID_STAGES:
            self.history.append(f"Ignored decision for unknown stage {decision.stage}")
            return
        self.decisions[decision.stage] = decision
        self.history.append(
            f"Recorded decision for {decision.stage} on version {decision.submission_version}"
        )

    @workflow.query
    def status(self) -> WorkflowStatus:
        snapshot: Optional[ReviewRoundSnapshot] = None
        if self.current_round_name and self.current_submission is not None:
            awaiting = [stage for stage in self.expected_stages if stage not in self.decisions]
            collected = {
                stage: decision
                for stage, decision in self.decisions.items()
                if stage in self.expected_stages
            }
            snapshot = ReviewRoundSnapshot(
                round_name=self.current_round_name,
                submission_version=self.current_submission.version,
                awaiting_reviewers=awaiting,
                collected_decisions=collected,
            )
        return WorkflowStatus(
            current_round=snapshot,
            awaiting_resubmission=self.awaiting_resubmission,
            attempts=self.attempts,
            history=list(self.history),
        )
