from __future__ import annotations

from datetime import timedelta

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from schema_approval.activities import complete_review, perform_review, upload_schema
from schema_approval.shared import ReviewDecisionPlan, ReviewRoundPlan, SchemaApprovalInput
from schema_approval.workflow import SchemaApprovalWorkflow


@pytest.mark.asyncio
async def test_workflow_completes_without_review3() -> None:
    env = await WorkflowEnvironment.start_time_skipping()
    async with env:
        task_queue = "schema-approval-tests-no-review3"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[SchemaApprovalWorkflow],
            activities=[upload_schema, perform_review, complete_review],
        ):
            request = SchemaApprovalInput(
                rounds=[
                    ReviewRoundPlan(
                        schema_id="schema-alpha",
                        schema_body="body",
                        review1_primary=ReviewDecisionPlan(
                            reviewer="alice",
                            approved=True,
                        ),
                        review1_secondary=ReviewDecisionPlan(
                            reviewer="bob",
                            approved=True,
                        ),
                        review2=ReviewDecisionPlan(
                            reviewer="carol",
                            approved=True,
                            skip_follow_up=True,
                        ),
                        requires_review3=False,
                    )
                ]
            )
            result = await env.client.execute_workflow(
                SchemaApprovalWorkflow.run,
                request,
                id="test-no-review3",
                task_queue=task_queue,
                run_timeout=timedelta(minutes=5),
            )
            assert result.final_report.approved is True
            assert len(tuple(result.history)) == 1


@pytest.mark.asyncio
async def test_workflow_handles_multiple_iterations() -> None:
    env = await WorkflowEnvironment.start_time_skipping()
    async with env:
        task_queue = "schema-approval-tests-review3"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[SchemaApprovalWorkflow],
            activities=[upload_schema, perform_review, complete_review],
        ):
            request = SchemaApprovalInput(
                rounds=[
                    ReviewRoundPlan(
                        schema_id="schema-beta",
                        schema_body="body",
                        review1_primary=ReviewDecisionPlan(
                            reviewer="alice",
                            approved=False,
                        ),
                        review1_secondary=ReviewDecisionPlan(
                            reviewer="bob",
                            approved=True,
                        ),
                        review2=ReviewDecisionPlan(
                            reviewer="carol",
                            approved=False,
                        ),
                        requires_review3=False,
                    ),
                    ReviewRoundPlan(
                        schema_id="schema-gamma",
                        schema_body="body2",
                        review1_primary=ReviewDecisionPlan(
                            reviewer="alice",
                            approved=True,
                        ),
                        review1_secondary=ReviewDecisionPlan(
                            reviewer="bob",
                            approved=True,
                        ),
                        review2=ReviewDecisionPlan(
                            reviewer="carol",
                            approved=True,
                            skip_follow_up=False,
                        ),
                        requires_review3=True,
                        review3=ReviewDecisionPlan(
                            reviewer="dave",
                            approved=True,
                        ),
                    ),
                ]
            )
            result = await env.client.execute_workflow(
                SchemaApprovalWorkflow.run,
                request,
                id="test-with-review3",
                task_queue=task_queue,
                run_timeout=timedelta(minutes=5),
            )
            assert result.final_report.submission.schema_id == "schema-gamma"
            assert len(tuple(result.history)) == 2
            assert result.history[-1].approved is True


@pytest.mark.asyncio
async def test_workflow_raises_when_no_approval() -> None:
    env = await WorkflowEnvironment.start_time_skipping()
    async with env:
        task_queue = "schema-approval-tests-failure"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[SchemaApprovalWorkflow],
            activities=[upload_schema, perform_review, complete_review],
        ):
            request = SchemaApprovalInput(
                rounds=[
                    ReviewRoundPlan(
                        schema_id="schema-delta",
                        schema_body="body",
                        review1_primary=ReviewDecisionPlan(
                            reviewer="alice",
                            approved=False,
                        ),
                        review1_secondary=ReviewDecisionPlan(
                            reviewer="bob",
                            approved=False,
                        ),
                        review2=ReviewDecisionPlan(
                            reviewer="carol",
                            approved=False,
                        ),
                        requires_review3=False,
                    )
                ]
            )
            with pytest.raises(WorkflowFailureError) as exc:
                await env.client.execute_workflow(
                    SchemaApprovalWorkflow.run,
                    request,
                    id="test-no-approval",
                    task_queue=task_queue,
                    run_timeout=timedelta(minutes=5),
                )
            assert isinstance(exc.value.cause, ApplicationError)
