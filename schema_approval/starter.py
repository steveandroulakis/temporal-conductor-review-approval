"""Starter script for launching the schema approval workflow."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import timedelta
from uuid import uuid4

from temporalio.client import Client

from .shared import ReviewDecisionPlan, ReviewRoundPlan, SchemaApprovalInput
from .worker import _TASK_QUEUE  # reuse task queue constant
from .workflow import SchemaApprovalWorkflow


async def main() -> None:
    """Execute the schema approval workflow using sample input."""

    client = await Client.connect("localhost:7233")

    sample_input = SchemaApprovalInput(
        rounds=[
            ReviewRoundPlan(
                schema_id="schema-v1",
                schema_body="initial schema definition",
                review1_primary=ReviewDecisionPlan(
                    reviewer="alice",
                    approved=False,
                    comments="Needs additional fields",
                ),
                review1_secondary=ReviewDecisionPlan(
                    reviewer="bob",
                    approved=True,
                    comments="Looks good to me",
                ),
                review2=ReviewDecisionPlan(
                    reviewer="carol",
                    approved=False,
                    comments="Pending updates from reviewers",
                ),
                requires_review3=False,
            ),
            ReviewRoundPlan(
                schema_id="schema-v2",
                schema_body="updated schema definition",
                review1_primary=ReviewDecisionPlan(
                    reviewer="alice",
                    approved=True,
                    comments="All comments resolved",
                ),
                review1_secondary=ReviewDecisionPlan(
                    reviewer="bob",
                    approved=True,
                    comments="Confirmed",
                ),
                review2=ReviewDecisionPlan(
                    reviewer="carol",
                    approved=True,
                    comments="Ready for final review",
                    skip_follow_up=False,
                ),
                requires_review3=True,
                review3=ReviewDecisionPlan(
                    reviewer="dave",
                    approved=True,
                    comments="Approved for deployment",
                ),
            ),
        ]
    )

    result = await client.execute_workflow(
        SchemaApprovalWorkflow.run,
        sample_input,
        id=f"schema-approval-{uuid4()}",
        task_queue=_TASK_QUEUE,
        run_timeout=timedelta(minutes=5),
    )

    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
