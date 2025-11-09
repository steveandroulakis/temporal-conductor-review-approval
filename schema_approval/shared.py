"""Shared data models for the schema approval workflow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

ReviewStageName = Literal["Review1.a", "Review1.b", "Review2", "Review3"]


@dataclass(frozen=True)
class ReviewDecisionPlan:
    """Plan describing a single reviewer's decision.

    Attributes:
        reviewer: Human readable reviewer identifier.
        approved: Flag indicating whether the reviewer approved the submission.
        comments: Optional contextual message recorded by the reviewer.
        skip_follow_up: When ``True`` the reviewer decided no additional review is
            required. This flag is only meaningful for the second review stage
            (``"Review2"``).
    """

    reviewer: str
    approved: bool
    comments: str | None = None
    skip_follow_up: bool = False


@dataclass(frozen=True)
class ReviewRoundPlan:
    """Describes the expected outcomes for a single review iteration."""

    schema_id: str
    schema_body: str
    review1_primary: ReviewDecisionPlan
    review1_secondary: ReviewDecisionPlan
    review2: ReviewDecisionPlan
    requires_review3: bool
    review3: ReviewDecisionPlan | None = None

    def __post_init__(self) -> None:
        if self.requires_review3 and self.review3 is None:
            raise ValueError(
                "review3 decision must be provided when requires_review3 is True"
            )
        if not self.requires_review3 and self.review3 is not None:
            raise ValueError(
                "review3 decision cannot be provided when requires_review3 is False"
            )


@dataclass(frozen=True)
class SchemaApprovalInput:
    """Workflow input describing every planned review iteration."""

    rounds: Sequence[ReviewRoundPlan]

    def __post_init__(self) -> None:
        if not self.rounds:
            raise ValueError("At least one review round must be provided")


@dataclass(frozen=True)
class SchemaSubmission:
    """Details about an uploaded schema submission."""

    schema_id: str
    body: str
    iteration: int


@dataclass(frozen=True)
class ReviewRequest:
    """Request object provided to the review activities."""

    stage: ReviewStageName
    iteration: int
    decision: ReviewDecisionPlan


@dataclass(frozen=True)
class ReviewOutcome:
    """Outcome returned by the review activities."""

    stage: ReviewStageName
    reviewer: str
    approved: bool
    comments: str | None
    skip_additional_review: bool = False

    @property
    def requires_follow_up(self) -> bool:
        """Return ``True`` when a subsequent review stage must be executed."""

        return not self.skip_additional_review


@dataclass(frozen=True)
class CompleteReviewRequest:
    """Input for the final completion activity."""

    submission: SchemaSubmission
    iteration: int
    approvals: Sequence[ReviewOutcome]

    def ensure_all_approved(self) -> None:
        """Validate that all review outcomes represent approvals."""

        disapprovals = [outcome for outcome in self.approvals if not outcome.approved]
        if disapprovals:
            reviewers = ", ".join(outcome.reviewer for outcome in disapprovals)
            raise ValueError(
                "Cannot complete review when some reviewers rejected the schema: "
                f"{reviewers}"
            )


@dataclass(frozen=True)
class CompletionReport:
    """Represents the final approval summary."""

    submission: SchemaSubmission
    iteration: int
    approved: bool
    summary: str


@dataclass(frozen=True)
class ReviewIterationResult:
    """Represents the outcome of a single review iteration."""

    iteration: int
    submission: SchemaSubmission
    primary_review: ReviewOutcome
    secondary_review: ReviewOutcome
    second_level_review: ReviewOutcome | None
    final_review: ReviewOutcome | None
    approved: bool


@dataclass(frozen=True)
class SchemaApprovalResult:
    """Workflow result that includes the final approval and iteration history."""

    final_report: CompletionReport
    history: Sequence[ReviewIterationResult]

    def completed_iterations(self) -> Iterable[ReviewIterationResult]:
        """Yield each recorded review iteration."""

        return iter(self.history)
