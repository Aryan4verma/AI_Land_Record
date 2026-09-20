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
    def latest_job_for_document(self, document_id: str) -> dict[str, Any] | None: ...
    def has_active_job_for_document(self, document_id: str) -> bool: ...


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

    def latest_job_for_document(self, document_id: str) -> dict[str, Any] | None:
        """Fetch only the row required by the document-status endpoint."""
        try:
            result = (
                self.client.table("processing_jobs")
                .select("id,status,error_code,started_at,completed_at")
                .eq("document_id", document_id)
                .order("created_at", desc=True)
                .order("id", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Job store", action="processing.latest_job_for_document"
            ) from exc
        rows = result.data or []
        return rows[0] if rows else None

    def has_active_job_for_document(self, document_id: str) -> bool:
        """Check the duplicate-claim recovery condition without loading history."""
        try:
            result = (
                self.client.table("processing_jobs")
                .select("id")
                .eq("document_id", document_id)
                .in_("status", ["PENDING", "RUNNING"])
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Job store", action="processing.has_active_job_for_document"
            ) from exc
        return bool(result.data)

    def mark_stale_failed(self) -> int:
        """Fail jobs left RUNNING/PENDING by a previous process lifetime.

        Called once at startup so a restart never leaves jobs (and their
        documents) stuck invisible. Returns the count reconciled.
        """
        try:
            result = self.client.rpc("reconcile_stale_processing_jobs", {}).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Job store", action="processing.mark_stale_failed") from exc
        value = result.data
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, list) and value and isinstance(value[0], int):
            return value[0]
        raise AppError(503, "DATABASE_UNAVAILABLE", "Stale processing jobs could not be reconciled.")


def get_job_store(request: Request) -> JobStore:
    return SupabaseJobStore(require_db(request))
