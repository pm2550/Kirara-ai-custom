"""
历史摘要管理模块
负责生成和存储对话历史的压缩摘要
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

class HistorySummaryManager:
    """历史摘要管理器"""
    
    def __init__(self, storage_dir: str = "./data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def get_summary_path(self, scope_key: str) -> Path:
        """获取摘要文件路径"""
        return self.storage_dir / f"{scope_key}_summary.json"
    
    def load_summary(self, scope_key: str) -> Optional[Dict[str, Any]]:
        """加载已有的摘要"""
        path = self.get_summary_path(scope_key)
        if not path.exists():
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def save_summary(self, scope_key: str, summary_text: str, entry_count: int):
        """保存摘要"""
        path = self.get_summary_path(scope_key)
        data = {
            "summary": summary_text,
            "entry_count": entry_count,
            "generated_at": datetime.now().isoformat(),
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def should_regenerate(self, scope_key: str, current_entry_count: int) -> bool:
        """判断是否需要重新生成摘要"""
        summary = self.load_summary(scope_key)
        if not summary:
            return current_entry_count > 60  # 首次生成阈值
        
        # 如果新增了 20 条以上，重新生成
        return current_entry_count - summary.get("entry_count", 0) > 20
    
    def build_summary_prompt(self, entries: List[Any], max_entries: int = 30) -> str:
        """构建用于生成摘要的文本"""
        lines = []
        for entry in entries[:max_entries]:
            try:
                content = str(entry).strip()
                if content:
                    lines.append(content)
            except Exception:
                continue
        
        return "\n".join(lines)
