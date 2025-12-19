#!/usr/bin/env python3
"""测试历史摘要功能"""
import json
from pathlib import Path
from datetime import datetime, timedelta

# 模拟 MemoryEntry
class MockEntry:
    def __init__(self, content, timestamp):
        self.content = content
        self.timestamp = timestamp
        self.sender = None
        self.metadata = {"_media_ids": [], "_tool_calls": [], "_tool_results": []}
    
    def __str__(self):
        return self.content

# 测试数据
def create_test_entries():
    entries = []
    base_time = datetime.now() - timedelta(days=10)
    
    for i in range(100):
        time_offset = timedelta(hours=i)
        content = f"用户{i}: 测试消息{i}\n你回答: 收到{i}"
        entries.append(MockEntry(content, base_time + time_offset))
    
    return entries

# 测试摘要加载
def test_summary_loading():
    print("=" * 60)
    print("测试历史摘要功能")
    print("=" * 60)
    
    # 创建测试摘要
    summary_dir = Path("./data/memory")
    summary_dir.mkdir(parents=True, exist_ok=True)
    
    test_scope = "test_scope_12345"
    summary_path = summary_dir / f"{test_scope}_summary.json"
    
    summary_data = {
        "summary": "这是一段测试摘要。包含了前60条对话的核心内容：主要讨论了游戏、工作和生活话题。",
        "entry_count": 60,
        "generated_at": datetime.now().isoformat()
    }
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 创建测试摘要: {summary_path}")
    
    # 测试加载逻辑
    entries = create_test_entries()
    context = {"scope_key": test_scope}
    
    print(f"✅ 创建了 {len(entries)} 条测试记录")
    
    # 模拟 decomposer 逻辑
    result_lines = []
    
    if len(entries) > 60:
        # 尝试加载摘要
        if summary_path.exists():
            with open(summary_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            
            old_count = loaded.get("entry_count", 0)
            summary_text = loaded.get("summary", "")
            
            result_lines.append(f"[更早的 {old_count} 条对话摘要]")
            result_lines.append(summary_text)
            result_lines.append("[以下是最近的详细对话]")
            
            print(f"✅ 成功加载摘要（{old_count} 条）")
    
    # 显示最近的记录
    recent = entries[-40:]
    result_lines.append(f"-- 最近 {len(recent)} 条详细记录 --")
    for entry in recent[:3]:  # 只显示前3条作为示例
        result_lines.append(str(entry))
    result_lines.append("...")
    
    print("\n" + "=" * 60)
    print("最终输出效果预览：")
    print("=" * 60)
    for line in result_lines:
        print(line)
    
    # 清理
    summary_path.unlink()
    print(f"\n✅ 测试完成，已清理测试文件")

if __name__ == "__main__":
    test_summary_loading()
