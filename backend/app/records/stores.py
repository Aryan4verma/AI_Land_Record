"""Search + dashboard persistence. Supabase implementations aggregate in
Python (MVP scale); tests substitute canned aggregates.
"""
from typing import Any, Protocol

from fastapi import Request

from ..database import require_db
from ..errors import AppError

SEARCHABLE = ("owner_name", "survey_number", "khasra_number", "village", "tehsil", "district", "status")


class RecordQueryStore(Protocol):
    def search_records(self, filters: dict[str, str], page: int, limit: int) -> tuple[list[dict], int]: ...


class DashboardStore(Protocol):
    def summary(self) -> dict[str, Any]: ...
    def processing(self) -> dict[str, Any]: ...
    def validation(self) -> dict[str, Any]: ...


def _fetch(client: Any, table: str, columns: str) -> list[dict]:
    try:
        return client.table(table).select(columns).execute().data or []
    except Exception as exc:
        raise classify_db_error(
            exc, subject="Store", action="records._fetch") from exc


def _count_by(rows: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "UNKNOWN")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so search input matches literally.

    PostgreSQL uses backslash as the default LIKE escape character, so
    user-supplied %/_/\\ must be escaped — otherwise a search for "%"
    would match every record.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SupabaseRecordQueryStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def _filtered(self, filters: dict[str, str], select: str = "*"):
        query = self.client.table("land_records").select(select, count="exact")
        mapping = {"owner": "owner_name", "survey_number": "survey_number",
                   "khasra_number": "khasra_number", "village": "village",
                   "tehsil": "tehsil", "district": "district"}
        for param, column in mapping.items():
            if filters.get(param):
                query = query.ilike(column, f"%{_escape_like(filters[param])}%")
        if filters.get("status"):
            query = query.eq("status", filters["status"])
        return query

    def search_records(self, filters: dict[str, str], page: int, limit: int) -> tuple[list[dict], int]:
        offset = (page - 1) * limit
        try:
            result = self._filtered(filters).order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
            return result.data or [], result.count or 0
        except Exception as exc:
            if not _is_unsatisfiable_range(exc):
                raise classify_db_error(
                    exc, subject="Record store", action="records.search_records") from exc
            # Page beyond the last result: empty items, honest total.
            # NOTE: build a fresh query — postgrest builders allow select() only once.
            try:
                counted = self._filtered(filters, select="id").limit(1).execute()
            except Exception as inner:
                raise classify_db_error(
                    inner, subject="Record store", action="records.search_records.count") from inner
            return [], counted.count or 0


def _is_unsatisfiable_range(exc: Exception) -> bool:
    """PostgREST answers 416 (PGRST103) when offset exceeds the row count."""
    return getattr(exc, "code", "") == "PGRST103" or "Requested range not satisfiable" in str(exc)


class SupabaseDashboardStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def summary(self) -> dict[str, Any]:
        documents = _fetch(self.client, "documents", "processing_status")
        records = _fetch(self.client, "land_records", "status")
        tasks = _fetch(self.client, "review_tasks", "status")
        confidences = [
            float(row["confidence"]) for row in _fetch(self.client, "extracted_fields", "confidence")
            if row.get("confidence") is not None
        ]
        return {
            "documents_total": len(documents),
            "documents_by_status": _count_by(documents, "processing_status"),
            "records_by_status": _count_by(records, "status"),
            "open_reviews": sum(1 for task in tasks if task.get("status") in ("PENDING", "IN_REVIEW")),
            "average_confidence": (sum(confidences) / len(confidences)) if confidences else None,
        }

    def processing(self) -> dict[str, Any]:
        try:
            jobs = (
                self.client.table("processing_jobs")
                .select("id,document_id,status,pipeline_version,started_at,completed_at,error_code")
                .order("created_at", desc=True)
                .limit(10)
                .execute()
                .data or []
            )
        except Exception as exc:
            raise classify_db_error(
                exc, subject="Store", action="records.processing") from exc
        return {"jobs_by_status": _count_by(jobs, "status"), "recent_jobs": jobs}

    def validation(self) -> dict[str, Any]:
        issues = _fetch(self.client, "validation_results", "severity,status")
        documents = _fetch(self.client, "documents", "processing_status")
        return {
            "issues_by_severity": _count_by(issues, "severity"),
            "issues_by_status": _count_by(issues, "status"),
            "blocked_documents": sum(1 for doc in documents if doc.get("processing_status") == "VALIDATION_FAILED"),
        }


def get_record_query_store(request: Request) -> RecordQueryStore:
    return SupabaseRecordQueryStore(require_db(request))


def get_dashboard_store(request: Request) -> DashboardStore:
    return SupabaseDashboardStore(require_db(request))
