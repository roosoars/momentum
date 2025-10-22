from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from ...domain.models import Strategy, StrategySignal
from ...domain.ports.persistence import PersistenceGateway
from ...services.signal_processor import SignalJob, SignalProcessor
from ...services.telegram import TelegramService

logger = logging.getLogger(__name__)


class StrategyService:
    """Coordinates strategy lifecycle, channel subscriptions, and signal parsing."""

    MAX_ACTIVE_STRATEGIES = 5

    def __init__(
        self,
        persistence: PersistenceGateway,
        telegram_service: TelegramService,
        signal_processor: SignalProcessor,
    ) -> None:
        self._persistence = persistence
        self._telegram = telegram_service
        self._signal_processor = signal_processor
        self._strategies: Dict[int, Strategy] = {}
        self._channel_index: Dict[str, List[int]] = {}
        self._lock = asyncio.Lock()
        self._initialized_at = datetime.utcnow()

    # ------------------------------------------------------------------
    async def initialize(self) -> None:
        async with self._lock:
            items = self._persistence.get_strategies()
            self._strategies = {item.id: item for item in items}
            self._rebuild_channel_index_locked()
            self._initialized_at = datetime.utcnow()
        await self._synchronise_channels()

    # Public query helpers -------------------------------------------------
    async def list_strategies(self) -> List[Strategy]:
        async with self._lock:
            return sorted(self._strategies.values(), key=lambda item: item.created_at)

    async def get_strategy(self, strategy_id: int) -> Strategy:
        async with self._lock:
            strategy = self._strategies.get(strategy_id)
            if strategy is None:
                strategy = self._persistence.get_strategy(strategy_id)
                if strategy is None:
                    raise ValueError(f"Estratégia {strategy_id} não encontrada.")
                self._store_strategy_locked(strategy)
            return strategy

    async def get_signals(
        self,
        strategy_id: int,
        *,
        limit: int = 100,
        newer_than: Optional[datetime] = None,
    ) -> List[StrategySignal]:
        await self.get_strategy(strategy_id)
        iso = newer_than.replace(microsecond=0).isoformat() if newer_than else None
        return self._persistence.get_signals_for_strategy(strategy_id, limit, iso)

    # CRUD operations ------------------------------------------------------
    async def create_strategy(
        self,
        name: str,
        channel_identifier: str,
        *,
        activate: bool = True,
    ) -> Strategy:
        clean_name = name.strip()
        clean_identifier = channel_identifier.strip()
        if not clean_name:
            raise ValueError("Informe um nome para a estratégia.")
        if not clean_identifier:
            raise ValueError("Informe o identificador do canal do Telegram.")

        channel_info = await self._telegram.resolve_channel(clean_identifier)
        canonical_id = str(channel_info["channel_id"])
        canonical_title = channel_info.get("title")
        linked_at = datetime.utcnow().replace(microsecond=0).isoformat()

        async with self._lock:
            if activate and self._count_active_locked() >= self.MAX_ACTIVE_STRATEGIES:
                raise ValueError("Limite de cinco estratégias ativas atingido.")
            strategy = self._persistence.create_strategy(
                name=clean_name,
                channel_identifier=clean_identifier,
                channel_id=canonical_id,
                channel_title=canonical_title,
                channel_linked_at=linked_at,
                is_active=activate,
            )
            self._store_strategy_locked(strategy)

        if activate:
            await self._synchronise_channels()
        logger.info("Strategy %s (%s) created for channel %s", strategy.id, clean_name, canonical_id)
        return strategy

    async def rename_strategy(self, strategy_id: int, name: str) -> Strategy:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("O nome da estratégia não pode ser vazio.")
        async with self._lock:
            strategy = self._require_strategy_locked(strategy_id)
            updated = self._persistence.update_strategy(strategy.id, name=clean_name)
            self._store_strategy_locked(updated)
            return updated

    async def assign_channel(self, strategy_id: int, channel_identifier: str) -> Strategy:
        clean_identifier = channel_identifier.strip()
        if not clean_identifier:
            raise ValueError("Informe o canal do Telegram para vincular.")
        channel_info = await self._telegram.resolve_channel(clean_identifier)
        canonical_id = str(channel_info["channel_id"])
        canonical_title = channel_info.get("title")
        linked_at = datetime.utcnow().replace(microsecond=0).isoformat()

        async with self._lock:
            strategy = self._require_strategy_locked(strategy_id)
            updated = self._persistence.update_strategy(
                strategy.id,
                channel_identifier=clean_identifier,
                channel_id=canonical_id,
                channel_title=canonical_title,
                channel_linked_at=linked_at,
            )
            self._store_strategy_locked(updated)

        await self._synchronise_channels()
        logger.info("Strategy %s linked to channel %s", strategy_id, canonical_id)
        return updated

    async def delete_strategy(self, strategy_id: int) -> None:
        async with self._lock:
            self._require_strategy_locked(strategy_id)
            self._persistence.delete_strategy(strategy_id)
            self._strategies.pop(strategy_id, None)
            self._rebuild_channel_index_locked()
        await self._synchronise_channels()
        logger.info("Strategy %s deleted", strategy_id)

    # State transitions ----------------------------------------------------
    async def activate_strategy(self, strategy_id: int) -> Strategy:
        async with self._lock:
            strategy = self._require_strategy_locked(strategy_id)
            if strategy.is_active and not strategy.is_paused:
                return strategy
            if not strategy.is_active and self._count_active_locked() >= self.MAX_ACTIVE_STRATEGIES:
                raise ValueError("Limite de cinco estratégias ativas atingido.")
            updated = self._persistence.update_strategy(strategy.id, is_active=True, is_paused=False)
            self._store_strategy_locked(updated)
        await self._synchronise_channels()
        logger.info("Strategy %s activated", strategy_id)
        return updated

    async def deactivate_strategy(self, strategy_id: int) -> Strategy:
        async with self._lock:
            strategy = self._require_strategy_locked(strategy_id)
            if not strategy.is_active:
                return strategy
            updated = self._persistence.update_strategy(strategy.id, is_active=False)
            self._store_strategy_locked(updated)
        await self._synchronise_channels()
        logger.info("Strategy %s deactivated", strategy_id)
        return updated

    async def pause_strategy(self, strategy_id: int) -> Strategy:
        async with self._lock:
            strategy = self._require_strategy_locked(strategy_id)
            if strategy.is_paused:
                return strategy
            updated = self._persistence.update_strategy(strategy.id, is_paused=True)
            self._store_strategy_locked(updated)
            return updated

    async def resume_strategy(self, strategy_id: int) -> Strategy:
        async with self._lock:
            strategy = self._require_strategy_locked(strategy_id)
            if not strategy.is_active:
                raise ValueError("Ative a estratégia antes de retomar.")
            if not strategy.is_paused:
                return strategy
            if self._count_active_locked() >= self.MAX_ACTIVE_STRATEGIES:
                raise ValueError("Limite de cinco estratégias ativas atingido.")
            updated = self._persistence.update_strategy(strategy.id, is_paused=False)
            self._store_strategy_locked(updated)
        logger.info("Strategy %s resumed", strategy_id)
        return updated

    # Runtime event handling ----------------------------------------------
    async def handle_incoming_message(self, message: Dict[str, object]) -> None:
        channel_id = str(message.get("channel_id")) if message.get("channel_id") else None
        if not channel_id:
            return
        telegram_id = int(message.get("telegram_id", 0))
        if telegram_id <= 0:
            return

        created_at = self._parse_timestamp(message.get("created_at")) or datetime.utcnow()
        if created_at < self._initialized_at:
            return
        raw_message = message.get("message")
        if raw_message is not None and not str(raw_message).strip():
            raw_message = None

        async with self._lock:
            strategy_ids = list(self._channel_index.get(channel_id, []))
            strategies = [self._strategies[sid] for sid in strategy_ids if sid in self._strategies]

        for strategy in strategies:
            if not strategy.is_active or strategy.is_paused:
                continue
            threshold = strategy.channel_linked_at or strategy.created_at
            if threshold and created_at < threshold:
                continue
            if raw_message is None:
                continue
            job = SignalJob(
                strategy_id=strategy.id,
                channel_id=channel_id,
                telegram_message_id=telegram_id,
                raw_message=str(raw_message) if raw_message is not None else None,
                received_at=created_at,
            )
            await self._signal_processor.enqueue(job)

    # Internal helpers -----------------------------------------------------
    def _require_strategy_locked(self, strategy_id: int) -> Strategy:
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            strategy = self._persistence.get_strategy(strategy_id)
            if not strategy:
                raise ValueError(f"Estratégia {strategy_id} não encontrada.")
            self._store_strategy_locked(strategy)
        return strategy

    def _store_strategy_locked(self, strategy: Strategy) -> None:
        self._strategies[strategy.id] = strategy
        self._rebuild_channel_index_locked()

    def _rebuild_channel_index_locked(self) -> None:
        index: Dict[str, List[int]] = {}
        for strategy in self._strategies.values():
            if strategy.channel_id:
                index.setdefault(strategy.channel_id, []).append(strategy.id)
        self._channel_index = index

    def _count_active_locked(self) -> int:
        return sum(1 for item in self._strategies.values() if item.is_active and not item.is_paused)

    async def _synchronise_channels(self) -> None:
        async with self._lock:
            channel_ids = sorted(
                {item.channel_id for item in self._strategies.values() if item.is_active and item.channel_id}
            )
        if channel_ids:
            await self._telegram.set_channels(channel_ids, reset_history=False, ingest_history=False)
        else:
            await self._telegram.stop_capture()

    @staticmethod
    def _parse_timestamp(value: object) -> Optional[datetime]:
        if not value:
            return None
        text = str(value)
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            try:
                return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.debug("Unable to parse timestamp %s", text)
                return None
