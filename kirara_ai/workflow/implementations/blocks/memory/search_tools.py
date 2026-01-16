"""
搜索工具提供者 Block
将搜索功能封装成 Tool，让 AI 自主决定搜索策略
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, List, Optional

from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.llm.format.message import LLMToolResultContent
from kirara_ai.llm.format.tool import CallableWrapper, TextContent, Tool, ToolCall, ToolInputSchema
from kirara_ai.logger import get_logger
from kirara_ai.workflow.core.block import Block, Output
from kirara_ai.workflow.core.block.param import ParamMeta


class SearchToolProvider(Block):
    """
    提供记忆搜索工具，让 AI 自主选择搜索方式和参数
    
    提供三种搜索工具:
    1. keyword_search - 关键词精确匹配
    2. vector_search - 语义向量搜索  
    3. recent_chat_search - 最近对话搜索
    """
    name = "search_tool_provider"
    outputs = {
        "tools": Output("tools", "搜索工具列表", List[Tool], "可用的搜索工具列表")
    }
    container: DependencyContainer
    
    # 用户别名映射：别名 -> QQ号列表（用字符串格式）
    USER_ALIAS_MAP = {
        "陆": ["3113742967"],
        "陆大师": ["3113742967"],
        "猪猪陆": ["3113742967"],
        "高": ["1021083474"],
        "高大师": ["1021083474"],
        "任": ["2359054324"],
        "任大仙": ["2359054324"],
        "丁": ["1290480847"],
        "小丁丁": ["1290480847"],
    }
    
    @staticmethod
    def _normalize_user_id(user_id) -> str:
        """统一 user_id 为字符串格式"""
        return str(user_id) if user_id else ""

    @staticmethod
    def _normalize_group_id(group_id) -> str:
        """统一 group_id 为字符串格式"""
        return str(group_id).strip() if group_id else ""

    def _iter_memory_files(self, group_id: str):
        """遍历符合条件的记忆文件（可按群号过滤）"""
        if not os.path.exists(self.memory_dir):
            return
        for name in os.listdir(self.memory_dir):
            if not (name.startswith("group_") or name.startswith("c2c_") or name.startswith("member_")):
                continue
            if name.endswith("_summary.json"):
                continue
            if group_id:
                if name.startswith("group_"):
                    if name != f"group_{group_id}.json":
                        continue
                elif name.startswith("member_"):
                    if not name.startswith(f"member_{group_id}_"):
                        continue
                else:
                    # 指定群号时不扫描私聊
                    continue
            yield os.path.join(self.memory_dir, name)

    def __init__(
        self,
        memory_dir: Annotated[
            str,
            ParamMeta(
                label="记忆目录",
                description="存储聊天记录的目录路径"
            )
        ] = "data/memory",
        enable_vector_search: Annotated[
            bool,
            ParamMeta(
                label="启用向量搜索",
                description="是否启用向量搜索功能"
            )
        ] = True,
        enable_keyword_search: Annotated[
            bool,
            ParamMeta(
                label="启用关键词搜索",
                description="是否启用关键词搜索功能"
            )
        ] = True,
        enable_recent_search: Annotated[
            bool,
            ParamMeta(
                label="启用最近对话搜索",
                description="是否启用最近对话搜索功能"
            )
        ] = True,
    ):
        self.memory_dir = memory_dir
        self.enable_vector_search = enable_vector_search
        self.enable_keyword_search = enable_keyword_search
        self.enable_recent_search = enable_recent_search
        self.logger = get_logger("SearchToolProvider")

    async def _keyword_search(self, tool_call: ToolCall) -> LLMToolResultContent:
        """关键词搜索实现"""
        args = tool_call.function.arguments or {}
        query = args.get("query", "")
        days_range = args.get("days_range", 30)
        limit = args.get("limit", 15)
        group_id = self._normalize_group_id(args.get("group_id", ""))
        
        # 检查是否是用户别名
        target_user_ids = self.USER_ALIAS_MAP.get(query, [])
        
        results = []
        time_range_start = datetime.now() - timedelta(days=days_range)
        for file_path in self._iter_memory_files(group_id):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    all_entries = json.load(f)
                for entry in all_entries:
                    if len(results) >= limit:
                        break
                    entry_timestamp = datetime.fromisoformat(
                        entry.get("timestamp", datetime.now().isoformat())
                    )
                    if entry_timestamp < time_range_start:
                        continue
                    content = entry.get("content", "") or ""
                    sender = entry.get("sender", {})
                    sender_name = sender.get("display_name", "")
                    user_id = self._normalize_user_id(sender.get("user_id", ""))
                    
                    if query:
                        lowered = query.lower()
                        # 匹配条件：内容包含关键词、发送者名字包含关键词、或者是目标用户ID
                        matched = (
                            lowered in content.lower() or 
                            lowered in sender_name.lower() or
                            user_id in target_user_ids
                        )
                        if matched:
                            results.append({
                                "content": content,
                                "user_name": sender_name,
                                "timestamp": entry.get("timestamp", ""),
                                "source": "keyword"
                            })
            except Exception as e:
                self.logger.warning(f"Error reading {file_path}: {e}")
                continue
        
        # 按时间倒序
        results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        results = results[:limit]
        
        result_text = self._format_results(results, "关键词搜索")
        return LLMToolResultContent(
            id=tool_call.id,
            name=tool_call.function.name,
            content=[TextContent(text=result_text)]
        )

    async def _vector_search(self, tool_call: ToolCall) -> LLMToolResultContent:
        """向量搜索实现"""
        args = tool_call.function.arguments or {}
        query = args.get("query", "")
        limit = args.get("limit", 10)
        group_id = self._normalize_group_id(args.get("group_id", ""))
        
        results = []
        try:
            # 动态导入向量搜索模块
            project_root = os.path.abspath(os.getcwd())
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from vector_memory import get_vector_manager
            vector_manager = get_vector_manager()
            
            vector_results = vector_manager.search(
                query=query,
                n_results=limit,
                group_filter=group_id or None
            )
            
            for r in vector_results:
                results.append({
                    "content": r.get("content", ""),
                    "user_name": r.get("user_name", ""),
                    "timestamp": r.get("timestamp", ""),
                    "similarity": f"{(1 - r.get('distance', 0)):.0%}",
                    "source": "vector"
                })
        except Exception as e:
            self.logger.error(f"Vector search error: {e}")
            result_text = f"向量搜索失败: {str(e)}"
            return LLMToolResultContent(
                id=tool_call.id,
                name=tool_call.function.name,
                content=[TextContent(text=result_text)],
                isError=True
            )
        
        result_text = self._format_results(results, "向量语义搜索")
        return LLMToolResultContent(
            id=tool_call.id,
            name=tool_call.function.name,
            content=[TextContent(text=result_text)]
        )

    async def _recent_chat_search(self, tool_call: ToolCall) -> LLMToolResultContent:
        """最近对话搜索实现"""
        args = tool_call.function.arguments or {}
        user_name = args.get("user_name", "")
        limit = args.get("limit", 20)
        hours = args.get("hours", 24)
        group_id = self._normalize_group_id(args.get("group_id", ""))
        
        # 检查是否是用户别名
        target_user_ids = self.USER_ALIAS_MAP.get(user_name, []) if user_name else []
        
        results = []
        time_range_start = datetime.now() - timedelta(hours=hours)
        for file_path in self._iter_memory_files(group_id):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    all_entries = json.load(f)
                for entry in reversed(all_entries):  # 从最新的开始
                    if len(results) >= limit:
                        break
                    entry_timestamp = datetime.fromisoformat(
                        entry.get("timestamp", datetime.now().isoformat())
                    )
                    if entry_timestamp < time_range_start:
                        continue
                    sender = entry.get("sender", {})
                    sender_name = sender.get("display_name", "")
                    user_id = self._normalize_user_id(sender.get("user_id", ""))
                    
                    # 如果指定了用户名，则过滤（支持别名）
                    if user_name:
                        name_match = user_name.lower() in sender_name.lower()
                        id_match = user_id in target_user_ids
                        if not (name_match or id_match):
                            continue
                        
                    content = entry.get("content", "") or ""
                    results.append({
                        "content": content,
                        "user_name": sender_name,
                        "timestamp": entry.get("timestamp", ""),
                        "source": "recent"
                    })
            except Exception as e:
                self.logger.warning(f"Error reading {file_path}: {e}")
                continue
        
        # 按时间倒序
        results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        results = results[:limit]
        
        result_text = self._format_results(results, "最近对话")
        return LLMToolResultContent(
            id=tool_call.id,
            name=tool_call.function.name,
            content=[TextContent(text=result_text)]
        )

    def _format_results(self, results: List[Dict], search_type: str) -> str:
        """格式化搜索结果"""
        if not results:
            return f"[{search_type}] 没有找到相关记录。"
        
        lines = [f"[{search_type}] 找到 {len(results)} 条相关记录:\n"]
        for i, r in enumerate(results, 1):
            user_name = r.get("user_name", "匿名")
            content = r.get("content", "")
            timestamp = r.get("timestamp", "")[:19] if r.get("timestamp") else ""
            similarity = r.get("similarity", "")
            
            line = f"{i}. [{user_name}]: {content}"
            if similarity:
                line += f" (相似度: {similarity})"
            if timestamp:
                line += f"\n   时间: {timestamp}"
            lines.append(line)
        
        return "\n".join(lines)

    def execute(self) -> Dict[str, Any]:
        """返回可用的搜索工具列表"""
        tools = []
        
        if self.enable_keyword_search:
            tools.append(Tool(
                name="keyword_search",
                description="按关键词精确匹配搜索聊天记录。适合搜索人名、特定词语、专有名词等。当用户问'XXX说过什么'或'有没有人提过XXX'时使用。可选传 group_id 仅搜索当前群。",
                parameters=ToolInputSchema(
                    type="object",
                    properties={
                        "query": {
                            "type": "string",
                            "description": "搜索关键词，可以是人名、词语或短语"
                        },
                        "days_range": {
                            "type": "integer",
                            "description": "搜索多少天内的记录，默认30天",
                            "default": 30
                        },
                        "limit": {
                            "type": "integer",
                            "description": "最多返回多少条结果，默认15条",
                            "default": 15
                        },
                        "group_id": {
                            "type": "string",
                            "description": "可选，限定群号，仅搜索该群的记录"
                        }
                    },
                    required=["query"]
                ),
                invokeFunc=CallableWrapper(self._keyword_search)
            ))
        
        if self.enable_vector_search:
            tools.append(Tool(
                name="vector_search",
                description="按语义相似度搜索聊天记录。适合模糊搜索、概念性问题、上下文相关的问题。当用户问'之前聊过关于XXX的话题'或'有没有讨论过XXX'时使用。可选传 group_id 仅搜索当前群。",
                parameters=ToolInputSchema(
                    type="object",
                    properties={
                        "query": {
                            "type": "string",
                            "description": "搜索语句，描述你想找的内容"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "最多返回多少条结果，默认10条",
                            "default": 10
                        },
                        "group_id": {
                            "type": "string",
                            "description": "可选，限定群号，仅搜索该群的记录"
                        }
                    },
                    required=["query"]
                ),
                invokeFunc=CallableWrapper(self._vector_search)
            ))
        
        if self.enable_recent_search:
            tools.append(Tool(
                name="recent_chat_search",
                description="搜索最近的对话记录。适合'刚才说了什么'、'最近在聊什么'这类问题。可以限定特定用户。可选传 group_id 仅搜索当前群。",
                parameters=ToolInputSchema(
                    type="object",
                    properties={
                        "user_name": {
                            "type": "string",
                            "description": "可选，限定搜索特定用户的消息，支持模糊匹配"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "最多返回多少条结果，默认20条",
                            "default": 20
                        },
                        "hours": {
                            "type": "integer",
                            "description": "搜索多少小时内的记录，默认24小时",
                            "default": 24
                        },
                        "group_id": {
                            "type": "string",
                            "description": "可选，限定群号，仅搜索该群的记录"
                        }
                    },
                    required=[]
                ),
                invokeFunc=CallableWrapper(self._recent_chat_search)
            ))
        
        self.logger.info(f"SearchToolProvider: 提供了 {len(tools)} 个搜索工具")
        return {"tools": tools}
