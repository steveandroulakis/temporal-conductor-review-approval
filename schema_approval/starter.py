#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["temporalio>=1.7.0"]
# ///
"""Utility for starting the schema approval workflow."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime

from temporalio.client import Client

from schema_approval.shared import (
    DEFAULT_TASK_QUEUE,
    SchemaApprovalWorkflowInput,
    SchemaSubmission,
)
from schema_approval.workflow import SchemaApprovalWorkflow


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema_id", help="Identifier of the schema being reviewed")
    parser.add_argument(
        "--version",
        type=int,
        default=1,
        help="Submission version number (increment on resubmission)",
    )
    parser.add_argument(
        "--description",
        default="New schema submission",
        help="Description shown to reviewers",
    )
    parser.add_argument(
        "--content-uri",
        default="https://example.com/schemas/latest.json",
        help="Location where reviewers can read the schema",
    )
    parser.add_argument(
        "--submitted-by",
        default="service-owner@example.com",
        help="Email of the submitter",
    )
    parser.add_argument(
        "--reviewer-a",
        default="alice@example.com",
        help="Reviewer handling Review1.a",
    )
    parser.add_argument(
        "--reviewer-b",
        default="bob@example.com",
        help="Reviewer handling Review1.b",
    )
    parser.add_argument(
        "--senior-reviewer",
        default="carol@example.com",
        help="Reviewer handling Review2",
    )
    parser.add_argument(
        "--compliance-reviewer",
        default="dave@example.com",
        help="Reviewer handling Review3 when required",
    )
    parser.add_argument(
        "--workflow-id",
        default=None,
        help="Override the generated workflow id",
    )
    return parser


async def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    submission = SchemaSubmission(
        schema_id=args.schema_id,
        version=args.version,
        description=args.description,
        content_uri=args.content_uri,
        submitted_by=args.submitted_by,
    )
    config = SchemaApprovalWorkflowInput(
        initial_submission=submission,
        stage_one_reviewers=(args.reviewer_a, args.reviewer_b),
        stage_two_reviewer=args.senior_reviewer,
        stage_three_reviewer=args.compliance_reviewer,
    )

    workflow_id = args.workflow_id or (
        f"schema-approval-{submission.schema_id}-v{submission.version}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

    client = await Client.connect("localhost:7233")
    handle = await client.start_workflow(
        SchemaApprovalWorkflow.run,
        config,
        id=workflow_id,
        task_queue=DEFAULT_TASK_QUEUE,
    )
    logging.info("Started workflow %s (run %s)", handle.id, handle.run_id)
    logging.info(
        "Send review signals with: temporal workflow signal --workflow-id %s --name record_review_decision",
        handle.id,
    )
    logging.info(
        "Signal payload example: '{\"stage\": \"Review1.a\", \"reviewer\": \"%s\", \"submission_version\": %s, \"approved\": true}'",
        args.reviewer_a,
        submission.version,
    )
    logging.info(
        "Resubmit with: temporal workflow signal --workflow-id %s --name submit_schema --input '{\"schema_id\": \"%s\", \"version\": %s, \"description\": \"Revised\", \"content_uri\": \"%s\", \"submitted_by\": \"%s\"}'",
        handle.id,
        submission.schema_id,
        submission.version + 1,
        submission.content_uri,
        submission.submitted_by,
    )


if __name__ == "__main__":
    asyncio.run(main())
