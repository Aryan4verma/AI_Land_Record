"""Review workflow persistence. Supabase implementations use the
service_role client; tests substitute in-memory stores via
dependency_overrides. Table shapes follow 09_DATABASE_SCHEMA.
"""
from typing import Any, Protocol

from fastapi import Request

from ..database import require_db
from ..db_errors import classify_db_error
from ..errors import AppError


def _one(result: Any, not_found_code: str, not_found_message: str) -> dict[str, Any]:
    rows = result.data or []
    if not rows:
        raise AppError(404, not_found_code, not_found_message)
    return rows[0]


class RecordStore(Protocol):
    def get_record(self, record_id: str) -> dict[str, Any] | None: ...
    def get_record_by_document(self, document_id: str) -> dict[str, Any] | None: ...
    def create_record(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def update_record(self, record_id: str, patch: dict[str, Any]) -> dict[str, Any]: ...
    def list_extracted_fields(self, record_id: str) -> list[dict[str, Any]]: ...
    def replace_extracted_fields(self, record_id: str, rows: list[dict[str, Any]]) -> None: ...
    def replace_validation_results(self, record_id: str, rows: list[dict[str, Any]]) -> None: ...
    def list_validation_results(self, record_id: str) -> list[dict[str, Any]]: ...
    def save_correction(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def get_document(self, document_id: str) -> dict[str, Any] | None: ...
    def list_reference_rows(self) -> list[dict[str, Any]]: ...
    def replace_ocr_results(self, document_id: str, rows: list[dict[str, Any]]) -> None: ...
    def list_record_summaries(self) -> list[dict[str, Any]]: ...
    def persist_processing_result(self, **kwargs: Any) -> dict[str, Any]: ...


class ReviewStore(Protocol):
    def create_task(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def get_task(self, task_id: str) -> dict[str, Any] | None: ...
    def list_tasks(self, status: str | None, assigned_to: str | None) -> list[dict[str, Any]]: ...
    def list_tasks_page(
        self, status: str | None, assigned_to: str | None, priority: str | None,
        limit: int, offset: int,
    ) -> tuple[list[dict[str, Any]], int]: ...
    def update_task(self, task_id: str, patch: dict[str, Any]) -> dict[str, Any]: ...
    def open_tasks_for_record(self, record_id: str) -> list[dict[str, Any]]: ...


class AuditStore(Protocol):
    def append(self, entry: dict[str, Any]) -> dict[str, Any]: ...
    def list_for(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]: ...
    def list_for_page(
        self, entity_type: str, entity_id: str, limit: int, offset: int,
    ) -> tuple[list[dict[str, Any]], int]: ...


class SupabaseRecordStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def _query(self, table: str, action: str) -> Any:
        try:
            return getattr(self.client.table(table), action)
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews._query") from exc

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        try:
            result = self.client.table("land_records").select("*").eq("id", record_id).limit(1).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.get_record") from exc
        rows = result.data or []
        return rows[0] if rows else None

    def update_record(self, record_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("land_records").update(patch).eq("id", record_id).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.update_record") from exc
        return _one(result, "RECORD_NOT_FOUND", "The requested record was not found.")

    def list_extracted_fields(self, record_id: str) -> list[dict[str, Any]]:
        try:
            result = (
                self.client.table("extracted_fields").select("*").eq("land_record_id", record_id).execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.list_extracted_fields") from exc
        return result.data or []

    def replace_validation_results(self, record_id: str, rows: list[dict[str, Any]]) -> None:
        try:
            self.client.table("validation_results").delete().eq("land_record_id", record_id).execute()
            if rows:
                self.client.table("validation_results").insert(rows).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.replace_validation_results") from exc

    def save_correction(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("field_corrections").insert(row).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.save_correction") from exc
        return _one(result, "DATABASE_UNAVAILABLE", "Correction was not stored.")

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        try:
            result = self.client.table("documents").select("*").eq("id", document_id).limit(1).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.get_document") from exc
        rows = result.data or []
        return rows[0] if rows else None

    def list_reference_rows(self) -> list[dict[str, Any]]:
        try:
            result = (
                self.client.table("reference_data")
                .select("id,reference_type,code,name,parent_id,version,status")
                .eq("status", "active")
                .execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.list_reference_rows") from exc
        return result.data or []

    def replace_ocr_results(self, document_id: str, rows: list[dict[str, Any]]) -> None:
        try:
            self.client.table("ocr_results").delete().eq("document_id", document_id).execute()
            if rows:
                self.client.table("ocr_results").insert(rows).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.replace_ocr_results") from exc

    def persist_processing_result(self, **kwargs: Any) -> dict[str, Any]:
        """Commit the final processing result through one PostgreSQL function.

        OCR/AI work and the initial RUNNING/PROCESSING state are deliberately
        outside this call.  The RPC owns the final result unit so a failure in
        any child insert, review creation, state update, or completion audit
        rolls back the complete unit.
        """
        try:
            result = self.client.rpc("persist_processing_result", kwargs).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.persist_processing_result") from exc
        data = result.data
        if isinstance(data, list):
            data = data[0] if data else None
        if not isinstance(data, dict) or not data.get("record_id"):
            raise AppError(503, "DATABASE_UNAVAILABLE", "Processing result was not committed.")
        return data

    def list_record_summaries(self) -> list[dict[str, Any]]:
        try:
            result = (
                self.client.table("land_records")
                .select("id,document_id,survey_number,village,owner_name")
                .execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.list_record_summaries") from exc
        return result.data or []

    def get_record_by_document(self, document_id: str) -> dict[str, Any] | None:
        try:
            result = (
                self.client.table("land_records").select("*").eq("document_id", document_id).limit(1).execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.get_record_by_document") from exc
        rows = result.data or []
        return rows[0] if rows else None

    def create_record(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("land_records").insert(row).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.create_record") from exc
        return _one(result, "DATABASE_UNAVAILABLE", "Record was not created.")

    def replace_extracted_fields(self, record_id: str, rows: list[dict[str, Any]]) -> None:
        try:
            self.client.table("extracted_fields").delete().eq("land_record_id", record_id).execute()
            if rows:
                self.client.table("extracted_fields").insert(rows).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.replace_extracted_fields") from exc

    def list_validation_results(self, record_id: str) -> list[dict[str, Any]]:
        try:
            result = (
                self.client.table("validation_results").select("*").eq("land_record_id", record_id).execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Record store", action="reviews.list_validation_results") from exc
        return result.data or []


class SupabaseReviewStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def create_task(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("review_tasks").insert(row).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Review store", action="reviews.create_task") from exc
        return _one(result, "DATABASE_UNAVAILABLE", "Review task was not created.")

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        try:
            result = self.client.table("review_tasks").select("*").eq("id", task_id).limit(1).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Review store", action="reviews.get_task") from exc
        rows = result.data or []
        return rows[0] if rows else None

    def list_tasks(self, status: str | None, assigned_to: str | None) -> list[dict[str, Any]]:
        try:
            query = self.client.table(
                "review_tasks"
            ).select("id,land_record_id,assigned_to,status,priority,reason,created_at,completed_at")
            if status:
                query = query.eq("status", status)
            if assigned_to:
                query = query.eq("assigned_to", assigned_to)
            result = query.order("created_at", desc=True).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Review store", action="reviews.list_tasks") from exc
        return result.data or []

    def list_tasks_page(
        self, status: str | None, assigned_to: str | None, priority: str | None,
        limit: int, offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        try:
            query = self.client.table(
                "review_tasks"
            ).select("id,land_record_id,assigned_to,status,priority,reason,created_at,completed_at", count="exact")
            if status:
                query = query.eq("status", status)
            if assigned_to:
                query = query.eq("assigned_to", assigned_to)
            if priority:
                query = query.eq("priority", priority)
            result = (
                query.order("created_at", desc=True)
                .order("id", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data or [], int(result.count or 0)
        except Exception as exc:
            if getattr(exc, "code", "") == "PGRST103":
                # Keep the response useful for a page beyond the end without
                # hiding other database failures.
                try:
                    count_query = self.client.table("review_tasks").select("id", count="exact")
                    if status:
                        count_query = count_query.eq("status", status)
                    if assigned_to:
                        count_query = count_query.eq("assigned_to", assigned_to)
                    if priority:
                        count_query = count_query.eq("priority", priority)
                    counted = count_query.limit(1).execute()
                    return [], int(counted.count or 0)
                except Exception as inner:
                    raise classify_db_error(
                        inner, subject="Review store", action="reviews.list_tasks_page.count"
                    ) from inner
            raise classify_db_error(
                exc, subject="Review store", action="reviews.list_tasks_page"
            ) from exc

    def update_task(self, task_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("review_tasks").update(patch).eq("id", task_id).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Review store", action="reviews.update_task") from exc
        return _one(result, "REVIEW_NOT_FOUND", "The requested review was not found.")

    def open_tasks_for_record(self, record_id: str) -> list[dict[str, Any]]:
        try:
            result = (
                self.client.table("review_tasks")
                .select("*")
                .eq("land_record_id", record_id)
                .in_("status", ["PENDING", "IN_REVIEW"])
                .execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Review store", action="reviews.open_tasks_for_record") from exc
        return result.data or []


class SupabaseAuditStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def append(self, entry: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table("audit_logs").insert(entry).execute()
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Audit store", action="reviews.append") from exc
        return _one(result, "DATABASE_UNAVAILABLE", "Audit entry was not stored.")

    def list_for(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
        try:
            result = (
                self.client.table("audit_logs")
                .select("*")
                .eq("entity_type", entity_type)
                .eq("entity_id", entity_id)
                .order("timestamp", desc=False)
                .execute()
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Audit store", action="reviews.list_for") from exc
        return result.data or []

    def list_for_page(
        self, entity_type: str, entity_id: str, limit: int, offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        try:
            result = (
                self.client.table("audit_logs")
                .select("*", count="exact")
                .eq("entity_type", entity_type)
                .eq("entity_id", entity_id)
                .order("timestamp", desc=False)
                .order("id", desc=False)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data or [], int(result.count or 0)
        except Exception as exc:
            if getattr(exc, "code", "") == "PGRST103":
                try:
                    counted = (
                        self.client.table("audit_logs")
                        .select("id", count="exact")
                        .eq("entity_type", entity_type)
                        .eq("entity_id", entity_id)
                        .limit(1)
                        .execute()
                    )
                    return [], int(counted.count or 0)
                except Exception as inner:
                    raise classify_db_error(
                        inner, subject="Audit store", action="reviews.list_for_page.count"
                    ) from inner
            raise classify_db_error(
                exc, subject="Audit store", action="reviews.list_for_page"
            ) from exc


def get_record_store(request: Request) -> RecordStore:
    return SupabaseRecordStore(require_db(request))


def get_review_store(request: Request) -> ReviewStore:
    return SupabaseReviewStore(require_db(request))


def get_audit_store(request: Request) -> AuditStore:
    return SupabaseAuditStore(require_db(request))
