"""Document persistence. Supabase implementation uses the service_role
client; tests substitute an in-memory store via dependency_overrides.
"""
from typing import Any, Protocol

from fastapi import Request

from ..database import require_db
from ..db_errors import classify_db_error
from ..errors import AppError


class DocumentStore(Protocol):
    def create(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def get(self, document_id: str) -> dict[str, Any] | None: ...
    def update_status(self, document_id: str, status: str) -> dict[str, Any]: ...
    def claim_for_processing(self, document_id: str) -> bool: ...


class SupabaseDocumentStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def create(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("documents").insert(row).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Document store", action="documents.create") from exc
        rows = result.data or []
        if not rows:
            raise AppError(503, "DATABASE_UNAVAILABLE", "Document store did not return the created record.")
        return rows[0]

    def get(self, document_id: str) -> dict[str, Any] | None:
        try:
            result = (
                self.client.table("documents").select("*").eq("id", document_id).limit(1).execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Document store", action="documents.get") from exc
        rows = result.data or []
        return rows[0] if rows else None

    def claim_for_processing(self, document_id: str) -> bool:
        """Atomically move a document into PROCESSING. True == this caller won.

        A single conditional UPDATE (`... WHERE id = ? AND status <> 'PROCESSING'`)
        is serialized by Postgres, so two concurrent /process requests cannot both
        succeed. Reading the status and then updating it is NOT equivalent: the
        pipeline sets PROCESSING from a background task, so a read-then-act guard
        stays open until the worker starts and both requests get through.
        """
        try:
            result = (
                self.client.table("documents")
                .update({"processing_status": "PROCESSING"})
                .eq("id", document_id)
                .neq("processing_status", "PROCESSING")
                .execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Document store", action="documents.claim_for_processing") from exc
        return bool(result.data)

    def update_status(self, document_id: str, status: str) -> dict[str, Any]:
        try:
            result = (
                self.client.table("documents").update({"processing_status": status}).eq("id", document_id).execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Document store", action="documents.update_status") from exc
        rows = result.data or []
        if not rows:
            raise AppError(404, "DOCUMENT_NOT_FOUND", "The requested document was not found.")
        return rows[0]


def get_document_store(request: Request) -> DocumentStore:
    return SupabaseDocumentStore(require_db(request))
