import asyncio
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from telethon import TelegramClient, events, functions, types
from telethon.errors import (
    ChannelInvalidError,
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    InviteHashInvalidError,
    InviteHashExpiredError,
    UserAlreadyParticipantError,
)
from telethon.tl.custom.message import Message
from telethon.utils import get_peer_id

from ..domain.ports.persistence import MessageRepository

logger = logging.getLogger(__name__)

MessageListener = Callable[[Dict[str, Any]], Awaitable[None]]


class TelegramService:
    """Handles Telegram connectivity, authentication, and realtime updates."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str,
        message_repository: MessageRepository,
        history_limit: int = 200,
    ) -> None:
        self._client = TelegramClient(session_name, api_id, api_hash)
        self._messages = message_repository
        self._history_limit = history_limit
        self._channel_id: Optional[str] = None
        self._channel_title: Optional[str] = None
        self._handler = None
        self._lock = asyncio.Lock()

        self._listeners: List[MessageListener] = []

        self._authorized = False
        self._pending_phone: Optional[str] = None
        self._phone_number: Optional[str] = None
        self._password_required = False

    @property
    def is_authorized(self) -> bool:
        return self._authorized

    @property
    def phone_number(self) -> Optional[str]:
        return self._phone_number

    # ------------------------------------------------------------------ #
    async def start(self) -> None:
        await self._ensure_connection()
        logger.info("Telegram client connected (authorized=%s)", self._authorized)

    async def stop(self) -> None:
        if self._handler:
            self._client.remove_event_handler(self._handler)
            self._handler = None
        if self._client.is_connected():
            await self._client.disconnect()
        logger.info("Telegram client disconnected.")

    async def _ensure_connection(self) -> None:
        if not self._client.is_connected():
            await self._client.connect()
        self._authorized = await self._client.is_user_authorized()

    # ------------------------------------------------------------------ #
    async def send_login_code(self, phone: str) -> Dict[str, Any]:
        await self._ensure_connection()
        self._pending_phone = phone.strip()
        self._password_required = False
        try:
            await self._client.send_code_request(self._pending_phone)
        except FloodWaitError as exc:
            raise ValueError(f"Aguarde {exc.seconds} segundos para reenviar o código.") from exc
        logger.info("Login code sent to %s", self._pending_phone)
        return {"status": "code_sent"}

    async def verify_login_code(self, code: str) -> Dict[str, Any]:
        await self._ensure_connection()
        if not self._pending_phone:
            raise ValueError("Envie primeiro o número de telefone.")

        try:
            phone_log = self._pending_phone
            await self._client.sign_in(phone=self._pending_phone, code=code.strip())
            self._authorized = True
            self._password_required = False
            self._phone_number = self._pending_phone
            self._pending_phone = None
            logger.info("Telegram session authorized for %s", phone_log)
            return {"authorized": True}
        except SessionPasswordNeededError:
            self._password_required = True
            logger.info("Two factor authentication required for %s", self._pending_phone)
            return {"password_required": True}
        except PhoneCodeInvalidError as exc:
            raise ValueError("Código inválido.") from exc
        except PhoneCodeExpiredError as exc:
            raise ValueError("Código expirado, solicite um novo.") from exc

    async def provide_password(self, password: str) -> Dict[str, Any]:
        await self._ensure_connection()
        if not self._password_required:
            raise ValueError("Senha não é necessária no momento.")
        phone_log = self._pending_phone or self._phone_number
        try:
            await self._client.sign_in(password=password)
        except PasswordHashInvalidError as exc:
            raise ValueError("Senha incorreta.") from exc

        self._authorized = True
        self._password_required = False
        self._phone_number = self._pending_phone or self._phone_number
        self._pending_phone = None
        logger.info("Telegram session authorized with password for %s", phone_log)
        return {"authorized": True}

    async def log_out(self) -> None:
        await self._ensure_connection()
        if self._client.is_connected():
            await self._client.log_out()
        self._authorized = False
        self._pending_phone = None
        self._phone_number = None
        self._password_required = False
        if self._handler:
            self._client.remove_event_handler(self._handler)
            self._handler = None
        self._channel_id = None
        self._channel_title = None
        logger.info("Telegram session logged out.")

    # ------------------------------------------------------------------ #
    async def set_channel(self, channel_identifier: str, reset_history: bool = True) -> Dict[str, Any]:
        await self._ensure_connection()
        if not self._authorized:
            raise ValueError("Autentique-se no Telegram antes de configurar o canal.")

        async with self._lock:
            logger.info("Configuring channel listener for %s", channel_identifier)
            try:
                entity = await self._client.get_entity(channel_identifier)
            except (ChannelInvalidError, ValueError):
                entity = await self._resolve_entity(channel_identifier)
                if entity is None:
                    raise ValueError("Canal inválido ou inacessível.")

            canonical_id = str(get_peer_id(entity))
            title = getattr(entity, "title", None) or getattr(entity, "username", None) or canonical_id

            if reset_history:
                self._messages.clear_messages_for_channel(canonical_id)

            await self._ingest_history(entity, canonical_id)

            if self._handler:
                self._client.remove_event_handler(self._handler)

            self._channel_id = canonical_id
            self._channel_title = title

            self._handler = self._client.add_event_handler(
                self._on_new_message, events.NewMessage(chats=entity)
            )

            logger.info("Listening to channel %s (%s)", title, canonical_id)
            return {"channel_id": canonical_id, "title": title}

    async def _resolve_entity_from_dialogs(self, identifier: str) -> Optional[object]:
        """Fallback resolution by iterating dialogs when get_entity fails."""

        identifier = identifier.strip()
        numeric_identifier: Optional[str] = None
        try:
            numeric_identifier = str(int(identifier))
        except ValueError:
            numeric_identifier = None
        username_identifier = identifier.lstrip("@").lower()

        async for dialog in self._client.iter_dialogs():
            entity = dialog.entity
            if not entity:
                continue
            if numeric_identifier is not None:
                peer_id = str(get_peer_id(entity))
                if peer_id == numeric_identifier:
                    return entity
            username = getattr(entity, "username", None)
            if username and username_identifier and username_identifier == username.lower():
                return entity

        logger.warning("Unable to resolve channel %s from dialogs", identifier)
        return None

    async def _resolve_entity(self, identifier: str) -> Optional[object]:
        identifier = identifier.strip()

        # Attempt to use invite links
        entity = await self._resolve_entity_from_invite(identifier)
        if entity is not None:
            return entity

        # Fallback to dialogs if the invite path did not return the entity
        return await self._resolve_entity_from_dialogs(identifier)

    async def _resolve_entity_from_invite(self, identifier: str) -> Optional[object]:
        lowered = identifier.lower()
        if "t.me/" not in lowered:
            return None

        slug = identifier.split("t.me/")[-1].strip()

        if slug.startswith("+"):
            invite_hash = slug.lstrip("+")
            try:
                result = await self._client(functions.messages.ImportChatInviteRequest(invite_hash))
            except (InviteHashInvalidError, InviteHashExpiredError, UserAlreadyParticipantError):
                logger.warning("Invite hash invalid or already joined for %s", identifier)
                return None
            except FloodWaitError as exc:
                logger.warning("Flood wait while importing invite: %s", exc.seconds)
                return None

            if isinstance(result, types.messages.ChatInviteAlready):
                return result.chat
            if isinstance(result, types.messages.ChatInvite):
                # If joining succeeds, fetch the entity using the peer id returned
                if result.chats:
                    chat = result.chats[0]
                    try:
                        return await self._client.get_entity(chat.id)
                    except Exception:  # pragma: no cover - defensive
                        return chat
            return None

        slug = slug.lstrip("@")
        if not slug:
            return None
        try:
            return await self._client.get_entity(slug)
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    def add_listener(self, listener: MessageListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: MessageListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    async def _notify_listeners(self, message: Dict[str, Any]) -> None:
        for listener in list(self._listeners):
            try:
                await listener(message)
            except Exception:  # pragma: no cover - defensive
                logger.exception("Error notifying listener")

    # ------------------------------------------------------------------ #
    async def _ingest_history(self, entity: object, canonical_id: str) -> None:
        fetched = 0
        try:
            async for message in self._client.iter_messages(entity, limit=self._history_limit):
                await self._persist_message(message, canonical_id, broadcast=False)
                fetched += 1
        except FloodWaitError as exc:
            logger.warning("Telegram rate limit hit while fetching history: wait %s seconds", exc.seconds)
        logger.info("Fetched %s historical messages for channel %s", fetched, canonical_id)

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        message: Message = event.message
        channel_id = str(event.chat_id or self._channel_id or "")
        await self._persist_message(message, channel_id, broadcast=True)

    async def _persist_message(self, message: Message, channel_id: str, broadcast: bool) -> Dict[str, Any]:
        sender_id = message.sender_id
        sender_repr = str(sender_id) if sender_id is not None else None
        created_at = (
            message.date.isoformat()
            if isinstance(message.date, datetime)
            else datetime.utcnow().isoformat()
        )
        text_content = message.message or getattr(message, "raw_text", None)

        self._messages.save_message(
            telegram_id=message.id,
            channel_id=channel_id,
            sender=sender_repr,
            message=text_content,
            payload=message.to_dict(),
            created_at=created_at,
        )

        record = {
            "telegram_id": message.id,
            "channel_id": channel_id,
            "sender": sender_repr,
            "message": text_content,
            "created_at": created_at,
        }

        if broadcast:
            await self._notify_listeners(record)
        return record

    # ------------------------------------------------------------------ #
    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self._client.is_connected(),
            "authorized": self._authorized,
            "channel_id": self._channel_id,
            "channel_title": self._channel_title,
            "pending_phone": self._pending_phone,
            "phone_number": self._phone_number,
            "password_required": self._password_required,
        }

    async def list_available_channels(self) -> List[Dict[str, Any]]:
        await self._ensure_connection()
        if not self._authorized:
            raise ValueError("Autentique-se antes de listar os canais disponíveis.")

        results: List[Dict[str, Any]] = []
        async for dialog in self._client.iter_dialogs():
            entity = dialog.entity
            if not entity:
                continue

            if not hasattr(entity, "id"):
                continue

            peer_id = str(get_peer_id(entity))
            username = getattr(entity, "username", None)
            is_channel = getattr(entity, "broadcast", False) or getattr(entity, "megagroup", False)
            entity_type = entity.__class__.__name__.lower()

            if entity_type in {"channel", "chat"} or is_channel:
                results.append(
                    {
                        "id": peer_id,
                        "title": dialog.name or getattr(entity, "title", peer_id),
                        "username": username,
                        "type": entity_type,
                    }
                )

        results.sort(key=lambda item: item["title"].casefold())
        return results
