from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Dict, List, Optional

from ..domain.models import StrategySignal
from ..domain.ports.persistence import PersistenceGateway
from .openai_parser import SignalParser

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SignalJob:
    strategy_id: int
    channel_id: str
    telegram_message_id: int
    raw_message: Optional[str]
    received_at: datetime


SignalRecordedCallback = Callable[[StrategySignal], Awaitable[None]]


class SignalProcessor:
    """Background worker that transforms raw messages into structured signals."""

    def __init__(
        self,
        persistence: PersistenceGateway,
        parser: SignalParser,
        *,
        retention_hours: int = 24,
        max_workers: int = 2,
        callback: Optional[SignalRecordedCallback] = None,
    ) -> None:
        self._persistence = persistence
        self._parser = parser
        self._retention = timedelta(hours=retention_hours)
        self._max_workers = max_workers
        self._queue: asyncio.Queue[Optional[SignalJob]] = asyncio.Queue()
        self._workers: List[asyncio.Task[None]] = []
        self._shutdown = asyncio.Event()
        self._callback = callback

    async def start(self) -> None:
        if self._workers:
            return
        logger.info("Starting signal processor with %s workers.", self._max_workers)
        self._shutdown.clear()
        loop = asyncio.get_running_loop()
        for _ in range(self._max_workers):
            task = loop.create_task(self._worker(), name="signal-processor")
            self._workers.append(task)

    async def stop(self) -> None:
        if not self._workers:
            return
        logger.info("Stopping signal processor.")
        self._shutdown.set()
        for _ in self._workers:
            await self._queue.put(None)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def enqueue(self, job: SignalJob) -> None:
        if self._shutdown.is_set():
            logger.warning("Signal processor is shutting down; dropping job for strategy %s.", job.strategy_id)
            return
        await self._queue.put(job)

    async def _worker(self) -> None:
        while not self._shutdown.is_set():
            job = await self._queue.get()
            if job is None:
                self._queue.task_done()
                break
            try:
                await self._process_job(job)
            except Exception:  # pragma: no cover - defensive
                logger.exception("Unexpected error while processing signal job.")
            finally:
                self._queue.task_done()

    async def _process_job(self, job: SignalJob) -> None:
        logger.debug(
            "Processing signal job strategy=%s telegram_id=%s",
            job.strategy_id,
            job.telegram_message_id,
        )
        processed_at = datetime.utcnow()
        status = "parsed"
        error: Optional[str] = None
        payload: Dict[str, object]

        try:
            payload = await self._parser.parse(job.raw_message or "")
        except Exception as exc:
            status = "failed"
            error = str(exc)
            payload = {
                "symbol": "NA",
                "action": "NONE",
                "entry": "NA",
                "take_profit": [],
                "stop_loss": "NA",
                "notes": "Parser failed",
                "error": error,
            }
            logger.warning(
                "Failed to parse signal (strategy=%s telegram_id=%s): %s",
                job.strategy_id,
                job.telegram_message_id,
                exc,
            )

        signal = self._persistence.record_signal(
            strategy_id=job.strategy_id,
            channel_id=job.channel_id,
            telegram_message_id=job.telegram_message_id,
            raw_message=job.raw_message,
            parsed_payload=payload,
            status=status,
            error=error,
            received_at=job.received_at.replace(microsecond=0).isoformat(),
            processed_at=processed_at.replace(microsecond=0).isoformat(),
        )

        cutoff = (datetime.utcnow() - self._retention).replace(microsecond=0).isoformat()
        purged = self._persistence.purge_signals_older_than(cutoff)
        if purged:
            logger.debug("Purged %s expired signals older than %s.", purged, cutoff)

        if self._callback:
            try:
                await self._callback(signal)
            except Exception:  # pragma: no cover - defensive
                logger.exception("Callback raised while notifying about processed signal.")
