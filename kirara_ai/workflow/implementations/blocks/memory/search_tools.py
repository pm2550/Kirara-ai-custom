"""
搜索工具提供者 Block
将搜索功能封装成 Tool，让 AI 自主决定搜索策略
"""

import asyncio
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, List, Optional

import requests

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

    WEB_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }
    MAX_WEB_RESULTS_WITH_FULLTEXT = 3
    MAX_WEB_EXCERPT_CHARS = 1200
    
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

    @classmethod
    def _is_noise_line(cls, line: str) -> bool:
        if not line:
            return True
        if re.fullmatch(r"t\d[\w_.:-]{0,40}", line):
            return True
        if re.fullmatch(r"\d+(\.\d+)?\s?(KB|MB|GB|TB)", line, re.IGNORECASE):
            return True
        if re.fullmatch(r"[A-Za-z0-9_.:-]{1,40}", line) and " " not in line:
            return True

        meaningful_chars = sum(
            1
            for ch in line
            if ("\u4e00" <= ch <= "\u9fff") or ch.isalpha()
        )
        if meaningful_chars == 0:
            return True
        if len(line) < 12 and meaningful_chars < 4 and " " not in line:
            return True
        return False

    @classmethod
    def _extract_html_text(cls, html_text: str) -> str:
        """粗略提取网页正文，尽量保留可读段落并压掉导航、脚本等噪声。"""
        cleaned = re.sub(r"(?is)<!--.*?-->", " ", html_text)
        cleaned = re.sub(
            r"(?is)<(script|style|noscript|svg|iframe|canvas|form|footer|nav|aside).*?>.*?</\1>",
            " ",
            cleaned,
        )
        cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
        cleaned = re.sub(r"(?i)</(p|div|article|section|main|li|ul|ol|h[1-6]|tr|table|blockquote)>", "\n", cleaned)
        cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
        cleaned = html.unescape(cleaned)

        lines = []
        seen = set()
        for raw_line in cleaned.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line:
                continue
            if len(line) < 8 and not re.search(r"[。！？.!?]", line):
                continue
            if cls._is_noise_line(line):
                continue
            if line in seen:
                continue
            seen.add(line)
            lines.append(line)

        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    def _fetch_page_excerpt(self, url: str) -> str:
        """抓取网页并提取正文摘录。"""
        if not url:
            return ""

        resp = requests.get(
            url,
            headers=self.WEB_HEADERS,
            timeout=8,
            allow_redirects=True,
        )
        resp.raise_for_status()

        content_type = (resp.headers.get("content-type") or "").lower()
        if "text/html" in content_type or "application/xhtml+xml" in content_type or not content_type:
            text = self._extract_html_text(resp.text)
        elif content_type.startswith("text/"):
            text = resp.text
        else:
            return ""

        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) > self.MAX_WEB_EXCERPT_CHARS:
            text = text[:self.MAX_WEB_EXCERPT_CHARS].rsplit("\n", 1)[0].rstrip()
        return text

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
        enable_web_search: Annotated[
            bool,
            ParamMeta(
                label="启用网络搜索",
                description="是否启用 SearXNG 网络搜索功能"
            )
        ] = False,
        searxng_url: Annotated[
            str,
            ParamMeta(
                label="SearXNG 地址",
                description="SearXNG 搜索引擎 API 地址"
            )
        ] = "http://localhost:8888",
    ):
        self.memory_dir = memory_dir
        self.enable_vector_search = enable_vector_search
        self.enable_keyword_search = enable_keyword_search
        self.enable_recent_search = enable_recent_search
        self.enable_web_search = enable_web_search
        self.searxng_url = searxng_url
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

    async def _web_search(self, tool_call: ToolCall) -> LLMToolResultContent:
        """SearXNG 网络搜索实现"""
        args = tool_call.function.arguments or {}
        query = args.get("query", "")
        limit = args.get("limit", 5)

        try:
            def _do_search():
                resp = requests.get(
                    f"{self.searxng_url}/search",
                    params={"q": query, "format": "json", "language": "zh-CN"},
                    timeout=10
                )
                resp.raise_for_status()
                return resp.json()

            data = await asyncio.to_thread(_do_search)
            results = data.get("results", [])[:limit]

            if not results:
                result_text = f"[网络搜索] 没有找到关于「{query}」的结果。"
            else:
                fetch_count = min(len(results), self.MAX_WEB_RESULTS_WITH_FULLTEXT)
                fetch_tasks = [
                    asyncio.to_thread(self._fetch_page_excerpt, r.get("url", ""))
                    for r in results[:fetch_count]
                ]
                fetched_pages = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                lines = [f"[网络搜索] 找到 {len(results)} 条结果，已读取前 {fetch_count} 个网页正文:\n"]
                for i, r in enumerate(results, 1):
                    title = r.get("title", "")
                    url = r.get("url", "")
                    snippet = (r.get("content", "") or "")[:180]
                    lines.append(f"{i}. {title}\n   链接: {url}")
                    if snippet:
                        lines.append(f"   搜索摘要: {snippet}")

                    if i <= fetch_count:
                        page_excerpt = fetched_pages[i - 1]
                        if isinstance(page_excerpt, Exception):
                            self.logger.warning(f"Fetch page failed for {url}: {page_excerpt}")
                        elif page_excerpt:
                            lines.append(f"   网页正文摘录: {page_excerpt}")

                result_text = "\n".join(lines)
        except Exception as e:
            self.logger.error(f"Web search error: {e}")
            result_text = f"网络搜索失败: {str(e)}"
            return LLMToolResultContent(
                id=tool_call.id, name=tool_call.function.name,
                content=[TextContent(text=result_text)], isError=True
            )

        return LLMToolResultContent(
            id=tool_call.id, name=tool_call.function.name,
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
        
        if self.enable_web_search:
            tools.append(Tool(
                name="web_search",
                description="搜索互联网获取实时信息和链接，并进一步抓取网页正文摘录。当用户需要查找网址、产品链接、新闻、教程等网络信息时使用。返回标题、链接、搜索摘要和网页正文摘录。",
                parameters=ToolInputSchema(
                    type="object",
                    properties={
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果数量，默认5",
                            "default": 5
                        }
                    },
                    required=["query"]
                ),
                invokeFunc=CallableWrapper(self._web_search)
            ))

        self.logger.info(f"SearchToolProvider: 提供了 {len(tools)} 个搜索工具")
        return {"tools": tools}
