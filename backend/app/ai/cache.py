"""Repeat-extraction cache (06 section 6).

A previous result is reused only when the full processing identity
matches: document checksum (or OCR-text hash fallback), pipeline version,
provider+model chain, and prompt/schema versions. Anything else — a new
document, a new model, a new prompt — is a cache miss by construction,
so stale results can never leak across configurations.

Bounded (LRU, max entries) and time-limited (TTL). Thread-safety is not
required: the backend calls this synchronously per request.
"""
import hashlib
import time
from collections import OrderedDict
from dataclasses import replace
from typing import Any


def source_key(document_checksum: str | None, ocr_text: str) -> str:
    if document_checksum and document_checksum.strip():
        return "checksum:" + document_checksum.strip()
    return "text-sha256:" + hashlib.sha256(ocr_text.encode("utf-8")).hexdigest()


def cache_key(*, source: str, pipeline_version: str, route_chain: str,
              prompt_version: str, schema_version: str) -> str:
    material = "|".join([source, pipeline_version, route_chain, prompt_version, schema_version])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class ExtractionCache:
    def __init__(self, max_entries: int = 256, ttl_seconds: int = 3600) -> None:
        self._max_entries = max(1, max_entries)
        self._ttl_seconds = max(1, ttl_seconds)
        self._items: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def configure(self, *, max_entries: int, ttl_seconds: int) -> None:
        self._max_entries = max(1, max_entries)
        self._ttl_seconds = max(1, ttl_seconds)
        while len(self._items) > self._max_entries:
            self._items.popitem(last=False)

    @property
    def max_entries(self) -> int:
        return self._max_entries

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def get(self, key: str) -> Any | None:
        slot = self._items.get(key)
        if slot is None:
            return None
        stored_at, result = slot
        if time.monotonic() - stored_at > self._ttl_seconds:
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return replace(result, cache_hit=True, attempted_routes=[])

    def put(self, key: str, result: Any) -> None:
        self._items[key] = (time.monotonic(), result)
        self._items.move_to_end(key)
        while len(self._items) > self._max_entries:
            self._items.popitem(last=False)

    def __len__(self) -> int:
        return len(self._items)
