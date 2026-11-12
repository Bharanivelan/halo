"""Shared HTTP client, throttling and provider-call recording."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.db import tenant_session
from app.models import ProviderCall
from app.workflow.errors import PermanentError, TransientError

_settings = get_settings()
client = httpx.Client(
    headers={"User-Agent": _settings.http_user_agent, "Accept-Language": "en-US,en;q=0.9"},
    timeout=httpx.Timeout(_settings.fetch_timeout_s, connect=8.0),
    follow_redirects=False,
)


class Throttle:
    """Minimum interval between calls per key, shared by all worker threads."""

    def __init__(self, interval_s: float):
        self.interval = interval_s
        self._last: dict[str, float] = defaultdict(float)
        self._locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._guard = threading.Lock()

    def wait(self, key: str = "_") -> None:
        with self._guard:
            lock = self._locks[key]
        with lock:
            delta = time.monotonic() - self._last[key]
            if delta < self.interval:
                time.sleep(self.interval - delta)
            self._last[key] = time.monotonic()


def raise_for_status(resp: httpx.Response, what: str) -> None:
    if resp.status_code == 429 or resp.status_code >= 500:
        ra = resp.headers.get("Retry-After")
        raise TransientError(f"{what} is busy (HTTP {resp.status_code})", float(ra) if ra and ra.isdigit() else None)
    if resp.status_code >= 400:
        raise PermanentError(f"{what} returned HTTP {resp.status_code}")


def record_provider_call(workspace_id: UUID | None, job_id: UUID | None, task_id: UUID | None, provider: str,
                         operation: str, cost_usd: float = 0.0, status: str = "ok", latency_ms: int = 0, units: int = 1) -> None:
    if not workspace_id:
        return
    try:
        with tenant_session(workspace_id) as db:
            db.add(ProviderCall(workspace_id=workspace_id, job_id=job_id, task_id=task_id, provider=provider,
                                operation=operation, cost_usd=cost_usd, status=status, latency_ms=latency_ms, units=units))
    except Exception:  # noqa: BLE001 — telemetry must never break the pipeline
        pass
