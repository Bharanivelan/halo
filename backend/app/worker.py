"""Worker process: claims tasks from the Postgres queue and runs them on a thread pool.

Run: python -m app.worker
Safe to run several workers; tasks are leased with SKIP LOCKED and re-leased if a worker dies.
"""
from __future__ import annotations

import os
import signal
import socket
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

from app.core.config import get_settings
from app.core.logging import configure_logging, log
from app.discovery import steps  # noqa: F401 — registers steps
from app.workflow.engine import run_task
from app.workflow.queue import queue

_stop = threading.Event()


def main() -> None:
    configure_logging()
    s = get_settings()
    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    pool = ThreadPoolExecutor(max_workers=s.worker_concurrency, thread_name_prefix="task")
    inflight: dict = {}
    lock = threading.Lock()

    def heartbeat() -> None:
        while not _stop.wait(30):
            with lock:
                ids = list(inflight)
            try:
                queue.heartbeat(ids, worker_id)
            except Exception as e:  # noqa: BLE001
                log.warning("heartbeat_failed", error=str(e))

    threading.Thread(target=heartbeat, daemon=True).start()

    def done(task_id, fut: Future) -> None:
        with lock:
            inflight.pop(task_id, None)
        if fut.exception():
            log.error("task_runner_crash", task_id=str(task_id), error=repr(fut.exception()))

    def handle(*_):
        log.info("worker_stopping")
        _stop.set()

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)
    log.info("worker_started", worker_id=worker_id, concurrency=s.worker_concurrency)
    while not _stop.is_set():
        with lock:
            free = s.worker_concurrency - len(inflight)
        claimed = []
        if free > 0:
            try:
                claimed = queue.claim(worker_id, free)
            except Exception as e:  # noqa: BLE001 — DB hiccup; retry shortly
                log.warning("claim_failed", error=str(e))
                time.sleep(3)
                continue
        for task_id, ws in claimed:
            with lock:
                inflight[task_id] = ws
            fut = pool.submit(run_task, task_id, ws)
            fut.add_done_callback(lambda f, t=task_id: done(t, f))
        if not claimed:
            _stop.wait(1.0)
    pool.shutdown(wait=True, cancel_futures=False)
    log.info("worker_stopped")


if __name__ == "__main__":
    main()
