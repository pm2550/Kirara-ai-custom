from typing import Annotated, Any, Dict, List, Optional

from kirara_ai.im.message import IMMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.llm.format.response import LLMChatResponse
from kirara_ai.logger import get_logger
from kirara_ai.memory.composes.base import ComposableMessageType
from kirara_ai.memory.memory_manager import MemoryManager
from kirara_ai.memory.registry import ComposerRegistry, DecomposerRegistry, ScopeRegistry
from kirara_ai.workflow.core.block import Block, Input, Output, ParamMeta


def scope_type_options_provider(container: DependencyContainer, block: Block) -> List[str]:
    return ["global", "group", "member"]


def decomposer_name_options_provider(container: DependencyContainer, block: Block) -> List[str]:
    return ["default", "multi_element"]


class ChatMemoryQuery(Block):
    name = "chat_memory_query"
    inputs = {
        "chat_sender": Input(
            "chat_sender", "聊天对象", ChatSender, "要查询记忆的聊天对象"
        )
    }
    outputs = {"memory_content": Output(
        "memory_content", "记忆内容", List[ComposableMessageType], "记忆内容")}
    container: DependencyContainer

    def __init__(
        self,
        scope_type: Annotated[
            Optional[str],
            ParamMeta(
                label="级别",
                description="要查询记忆的级别，代表记忆可以被共享的粒度。（例如：member 级别下，同一群聊下不同用户的记忆互相隔离； group 级别下，同一群组内所有成员记忆共享，但不同群组之间记忆互相隔离）",
                options_provider=scope_type_options_provider,
            ),
        ],
        decomposer_name: Annotated[
            Optional[str],
            ParamMeta(
                label="解析器名称",
                description="要使用的解析器名称",
                options_provider=decomposer_name_options_provider,
            ),
        ] = "default",
        extra_identifier: Annotated[
            Optional[str],
            ParamMeta(
                label="额外隔离标识符",
                description="仅支持输入英文，可为空。对于同一用户，不同标识符之间的记忆互相隔离。可用于避免不同工作流之间记忆互相干扰。",
            ),
        ] = None,
    ):
        self.scope_type = scope_type
        self.decomposer_name: str = decomposer_name or "default"
        self.extra_identifier = extra_identifier

    def execute(self, chat_sender: ChatSender) -> Dict[str, Any]:
        self.memory_manager = self.container.resolve(MemoryManager)

        # 如果没有指定作用域类型，使用配置中的默认值
        if self.scope_type is None:
            self.scope_type = self.memory_manager.config.default_scope

        # 获取作用域实例
        scope_registry = self.container.resolve(ScopeRegistry)
        self.scope = scope_registry.get_scope(self.scope_type)

        # 获取解析器实例
        decomposer_registry = self.container.resolve(DecomposerRegistry)
        self.decomposer = decomposer_registry.get_decomposer(
            self.decomposer_name)

        entries = self.memory_manager.query(self.scope, chat_sender, self.extra_identifier)
        memory_content = self.decomposer.decompose(entries)
        return {"memory_content": memory_content}


