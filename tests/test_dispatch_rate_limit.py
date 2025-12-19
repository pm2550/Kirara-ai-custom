from kirara_ai.im.message import IMMessage, TextMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.workflow.core.dispatch.models.dispatch_rules import (
    BurstRateLimitConfig,
    RateLimitConfig,
)
from kirara_ai.workflow.core.dispatch.rate_limit import RateLimitGuard


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


def _make_message(user_id: str, group_id: str | None = None) -> IMMessage:
    if group_id:
        sender = ChatSender.from_group_chat(user_id=user_id, group_id=group_id, display_name=user_id)
    else:
        sender = ChatSender.from_c2c_chat(user_id=user_id, display_name=user_id)
    return IMMessage(sender=sender, message_elements=[TextMessage("hi")], raw_message={})


def test_rate_limit_per_sender() -> None:
    clock = FakeClock()
    guard = RateLimitGuard(time_provider=clock)
    config = RateLimitConfig(per_sender_seconds=10)
    msg = _make_message("user1")

    assert guard.should_block("rule", msg, config) is False
    assert guard.should_block("rule", msg, config) is True

    clock.advance(11)
    assert guard.should_block("rule", msg, config) is False


def test_rate_limit_per_chat() -> None:
    clock = FakeClock()
    guard = RateLimitGuard(time_provider=clock)
    config = RateLimitConfig(per_chat_seconds=5)

    first = _make_message("user1", "group42")
    second = _make_message("user2", "group42")

    assert guard.should_block("rule", first, config) is False
    assert guard.should_block("rule", second, config) is True

    clock.advance(6)
    assert guard.should_block("rule", second, config) is False


def test_rate_limit_burst_window() -> None:
    clock = FakeClock()
    guard = RateLimitGuard(time_provider=clock)
    config = RateLimitConfig(burst=BurstRateLimitConfig(window_seconds=10, max_triggers=2))

    msg = _make_message("user1", "group99")

    assert guard.should_block("rule", msg, config) is False
    clock.advance(1)
    assert guard.should_block("rule", msg, config) is False

    clock.advance(1)
    assert guard.should_block("rule", msg, config) is True

    clock.advance(10)
    assert guard.should_block("rule", msg, config) is False
