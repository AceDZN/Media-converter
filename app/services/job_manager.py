"""Job management with ProcessPoolExecutor for concurrent conversions."""

import asyncio
import logging
from concurrent.futures import Future, ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Represents a conversion job."""

    id: str
    input_path: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    images: List[str] = field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    processing_time_ms: int = 0


class JobManager:
    """
    Manages conversion jobs with in-memory state storage.

    Uses ProcessPoolExecutor for CPU-bound conversion work,
    allowing the async event loop to remain responsive.
    """

    _instance: Optional["JobManager"] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern for shared executor."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.settings = get_settings()
        self._jobs: Dict[str, Job] = {}
        self._futures: Dict[str, Future] = {}
        self._executor: Optional[ProcessPoolExecutor] = None
        self._initialized = True
        logger.info(f"JobManager initialized (max_workers={self.settings.max_workers})")

    def _get_executor(self) -> ProcessPoolExecutor:
        """Get or create the process pool executor."""
        if self._executor is None:
            self._executor = ProcessPoolExecutor(max_workers=self.settings.max_workers)
        return self._executor

    async def submit_job(
        self, job_id: str, input_path: str, converter_func: Callable
    ) -> Job:
        """
        Submit a new conversion job.

        Args:
            job_id: Unique job identifier
            input_path: Path to input file
            converter_func: The sync conversion function to run

        Returns:
            Job instance
        """
        job = Job(id=job_id, input_path=input_path, status=JobStatus.PROCESSING)
        self._jobs[job_id] = job

        # Submit to process pool
        executor = self._get_executor()
        future = executor.submit(converter_func, input_path, job_id)
        self._futures[job_id] = future

        logger.info(f"Job {job_id} submitted for processing")
        return job

    async def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> Optional[Job]:
        """
        Wait for job completion.

        Args:
            job_id: Job identifier
            timeout: Maximum wait time in seconds

        Returns:
            Completed Job or None if not found
        """
        timeout = timeout or self.settings.job_timeout_seconds
        start = datetime.utcnow()

        job = self._jobs.get(job_id)
        if not job:
            return None

        future = self._futures.get(job_id)
        if not future:
            return job

        # Poll for completion
        while not future.done():
            elapsed = (datetime.utcnow() - start).total_seconds()
            if elapsed >= timeout:
                job.status = JobStatus.FAILED
                job.error = f"Job timed out after {timeout}s"
                job.completed_at = datetime.utcnow()
                job.processing_time_ms = int(elapsed * 1000)
                return job

            await asyncio.sleep(0.5)

        # Process result
        try:
            result = future.result(timeout=1)

            if result.success:
                job.status = JobStatus.COMPLETED
                job.images = result.images
                job.progress = 100
            else:
                job.status = JobStatus.FAILED
                job.error = result.error

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            logger.exception(f"Job {job_id} failed with exception")

        job.completed_at = datetime.utcnow()
        job.processing_time_ms = int(
            (job.completed_at - job.created_at).total_seconds() * 1000
        )

        # Clean up future reference
        self._futures.pop(job_id, None)
        logger.info(f"Job {job_id} completed with status: {job.status}")

        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        job = self._jobs.get(job_id)

        # Check if job is still processing and update status
        if job and job.status == JobStatus.PROCESSING:
            future = self._futures.get(job_id)
            if future and future.done():
                # Update job with result
                try:
                    result = future.result(timeout=1)
                    if result.success:
                        job.status = JobStatus.COMPLETED
                        job.images = result.images
                        job.progress = 100
                    else:
                        job.status = JobStatus.FAILED
                        job.error = result.error
                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.error = str(e)

                job.completed_at = datetime.utcnow()
                job.processing_time_ms = int(
                    (job.completed_at - job.created_at).total_seconds() * 1000
                )
                self._futures.pop(job_id, None)

        return job

    async def cleanup_old_jobs(self, max_age_hours: Optional[int] = None) -> int:
        """
        Remove jobs older than max_age_hours.

        Args:
            max_age_hours: Maximum job age in hours

        Returns:
            Number of jobs removed
        """
        max_age = max_age_hours or self.settings.job_ttl_hours
        cutoff = datetime.utcnow() - timedelta(hours=max_age)

        old_jobs = [jid for jid, job in self._jobs.items() if job.created_at < cutoff]

        for jid in old_jobs:
            del self._jobs[jid]
            self._futures.pop(jid, None)

        if old_jobs:
            logger.info(f"Cleaned up {len(old_jobs)} old jobs")

        return len(old_jobs)

    def get_stats(self) -> Dict:
        """Get job manager statistics."""
        statuses = {}
        for job in self._jobs.values():
            statuses[job.status.value] = statuses.get(job.status.value, 0) + 1

        return {
            "total_jobs": len(self._jobs),
            "active_futures": len(self._futures),
            "by_status": statuses,
        }

    def shutdown(self):
        """Gracefully shutdown the executor."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        logger.info("JobManager shutdown complete")


def get_job_manager() -> JobManager:
    """Get the singleton JobManager instance."""
    return JobManager()
