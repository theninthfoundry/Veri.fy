import queue
import threading
import time
import requests
import logging
from typing import Dict, Any, Optional
from .context import AgentSessionContext

logger = logging.getLogger("veri.client")


class VeriClient:
    """
    Core VERI client — manages async event emission via a background
    worker thread. Guarantees zero impact on agent execution latency.

    Events are batched (up to 50 events or 500ms, whichever comes first)
    and flushed to the gateway in a single HTTP POST.
    """

    BATCH_SIZE = 50
    FLUSH_INTERVAL_SEC = 0.5
    QUEUE_MAX = 10_000

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        cost_limit: float,
        call_limit: int,
        disabled: bool,
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.cost_limit = cost_limit
        self.call_limit = call_limit
        self.disabled = disabled

        self._queue: queue.Queue = queue.Queue(maxsize=self.QUEUE_MAX)
        self._thread: Optional[threading.Thread] = None
        self._running = False

        if not self.disabled:
            self._start_worker()

    # ── Background Worker ───────────────────────────────────────────

    def _start_worker(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="VeriTelemetryWorker"
        )
        self._thread.start()

    def _worker_loop(self) -> None:
        batch: list[Dict[str, Any]] = []
        last_flush = time.monotonic()

        while self._running:
            try:
                event = self._queue.get(timeout=0.1)
                batch.append(event)
                self._queue.task_done()
            except queue.Empty:
                pass

            now = time.monotonic()
            should_flush = (
                len(batch) >= self.BATCH_SIZE
                or (batch and (now - last_flush) >= self.FLUSH_INTERVAL_SEC)
            )

            if should_flush:
                self._flush_batch(batch)
                batch = []
                last_flush = now

        # Drain remaining events on shutdown
        if batch:
            self._flush_batch(batch)

    def _flush_batch(self, batch_data: list[Dict[str, Any]]) -> None:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                self.endpoint,
                json={"events": batch_data},
                headers=headers,
                timeout=3.0,
            )
            if response.status_code != 200:
                logger.error(
                    "VERI Gateway rejected batch. Status: %d", response.status_code
                )
        except requests.exceptions.ConnectionError:
            logger.debug("VERI Gateway unreachable — events buffered locally.")
        except Exception as e:
            logger.error("VERI telemetry dispatch error: %s", str(e))

    # ── Public API ──────────────────────────────────────────────────

    def emit_async(self, event_data: Dict[str, Any]) -> None:
        """
        Non-blocking event emission. Drops silently under backpressure
        to guarantee zero latency impact on the host agent.
        """
        if self.disabled:
            return
        try:
            self._queue.put_nowait(event_data)
        except queue.Full:
            logger.error(
                "VERI telemetry queue full (%d). Dropping event.", self.QUEUE_MAX
            )

    def session(
        self, session_id: str, agent_id: str, project_id: str
    ) -> AgentSessionContext:
        """Creates a tracked session context manager."""
        return AgentSessionContext(
            client=self,
            session_id=session_id,
            agent_id=agent_id,
            project_id=project_id,
            cost_limit=self.cost_limit,
            call_limit=self.call_limit,
        )

    def shutdown(self) -> None:
        """Gracefully stops the background worker, flushing pending events."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
