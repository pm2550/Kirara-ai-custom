"""
向量记忆管理模块
使用 Chroma + text2vec-base-chinese 实现聊天记录的向量化存储和检索
"""

import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_VECTOR_DIR = BASE_DIR /"vector_db"


class VectorMemoryManager:
    """向量记忆管理器 (单例模式)"""
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        初始化向量记忆管理器
        
        Args:
            persist_directory: 向量数据库持久化目录
        """
        # 单例模式: 只初始化一次
        if VectorMemoryManager._initialized:
            return
        
        base_path = Path(persist_directory).expanduser() if persist_directory else DEFAULT_VECTOR_DIR
        self.persist_directory = base_path.resolve()
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # 初始化中文 Embedding 模型
        print("Loading text2vec-base-chinese model...")
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=str(BASE_DIR / "models" / "text2vec-base-chinese")
        )
        print("[OK] Model loaded successfully!")
        
        # 初始化 Chroma 客户端 (使用 Settings 确保正确初始化)
        try:
            from chromadb.config import Settings
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        except ImportError:
            # 旧版本 Chroma
            self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # 创建或获取集合
        self.collection = self.client.get_or_create_collection(
            name="chat_history",
            embedding_function=self.embedding_fn,
            metadata={"description": "QQ群聊天记录向量化存储"}
        )
        
        VectorMemoryManager._initialized = True
        print("[OK] VectorMemoryManager initialized as singleton!")
    
    def add_message(
        self,
        message_id: str,
        content: str,
        user_id: str,
        user_name: str,
        group_id: str,
        timestamp: Optional[str] = None
    ):
        """
        添加一条聊天记录到向量库
        
        Args:
            message_id: 消息唯一 ID
            content: 消息内容
            user_id: 用户 QQ 号
            user_name: 用户昵称/群名片
            group_id: 群号
            timestamp: 时间戳 (ISO格式)
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 构建完整文档 (包含用户信息,便于搜索)
        document = f"[{user_name}] {content}"
        
        try:
            self.collection.add(
                documents=[document],
                ids=[message_id],
                metadatas=[{
                    "user_id": user_id,
                    "user_name": user_name,
                    "group_id": group_id,
                    "timestamp": timestamp,
                    "content": content  # 保留原始内容
                }]
            )
            # 强制持久化
            try:
                self.client.persist()
            except AttributeError:
                pass  # 新版本 Chroma 自动持久化
        except Exception as e:
            print(f"[ERROR] Failed to add message to vector DB: {e}")
            raise  # 重新抛出异常,让调用方知道失败了
    
    def search(
        self,
        query: str,
        n_results: int = 20,
        user_filter: Optional[str] = None,
        group_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        搜索相关聊天记录
        
        Args:
            query: 搜索查询
            n_results: 返回结果数量
            user_filter: 按用户昵称过滤
            group_filter: 按群号过滤
            
        Returns:
            搜索结果列表,每条包含: content, user_name, user_id, timestamp, distance
        """
        # 构建过滤条件
        where = {}
        if user_filter:
            where["user_name"] = user_filter
        if group_filter:
            where["group_id"] = group_filter
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where if where else None
            )
            
            # 格式化结果
            formatted_results = []
            if results and results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    metadata = results['metadatas'][0][i]
                    formatted_results.append({
                        "content": metadata.get("content", ""),
                        "user_name": metadata.get("user_name", ""),
                        "user_id": metadata.get("user_id", ""),
                        "group_id": metadata.get("group_id", ""),
                        "timestamp": metadata.get("timestamp", ""),
                        "distance": results['distances'][0][i] if results.get('distances') else 0
                    })
            
            return formatted_results
        
        except Exception as e:
            print(f"[WARN] Vector search failed: {e}")
            return []
    
    def search_by_user(
        self,
        user_name: str,
        n_results: int = 20,
        group_id: Optional[str] = None
    ) -> List[Dict]:
        """
        搜索特定用户的最近消息
        
        Args:
            user_name: 用户昵称
            n_results: 返回结果数量
            group_id: 限定群号
            
        Returns:
            该用户的消息列表
        """
        where = {"user_name": user_name}
        if group_id:
            where["group_id"] = group_id
        
        try:
            # 使用空查询 + 过滤器获取用户所有消息
            results = self.collection.get(
                where=where,
                limit=n_results
            )
            
            formatted_results = []
            if results and results['metadatas']:
                for metadata in results['metadatas']:
                    formatted_results.append({
                        "content": metadata.get("content", ""),
                        "user_name": metadata.get("user_name", ""),
                        "user_id": metadata.get("user_id", ""),
                        "timestamp": metadata.get("timestamp", "")
                    })
            
            return formatted_results
        
        except Exception as e:
            print(f"⚠️ 按用户搜索失败: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """获取向量库统计信息"""
        return {
            "total_messages": self.collection.count(),
            "persist_directory": str(self.persist_directory)
        }


# 全局单例
_vector_manager: Optional[VectorMemoryManager] = None


def get_vector_manager() -> VectorMemoryManager:
    """获取向量管理器单例"""
    global _vector_manager
    if _vector_manager is None:
        _vector_manager = VectorMemoryManager()
    return _vector_manager


if __name__ == "__main__":
    # Test code
    print("Initializing vector memory manager...")
    manager = VectorMemoryManager()
    
    # Add test data
    print("\nAdding test data...")
    manager.add_message(
        message_id="test_001",
        content="I want to play Genshin today",
        user_id="123456",
        user_name="Lu Master",
        group_id="123072262"
    )
    
    manager.add_message(
        message_id="test_002",
        content="Stayed up late last night",
        user_id="789012",
        user_name="Gao Master",
        group_id="123072262"
    )
    
    manager.add_message(
        message_id="test_003",
        content="dds You are all losers",
        user_id="345678",
        user_name="Thunder God Lei",
        group_id="123072262"
    )
    
    # Test search
    print("\nTesting search: 'What did Lu Master say'")
    results = manager.search("What did Lu Master say", n_results=3)
    for r in results:
        print(f"  - [{r['user_name']}]: {r['content']} (similarity: {1-r['distance']:.2f})")
    
    print("\nTesting search: 'stayed up late'")
    results = manager.search("stayed up late", n_results=3)
    for r in results:
        print(f"  - [{r['user_name']}]: {r['content']} (similarity: {1-r['distance']:.2f})")
    
    print("\nStatistics:")
    stats = manager.get_stats()
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Storage path: {stats['persist_directory']}")

