"""Live Supabase operations (12 sections 2/8). OPT-IN ONLY.

Skipped unless LIVE_DB_TESTS=1, so the default suite never touches hosted
infrastructure. Creates clearly-labeled synthetic rows, asserts real
persistence/constraints, and deletes everything it created — then proves
the leftovers are gone. Never touches pre-existing rows.
"""
import os
import uuid

import pytest

live = pytest.mark.skipif(os.getenv("LIVE_DB_TESTS") != "1",
                          reason="opt-in live Supabase test; set LIVE_DB_TESTS=1")

TAG = uuid.uuid4().hex[:8]
EMAIL = f"livetest-{TAG}@example.com"
FNAME = f"LIVETEST-{TAG}.pdf"


@live
def test_live_crud_isolated_with_cleanup():
    from app.config import get_settings
    from app.database import init_supabase

    # conftest.py deliberately blanks Supabase settings for isolation, so
    # this opt-in test loads backend/.env itself (values never printed).
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    saved = {}
    try:
        with open(env_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip()
                    if key.startswith(("SUPABASE_", "DATABASE_")):
                        saved[key] = os.environ.get(key)
                        os.environ[key] = value
        get_settings.cache_clear()
        settings = get_settings()
        if not settings.supabase_configured:
            pytest.skip("supabase not configured in backend/.env")
        client = init_supabase()
    finally:
        for key, old in saved.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        get_settings.cache_clear()
    uid = doc = rec = task = None
    try:
        uid = client.table("users").insert(
            {"name": "Live Test", "email": EMAIL, "role": "operator", "status": "active"}
        ).execute().data[0]["id"]
        doc = client.table("documents").insert(
            {"file_name": FNAME, "file_type": "application/pdf", "file_size": 42,
             "checksum": "livetest-" + TAG, "storage_path": "livetest/none.pdf",
             "uploaded_by": uid}
        ).execute().data[0]["id"]
        rec = client.table("land_records").insert(
            {"document_id": doc, "status": "DRAFT", "owner_name": "Live Owner",
             "survey_number": "LT/1", "area": "3.5", "area_unit": "hectare",
             "village": "Demo Village", "tehsil": "Demo Tehsil", "district": "Demo District"}
        ).execute().data[0]["id"]
        back = client.table("land_records").select("*").eq("id", rec).execute().data[0]
        assert back["owner_name"] == "Live Owner" and str(back["area"]) == "3.5"
        client.table("land_records").update({"area": "4.0"}).eq("id", rec).execute()
        assert str(client.table("land_records").select("area").eq("id", rec).execute().data[0]["area"]) == "4.0"

        # FK RESTRICT: a document with a record cannot be deleted.
        with pytest.raises(Exception):
            client.table("documents").delete().eq("id", doc).execute()
        assert client.table("land_records").select("id").eq("id", rec).execute().data

        task = client.table("review_tasks").insert(
            {"land_record_id": rec, "status": "PENDING", "priority": "MEDIUM", "reason": "live test"}
        ).execute().data[0]["id"]
        client.table("audit_logs").insert(
            {"user_id": uid, "entity_type": "land_record", "entity_id": rec,
             "action": "LIVE_TEST", "metadata": {}}
        ).execute()
        assert client.table("audit_logs").select("id").eq("entity_id", rec).execute().data
    finally:
        if rec:
            client.table("audit_logs").delete().eq("entity_id", rec).execute()
            client.table("review_tasks").delete().eq("land_record_id", rec).execute()
            client.table("land_records").delete().eq("id", rec).execute()
        if doc:
            client.table("documents").delete().eq("id", doc).execute()
        if uid:
            client.table("users").delete().eq("id", uid).execute()
    assert client.table("users").select("id").eq("email", EMAIL).execute().data == []
    assert client.table("documents").select("id").eq("file_name", FNAME).execute().data == []
