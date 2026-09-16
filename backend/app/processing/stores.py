"""Processing-job persistence. Supabase implementation; tests override
with an in-memory fake via dependency_overrides.
"""
from typing import Any, Protocol

from fastapi import Request

from ..database import require_db
from ..errors import AppError


class JobStore(Protocol):
    def create_job(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def get_job(self, job_id: str) -> dict[str, Any] | None: ...
    def update_job(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]: ...
    def mark_stale_failed(self) -> int: ...
    def list_jobs_for_document(self, document_id: str) -> list[dict[str, Any]]: ...


class SupabaseJobStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def create_job(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("processing_jobs").insert(row).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Job store", action="processing.create_job") from exc
        rows = result.data or []
        if not rows:
            raise AppError(503, "DATABASE_UNAVAILABLE", "Processing job was not created.")
        return rows[0]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        try:
            result = self.client.table("processing_jobs").select("*").eq("id", job_id).limit(1).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Job store", action="processing.get_job") from exc
        rows = result.data or []
        return rows[0] if rows else None

    def update_job(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("processing_jobs").update(patch).eq("id", job_id).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Job store", action="processing.update_job") from exc
        rows = result.data or []
        if not rows:
            raise AppError(404, "JOB_NOT_FOUND", "The requested processing job was not found.")
        return rows[0]

    def list_jobs_for_document(self, document_id: str) -> list[dict[str, Any]]:
        try:
            result = (
                self.client.table("processing_jobs")
                .select("*")
                .eq("document_id", document_id)
                .order("created_at", desc=True)
                .execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Job store", action="processing.list_jobs_for_document") from exc
        return result.data or []

    def mark_stale_failed(self) -> int:
        """Fail jobs left RUNNING/PENDING by a previous process lifetime.

        Called once at startup so a restart never leaves jobs (and their
        documents) stuck invisible. Returns the count reconciled.
        """
        from datetime import datetime, timezone

        try:
            result = (
                self.client.table("processing_jobs")
                .update({"status": "FAILED", "completed_at": datetime.now(timezone.utc).isoformat(),
                         "error_code": "SERVER_RESTARTED",
                         "error_message": "Server restarted while this job was running."})
                .in_("status", ["PENDING", "RUNNING"])
                .execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Job store", action="processing.mark_stale_failed") from exc
        return len(result.data or [])


def get_job_store(request: Request) -> JobStore:
    return SupabaseJobStore(require_db(request))
