import asyncio
import random
from typing import Annotated, Any, Dict, List, Optional

from kirara_ai.im.adapter import IMAdapter
from kirara_ai.im.manager import IMManager
from kirara_ai.im.message import IMMessage, MessageElement, TextMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.core.block import Block, Input, Output, ParamMeta


def im_adapter_options_provider(container: DependencyContainer, block: Block) -> List[str]:
    return [key for key, _ in container.resolve(IMManager).adapters.items()]

class GetIMMessage(Block):
    """获取 IM 消息"""

    name = "msg_input"
    container: DependencyContainer
    outputs = {
        "msg": Output("msg", "IM 消息", IMMessage, "获取 IM 发送的最新一条的消息"),
        "sender": Output("sender", "发送者", ChatSender, "获取 IM 消息的发送者"),
    }

    def execute(self, **kwargs) -> Dict[str, Any]:
        msg = self.container.resolve(IMMessage)
        return {"msg": msg, "sender": msg.sender}


class SendIMMessage(Block):
    """发送 IM 消息"""

    name = "msg_sender"
    inputs = {
        "msg": Input("msg", "IM 消息", IMMessage, "要从 IM 发送的消息"),
        "target": Input(
            "target",
            "发送对象",
            ChatSender,
            "要发送给谁，如果填空则默认发送给消息的发送者",
            nullable=True,
        ),
    }
    outputs = {}
    container: DependencyContainer

    def __init__(
        self, im_name: Annotated[Optional[str], ParamMeta(label="聊天平台适配器名称", options_provider=im_adapter_options_provider)] = None
    ):
        self.im_name = im_name

    def execute(
        self, msg: IMMessage, target: Optional[ChatSender] = None
    ) -> Dict[str, Any]:
        src_msg = self.container.resolve(IMMessage)
        if not self.im_name:
            adapter = self.container.resolve(IMAdapter)
        else:
            adapter = self.container.resolve(
                IMManager).get_adapter(self.im_name)
        loop: asyncio.AbstractEventLoop = self.container.resolve(
            asyncio.AbstractEventLoop
        )
        loop.create_task(adapter.send_message(msg, target or src_msg.sender))
        return {"ok": True}


class SendIMMessageBatch(Block):
    """批量发送 IM 消息"""

    name = "msg_sender_batch"
    inputs = {
        "msgs": Input("msgs", "IM 消息列表", List[IMMessage], "要发送的消息列表"),
        "target": Input(
            "target",
            "发送对象",
            ChatSender,
            "要发送给谁，如果填空则默认发送给消息的发送者",
            nullable=True,
        ),
    }
    outputs = {}
    container: DependencyContainer

    def __init__(
        self,
        im_name: Annotated[Optional[str], ParamMeta(label="聊天平台适配器名称", options_provider=im_adapter_options_provider)] = None,
        interval_ms: Annotated[Optional[int], ParamMeta(label="逐条发送基础间隔 (毫秒)")] = 900,
        jitter_ms: Annotated[Optional[int], ParamMeta(label="附加随机延迟上限 (毫秒)")] = 400,
    ):
        self.im_name = im_name
        self.interval_ms = max(interval_ms or 0, 0)
        self.jitter_ms = max(jitter_ms or 0, 0)

    def execute(
        self, msgs: List[IMMessage], target: Optional[ChatSender] = None
    ) -> Dict[str, Any]:
        if isinstance(msgs, IMMessage):
            msgs = [msgs]
        elif not isinstance(msgs, list):
            msgs = msgs or []

        if not msgs:
            return {"ok": True}

        src_msg = self.container.resolve(IMMessage)
        if not self.im_name:
            adapter = self.container.resolve(IMAdapter)
        else:
            adapter = self.container.resolve(
                IMManager).get_adapter(self.im_name)
        loop: asyncio.AbstractEventLoop = self.container.resolve(
            asyncio.AbstractEventLoop
        )
        recipient = target or src_msg.sender
        base_interval = self.interval_ms / 1000.0
        jitter_interval = self.jitter_ms / 1000.0

        async def _send_all():
            for idx, msg in enumerate(msgs):
                if not isinstance(msg, IMMessage):
                    continue
                if idx > 0 and (base_interval > 0 or jitter_interval > 0):
                    delay = base_interval
                    if jitter_interval > 0:
                        delay += random.uniform(0, jitter_interval)
                    await asyncio.sleep(delay)
                await adapter.send_message(msg, recipient)

        loop.create_task(_send_all())
        return {"ok": True}

# IMMessage 转纯文本


class IMMessageToText(Block):
    """IMMessage 转纯文本"""

    name = "im_message_to_text"
    container: DependencyContainer
    inputs = {"msg": Input("msg", "IM 消息", IMMessage, "IM 消息")}
    outputs = {"text": Output("text", "纯文本", str, "纯文本")}

    def execute(self, msg: IMMessage) -> Dict[str, Any]:
        return {"text": msg.content}


# 纯文本转 IMMessage
class TextToIMMessage(Block):
    """纯文本转 IMMessage"""

    name = "text_to_im_message"
    container: DependencyContainer
    inputs = {"text": Input("text", "纯文本", str, "纯文本")}
    outputs = {"msg": Output("msg", "IM 消息", IMMessage, "IM 消息")}

    def __init__(self, split_by: Annotated[Optional[str], ParamMeta(label="分段符")] = None):
        self.split_by = split_by

    def execute(self, text: str) -> Dict[str, Any]:
        if self.split_by:
            return {"msg": IMMessage(sender=ChatSender.get_bot_sender(), message_elements = [TextMessage(line.strip()) for line in text.split(self.split_by) if line.strip()])}
        else:
            return {"msg": IMMessage(sender=ChatSender.get_bot_sender(), message_elements=[TextMessage(text)])}

# 补充 IMMessage 消息
class AppendIMMessage(Block):
    """补充 IMMessage 消息"""

    name = "concat_im_message"
    container: DependencyContainer
    inputs = {
        "base_msg": Input("base_msg", "IM 消息", IMMessage, "IM 消息"),
        "append_msg": Input("append_msg", "新消息片段", MessageElement, "新消息片段"),
    }
    outputs = {"msg": Output("msg", "IM 消息", IMMessage, "IM 消息")}

    def execute(self, base_msg: IMMessage, append_msg: MessageElement) -> Dict[str, Any]:
        return {"msg": IMMessage(sender=base_msg.sender, message_elements=base_msg.message_elements + [append_msg])}
