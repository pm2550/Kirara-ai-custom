from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic
from typing import Callable, Deque, Dict, Optional, Tuple

from kirara_ai.im.message import IMMessage
from kirara_ai.im.sender import ChatSender, ChatType

from .models.dispatch_rules import RateLimitConfig


class RateLimitGuard:
    """Simple in-memory rate limiter for dispatch rules."""

    def __init__(self, time_provider: Optional[Callable[[], float]] = None) -> None:
        self._now = time_provider or monotonic
        self._per_sender: Dict[str, float] = {}
        self._per_chat: Dict[str, float] = {}
        self._burst: Dict[str, Deque[float]] = defaultdict(deque)

    def should_block(self, rule_id: str, message: IMMessage, config: RateLimitConfig) -> bool:
        """Return True if the trigger should be blocked due to rate limit."""
        if not config:
            return False

        sender_key, chat_key = self._build_keys(rule_id, getattr(message, "sender", None))
        if not sender_key and not chat_key:
            return False

        now = self._now()
        blocked = False
        pending_updates: list[Tuple[str, str]] = []
        burst_queue: Optional[Deque[float]] = None

        per_sender_seconds = config.per_sender_seconds or 0
        if per_sender_seconds > 0 and sender_key:
            last = self._per_sender.get(sender_key)
            if last is not None and now - last < per_sender_seconds:
                blocked = True
            else:
                pending_updates.append(("per_sender", sender_key))

        per_chat_seconds = config.per_chat_seconds or 0
        if per_chat_seconds > 0 and chat_key:
            last = self._per_chat.get(chat_key)
            if last is not None and now - last < per_chat_seconds:
                blocked = True
            else:
                pending_updates.append(("per_chat", chat_key))

        burst_cfg = config.burst
        if burst_cfg and burst_cfg.window_seconds > 0 and burst_cfg.max_triggers > 0 and chat_key:
            burst_queue = self._burst[chat_key]
            while burst_queue and now - burst_queue[0] > burst_cfg.window_seconds:
                burst_queue.popleft()
            if len(burst_queue) >= burst_cfg.max_triggers:
                blocked = True
            else:
                pending_updates.append(("burst", chat_key))

        if blocked:
            return True

        for bucket, key in pending_updates:
            if bucket == "per_sender":
                self._per_sender[key] = now
            elif bucket == "per_chat":
                self._per_chat[key] = now
            elif bucket == "burst" and burst_queue is not None:
                burst_queue.append(now)

        return False

    @staticmethod
    def _build_keys(rule_id: str, sender: Optional[ChatSender]) -> Tuple[Optional[str], Optional[str]]:
        if sender is None:
            return None, None

        if sender.chat_type == ChatType.GROUP:
            chat_key = f"{rule_id}:group:{sender.group_id}"
            sender_key = f"{chat_key}:{sender.user_id}"
        else:
            chat_key = f"{rule_id}:c2c:{sender.user_id}"
            sender_key = chat_key

        return sender_key, chat_key
