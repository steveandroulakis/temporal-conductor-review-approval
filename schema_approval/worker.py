#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["temporalio>=1.7.0"]
# ///
"""Worker process that hosts the schema approval workflow."""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from schema_approval.activities import (
    dispatch_review_request,
    finalize_review,
    record_revision_request,
    upload_schema,
)
from schema_approval.shared import DEFAULT_TASK_QUEUE
from schema_approval.workflow import SchemaApprovalWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=DEFAULT_TASK_QUEUE,
        workflows=[SchemaApprovalWorkflow],
        activities=[
            upload_schema,
            dispatch_review_request,
            record_revision_request,
            finalize_review,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
