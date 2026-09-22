"""Read-only deployment checks; no provider inference call is made."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_tesseract() -> None:
    from ai.ocr.script_detect import tessdata_dir
    from ai.ocr.tesseract_adapter import find_binary

    binary = find_binary()
    if not (shutil.which(binary) or Path(binary).is_file()):
        raise RuntimeError("Tesseract executable was not found")
    env = os.environ.copy()
    data_dir = tessdata_dir()
    if data_dir:
        env["TESSDATA_PREFIX"] = data_dir
    languages = subprocess.check_output(
        [binary, "--list-langs"], text=True, stderr=subprocess.STDOUT, env=env
    )
    missing = {"eng", "hin", "guj"} - set(languages.split())
    if missing:
        raise RuntimeError(f"Tesseract language data missing: {', '.join(sorted(missing))}")
    print("tesseract: ok (eng, hin, guj)")


def check_app() -> None:
    from app.ai.service import get_ai_service
    from app.config import get_settings
    from app.main import app

    settings = get_settings()
    if not settings.frontend_origin_list or "*" in settings.frontend_origin_list:
        raise RuntimeError("FRONTEND_ORIGINS must contain explicit origins")
    if not settings.auth_secret:
        raise RuntimeError("AUTH_SECRET is not configured")
    service = get_ai_service(settings)
    print(f"fastapi: ok ({app.title})")
    print(f"ai: ok ({service.route_chain})")


def check_supabase() -> None:
    from app.database import init_supabase, ping_database

    client = init_supabase()
    if client is None or not ping_database(client):
        raise RuntimeError("Supabase connection check failed")
    print("supabase: ok")


def check_http(url: str) -> None:
    import httpx

    response = httpx.get(url.rstrip("/") + "/health", timeout=10)
    response.raise_for_status()
    print("health: ok")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="deployed backend base URL; performs GET /health")
    parser.add_argument("--supabase", action="store_true", help="run a read-only Supabase ping")
    args = parser.parse_args()
    check_tesseract()
    check_app()
    if args.supabase:
        check_supabase()
    if args.url:
        check_http(args.url)
    print("deployment smoke checks: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
