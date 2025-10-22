from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

try:
    from openai import AsyncOpenAI  # type: ignore import-not-found
except Exception:  # pragma: no cover - library optional at runtime
    AsyncOpenAI = None  # type: ignore assignment

logger = logging.getLogger(__name__)

_DEFAULT_SCHEMA = {
    "name": "TradingSignal",
    "schema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Currency pair or asset ticker in uppercase, e.g., EURUSD.",
            },
            "action": {
                "type": "string",
                "enum": ["BUY", "SELL", "HOLD", "NONE"],
                "description": "Trading direction inferred from the signal. Use HOLD when direction is neutral or missing.",
            },
            "entry": {
                "type": "string",
                "description": "Price level for entry. Use the literal MARKET if signal requests market order.",
            },
            "take_profit": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of take profit targets. Use an empty array if the signal has no targets.",
            },
            "stop_loss": {
                "type": "string",
                "description": "Stop loss price. Use NA when not provided.",
            },
            "timeframe": {
                "type": "string",
                "description": "Optional timeframe or schedule mentioned in the signal. Use NA if absent.",
            },
            "notes": {
                "type": "string",
                "description": "Additional remarks or context that should accompany the signal. Use NA if none.",
            },
        },
        "required": ["symbol", "action", "entry", "take_profit", "stop_loss"],
        "additionalProperties": False,
    },
}

_SYSTEM_PROMPT = """You are an assistant that extracts structured trading data from Telegram signals.
Read the user message and respond strictly in JSON following the provided schema.

Guidelines:
- Preserve the asset naming in uppercase without extra characters. If multiple assets are mentioned, pick the primary one.
- Interpret BUY/LONG as BUY and SELL/SHORT as SELL. If direction cannot be inferred, set action to HOLD.
- Entry should be the numeric price if present; otherwise respond with the literal string MARKET.
- Take profit must be an array of strings in ascending order. Use an empty array when no targets are present.
- Stop loss must always have a value; use the literal string NA if not provided.
- Include timeframe information when explicitly present; otherwise respond with NA.
- Trim textual noise and never invent data absent from the signal.
"""


class SignalParser:
    """Wrapper around OpenAI Responses API to transform raw signals into structured JSON."""

    def __init__(
        self,
        api_key: Optional[str],
        model: str,
        *,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._schema = response_schema or _DEFAULT_SCHEMA
        if api_key and AsyncOpenAI is not None:
            self._client = AsyncOpenAI(api_key=api_key)
        else:
            self._client = None
            if api_key:
                logger.warning("OpenAI client unavailable even though API key is set.")

    @property
    def configured(self) -> bool:
        return self._client is not None

    async def parse(self, message: str) -> Dict[str, Any]:
        if not message or not message.strip():
            raise ValueError("Cannot parse empty signal message.")
        if not self._client:
            raise RuntimeError("OpenAI API key is not configured.")

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": message.strip()},
                ],
                response_format={"type": "json_schema", "json_schema": self._schema},
                temperature=0.2,
            )
        except Exception as exc:  # pragma: no cover - depends on external API
            logger.exception("OpenAI API error while parsing signal.")
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc

        # The Responses API returns a list of outputs; gather concatenated text blocks.
        try:
            json_payload = getattr(response, "output_text", None)
            if not json_payload:
                output_blocks = getattr(response, "output", []) or []
                text_chunks = []
                for block in output_blocks:
                    for item in getattr(block, "content", []):
                        if getattr(item, "type", None) == "output_text":
                            text_chunks.append(item.text)
                        elif getattr(item, "type", None) == "text":
                            text_chunks.append(item.text)
                json_payload = "".join(text_chunks).strip()
            if not json_payload:
                raise ValueError("Empty JSON payload returned by OpenAI.")
            return json.loads(json_payload)
        except Exception as exc:
            logger.exception("Failed to parse JSON payload generated by OpenAI.")
            raise RuntimeError(f"Invalid JSON returned by OpenAI: {exc}") from exc