class ChatMemoryStore(Block):
    name = "chat_memory_store"

    inputs = {
        "user_msg": Input("user_msg", "用户消息", IMMessage, "用户消息", nullable=True),
        "llm_resp": Input(
            "llm_resp", "LLM 回复", LLMChatResponse, "LLM 回复", nullable=True
        ),
        "middle_steps": Input(
            "middle_steps", "中间步骤消息", List[ComposableMessageType], "中间步骤消息", nullable=True
        )
    }
    outputs = {}
    container: DependencyContainer

    def __init__(
        self,
        scope_type: Annotated[
            Optional[str],
            ParamMeta(
                label="级别",
                description="要查询记忆的级别，代表记忆可以被共享的粒度。（例如：member 级别下，同一群聊下不同用户的记忆互相隔离； group 级别下，同一群组内所有成员记忆共享，但不同群组之间记忆互相隔离）",
                options_provider=scope_type_options_provider,
            ),
        ],
        extra_identifier: Annotated[
            Optional[str],
            ParamMeta(
                label="额外隔离标识符",
                description="仅支持输入英文，可为空。对于同一用户，不同标识符之间的记忆互相隔离。可用于避免不同工作流之间记忆互相干扰。",
            ),
        ] = None,
    ):
        self.scope_type = scope_type
        self.logger = get_logger("Block.ChatMemoryStore")
        self.extra_identifier = extra_identifier

    def execute(
        self,
        user_msg: Optional[IMMessage] = None,
        llm_resp: Optional[LLMChatResponse] = None,
        middle_steps: Optional[List[ComposableMessageType]] = None,
    ) -> Dict[str, Any]:
        self.memory_manager = self.container.resolve(MemoryManager)

        # 如果没有指定作用域类型，使用配置中的默认值
        if self.scope_type is None:
            self.scope_type = self.memory_manager.config.default_scope

        # 获取作用域实例
        scope_registry = self.container.resolve(ScopeRegistry)
        self.scope = scope_registry.get_scope(self.scope_type)

        # 获取组合器实例
        composer_registry = self.container.resolve(ComposerRegistry)
        self.composer = composer_registry.get_composer("default")

        # 存储用户消息和LLM响应
        if user_msg is None:
            composed_messages: List[ComposableMessageType] = []
        else:
            composed_messages = [user_msg]
            
        if middle_steps is not None:
            composed_messages.extend(middle_steps)

        if llm_resp is not None:
            if llm_resp.message:
                composed_messages.append(llm_resp.message)
        if not composed_messages:
            self.logger.warning("No messages to store")
            return {}
        self.logger.debug(f"Composed messages: {composed_messages}")
        memory_entries = self.composer.compose(
            user_msg.sender if user_msg else None, composed_messages)

        # 本地文件探针: store 前
        try:
            from datetime import datetime as _dt
            with open(r'C:\\Users\\pm\\Desktop\\QQBot\\vector_sync_file.log', 'a', encoding='utf-8') as _f:
                _f.write(f"[{_dt.now().strftime('%H:%M:%S')}] [PROBE] BEFORE_STORE (project)\n")
        except Exception:
            pass

        self.memory_manager.store(self.scope, memory_entries, self.extra_identifier)

        # 本地文件探针: store 后
        try:
            from datetime import datetime as _dt
            with open(r'C:\\Users\\pm\\Desktop\\QQBot\\vector_sync_file.log', 'a', encoding='utf-8') as _f:
                _f.write(f"[{_dt.now().strftime('%H:%M:%S')}] [PROBE] AFTER_STORE (project)\n")
        except Exception:
            pass

        # 同步到向量库 (包含用户消息和雷帝回复)
        try:
            # 本地日志
            _log_file = r'C:\\Users\\pm\\Desktop\\QQBot\\vector_sync_file.log'
            def _f_log(text: str) -> None:
                try:
                    from datetime import datetime as _dt
                    with open(_log_file, 'a', encoding='utf-8') as _f:
                        _f.write(f"[{_dt.now().strftime('%H:%M:%S')}] {text}\n")
                except Exception:
                    pass
            import sys
            import os
            # 添加项目根目录到 Python 路径
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../..'))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from vector_memory import get_vector_manager
            vector_manager = get_vector_manager()
            _f_log('[VectorSync] Manager ready (project)')
            
            import hashlib
            from datetime import datetime
            
            # 1. 存储用户消息
            if user_msg:
                sender = user_msg.sender
                # 逐元素提取文本，避免 to_plain 差异
                content_parts = []
                try:
                    for element in getattr(user_msg, 'message_elements', []) or []:
                        if hasattr(element, 'text') and isinstance(element.text, str) and element.text.strip():
                            content_parts.append(element.text.strip())
                except Exception:
                    pass
                content = " ".join(content_parts).strip() if content_parts else ""
                timestamp = datetime.now().isoformat()
                message_id = hashlib.md5(
                    f"{sender.user_id}_{timestamp}_{content}".encode()
                ).hexdigest()
                
                if content:
                    _f_log(f"[VectorSync] USER add_message id={message_id} len={len(content)}")
                    vector_manager.add_message(
                        message_id=message_id,
                        content=content,
                        user_id=sender.user_id,
                        user_name=sender.display_name,
                        group_id=sender.group_id or "private",
                        timestamp=timestamp
                    )
                    _f_log("[VectorSync] USER synced OK (project)")
            
            # 2. 存储雷帝回复
            if llm_resp and llm_resp.message:
                # 提取纯文本内容
                bot_content = ""
                for element in llm_resp.message.content:
                    if hasattr(element, 'text'):
                        bot_content += element.text + " "
                bot_content = bot_content.strip()
                _f_log(f"[VectorSync] BOT content_len={len(bot_content)} (project)")
                
                if bot_content:  # 只有在有文本内容时才存储
                    bot_timestamp = datetime.now().isoformat()
                    bot_message_id = hashlib.md5(
                        f"bot_{bot_timestamp}_{bot_content}".encode()
                    ).hexdigest()
                    
                    # 获取群组信息
                    group_id = "private"
                    if user_msg and user_msg.sender:
                        group_id = user_msg.sender.group_id or "private"
                    
                    _f_log(f"[VectorSync] BOT add_message id={bot_message_id}")
                    vector_manager.add_message(
                        message_id=bot_message_id,
                        content=bot_content,
                        user_id="1204222398",  # 雷帝的 QQ 号
                        user_name="雷帝",
                        group_id=group_id,
                        timestamp=bot_timestamp
                    )
                    _f_log("[VectorSync] BOT synced OK (project)")
                
        except Exception as e:
            self.logger.warning(f"Failed to sync to vector DB: {e}")

        return {}
