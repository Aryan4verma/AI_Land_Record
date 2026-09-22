"""Regression checks for bounded database access paths."""

from types import SimpleNamespace

from app.processing.stores import SupabaseJobStore
from app.reviews.stores import SupabaseReviewStore


class _Chain:
    def __init__(self):
        self.select_args = None
        self.filters = []
        self.orderings = []
        self.limit_value = None

    def select(self, *args, **kwargs):
        self.select_args = (args, kwargs)
        return self

    def eq(self, *args):
        self.filters.append(("eq", args))
        return self

    def in_(self, *args):
        self.filters.append(("in", args))
        return self

    def order(self, *args, **kwargs):
        self.orderings.append((args, kwargs))
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        return SimpleNamespace(data=[{"id": "job-1", "status": "RUNNING"}], count=None)


class _Client:
    def __init__(self):
        self.chains = []

    def table(self, _name):
        chain = _Chain()
        self.chains.append(chain)
        return chain


def test_processing_status_reads_are_bounded_to_one_row():
    client = _Client()
    store = SupabaseJobStore(client)

    latest = store.latest_job_for_document("doc-1")
    assert latest["id"] == "job-1"
    assert client.chains[-1].limit_value == 1
    assert client.chains[-1].select_args[0] == ("id,status,error_code,error_message,started_at,completed_at",)

    assert store.has_active_job_for_document("doc-1") is True
    active = client.chains[-1]
    assert active.limit_value == 1
    assert ("in", ("status", ["PENDING", "RUNNING"])) in active.filters
    assert active.select_args[0] == ("id",)


def test_review_queue_projection_does_not_fetch_unneeded_columns():
    client = _Client()
    store = SupabaseReviewStore(client)
    store.list_tasks("PENDING", None)
    selected, _kwargs = client.chains[-1].select_args
    assert selected[0] == "id,land_record_id,assigned_to,status,priority,reason,created_at,completed_at"
    assert "*" not in selected[0]
