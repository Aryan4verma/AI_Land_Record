"""Records, dashboard and mock-integration endpoints (10 sections 8, 10, 11)."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from ..auth.dependencies import get_current_user, require_role
from ..reviews.stores import RecordStore, get_record_store
from .schemas import (
    DashboardProcessingOut,
    DashboardSummaryOut,
    DashboardValidationOut,
    MockLrmsIn,
    MockLrmsOut,
    RecordDetailOut,
    RecordExportOut,
    RecordSearchOut,
)
from .service import ALLOWED_STATUSES, collect_filters, export_record, mock_lrms_submit, record_detail
from .stores import DashboardStore, RecordQueryStore, get_dashboard_store, get_record_query_store

router = APIRouter(tags=["records"])


@router.get("/api/v1/records", response_model=RecordSearchOut)
def search_records(
    request: Request,
    owner: str | None = Query(None, max_length=200),
    survey_number: str | None = Query(None, max_length=64),
    khasra_number: str | None = Query(None, max_length=64),
    village: str | None = Query(None, max_length=200),
    tehsil: str | None = Query(None, max_length=200),
    district: str | None = Query(None, max_length=200),
    status: str | None = Query(None, max_length=32),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    store: RecordQueryStore = Depends(get_record_query_store),
) -> dict:
    _ = (request, user)
    if status is not None and status not in ALLOWED_STATUSES:
        from ..errors import AppError

        raise AppError(422, "INVALID_STATUS", f"Status must be one of: {', '.join(ALLOWED_STATUSES)}.")
    items, total = store.search_records(
        collect_filters(owner, survey_number, khasra_number, village, tehsil, district, status), page, limit)
    return {"items": items, "page": page, "limit": limit, "total": total}


@router.get("/api/v1/records/{record_id}", response_model=RecordDetailOut)
def get_record(
    record_id: UUID,
    request: Request,
    user: dict = Depends(get_current_user),
    records: RecordStore = Depends(get_record_store),
) -> dict:
    _ = (request, user)
    return record_detail(str(record_id), records)


@router.get("/api/v1/records/{record_id}/export", response_model=RecordExportOut)
def export_record_endpoint(
    record_id: UUID,
    request: Request,
    user: dict = Depends(get_current_user),
    records: RecordStore = Depends(get_record_store),
) -> dict:
    _ = (request, user)
    return export_record(str(record_id), records)


@router.get("/api/v1/dashboard/summary", response_model=DashboardSummaryOut)
def dashboard_summary(
    request: Request,
    user: dict = Depends(get_current_user),
    store: DashboardStore = Depends(get_dashboard_store),
) -> dict:
    _ = (request, user)
    return store.summary()


@router.get("/api/v1/dashboard/processing", response_model=DashboardProcessingOut)
def dashboard_processing(
    request: Request,
    user: dict = Depends(get_current_user),
    store: DashboardStore = Depends(get_dashboard_store),
) -> dict:
    _ = (request, user)
    return store.processing()


@router.get("/api/v1/dashboard/validation", response_model=DashboardValidationOut)
def dashboard_validation(
    request: Request,
    user: dict = Depends(get_current_user),
    store: DashboardStore = Depends(get_dashboard_store),
) -> dict:
    _ = (request, user)
    return store.validation()


@router.post("/api/v1/integrations/mock-lrms", response_model=MockLrmsOut)
def mock_lrms(
    body: MockLrmsIn,
    request: Request,
    user: dict = Depends(require_role("operator")),
    records: RecordStore = Depends(get_record_store),
) -> dict:
    _ = (request, user)
    return mock_lrms_submit(str(body.record_id), records)
