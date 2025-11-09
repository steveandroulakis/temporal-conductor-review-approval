"""Worker entrypoint for the schema approval workflow."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import complete_review, perform_review, upload_schema
from .workflow import SchemaApprovalWorkflow

_TASK_QUEUE = "schema-approval-task-queue"
_PID_FILE = Path("worker.pid")


async def main() -> None:
    """Run the Temporal worker until interrupted."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = await Client.connect(os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))
    worker = Worker(
        client,
        task_queue=_TASK_QUEUE,
        workflows=[SchemaApprovalWorkflow],
        activities=[upload_schema, perform_review, complete_review],
    )

    _PID_FILE.write_text(str(os.getpid()))
    logging.info("Worker started with PID %s", os.getpid())

    try:
        await worker.run()
    finally:
        logging.info("Worker shutting down")
        try:
            _PID_FILE.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
