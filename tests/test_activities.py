from __future__ import annotations

import pytest

from schema_approval.activities import complete_review, perform_review, upload_schema
from schema_approval.shared import (
    CompleteReviewRequest,
    ReviewDecisionPlan,
    ReviewOutcome,
    ReviewRequest,
    ReviewRoundPlan,
    SchemaSubmission,
)


@pytest.mark.asyncio
async def test_upload_schema_returns_submission() -> None:
    plan = ReviewRoundPlan(
        schema_id="schema-1",
        schema_body="body",
        review1_primary=ReviewDecisionPlan(reviewer="alice", approved=True),
        review1_secondary=ReviewDecisionPlan(reviewer="bob", approved=True),
        review2=ReviewDecisionPlan(reviewer="carol", approved=True),
        requires_review3=False,
    )
    submission = await upload_schema(plan, 1)
    assert submission == SchemaSubmission(schema_id="schema-1", body="body", iteration=1)


@pytest.mark.asyncio
async def test_perform_review_success() -> None:
    request = ReviewRequest(
        stage="Review1.a",
        iteration=1,
        decision=ReviewDecisionPlan(reviewer="alice", approved=True, comments="ok"),
    )
    outcome = await perform_review(request)
    assert outcome.reviewer == "alice"
    assert outcome.approved is True
    assert outcome.comments == "ok"


@pytest.mark.asyncio
async def test_perform_review_invalid_skip_flag() -> None:
    request = ReviewRequest(
        stage="Review1.b",
        iteration=1,
        decision=ReviewDecisionPlan(
            reviewer="bob",
            approved=True,
            skip_follow_up=True,
        ),
    )
    with pytest.raises(ValueError):
        await perform_review(request)


@pytest.mark.asyncio
async def test_complete_review_requires_approvals() -> None:
    request = CompleteReviewRequest(
        submission=SchemaSubmission(schema_id="schema-1", body="body", iteration=1),
        iteration=1,
        approvals=(
            ReviewOutcome(stage="Review1.a", reviewer="alice", approved=True, comments=None),
            ReviewOutcome(stage="Review1.b", reviewer="bob", approved=False, comments=None),
        ),
    )
    with pytest.raises(ValueError):
        await complete_review(request)
