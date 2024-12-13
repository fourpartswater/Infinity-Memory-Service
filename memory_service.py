import infinity
from infinity import NetworkAddress
from datetime import datetime
import json
from typing import List, Dict, Any, Optional
import aiohttp
import certifi
import ssl
from config import MemoryServiceConfig
import re
import asyncio
import time


class InfinityMemoryService:
    def __init__(self, config: Optional[MemoryServiceConfig] = None):
        """初始化记忆服务"""
        self.config = config or MemoryServiceConfig()
        self._init_connection()
        self._table_cache = {}
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self._closed = False

    def _init_connection(self):
        """初始化数据库连接"""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                self.infinity_obj = infinity.connect(
                    NetworkAddress(self.config.INFINITY_HOST, self.config.INFINITY_PORT)
                )
                self._init_database()
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise e

    def _reconnect(self):
        """重新连接数据库"""
        try:
            self.infinity_obj.disconnect()
        except:
            pass
        time.sleep(1)  # 等待一秒后重连
        self._init_connection()

    def _ensure_connection(self):
        """确保连接可用"""
        try:
            self.infinity_obj.list_databases()
        except Exception as e:
            if "TSocket read 0 bytes" in str(e) or "Connection refused" in str(e):
                self._reconnect()
                # 验证重连是否成功
                try:
                    self.infinity_obj.list_databases()
                except Exception as e2:
                    raise Exception(f"Failed to reconnect: {e2}")

    def _process_row(self, row) -> Dict:
        """处理单行数据"""
        try:
            # 确保所有字段都被转换为字符串
            memory_id = str(row['memory_id']) if 'memory_id' in row else None
            content = str(row['content']) if 'content' in row else None
            timestamp = str(row['timestamp']) if 'timestamp' in row else None

            # 处理 JSON 字段
            metadata_str = str(row['metadata']) if 'metadata' in row else '{}'
            tags_str = str(row['tags']) if 'tags' in row else '[]'

            # 解析 JSON 字段
            try:
                metadata = json.loads(metadata_str)
            except:
                metadata = {}

            try:
                tags = json.loads(tags_str)
            except:
                tags = []

            return {
                "memory_id": memory_id,
                "content": content,
                "timestamp": timestamp,
                "metadata": metadata,
                "tags": tags,
                "score": float(row['_score']) if '_score' in row else None
            }
        except Exception as e:
            print(f"Error processing row: {e}")
            return None

    def _init_database(self):
        """初始化数据库"""
        try:
            # 首先检查数据库是否存在
            databases = self.infinity_obj.list_databases()
            database_exists = False
            # 使用 db_names 字段检查数据库是否存在
            if hasattr(databases, 'db_names'):
                database_exists = self.config.DEFAULT_DATABASE in databases.db_names
            if not database_exists:
                # 数据库不存在时创建
                self.infinity_obj.create_database(self.config.DEFAULT_DATABASE)
            # 获取数据库连接
            self.db = self.infinity_obj.get_database(self.config.DEFAULT_DATABASE)
        except infinity.common.InfinityException as e:
            if "Duplicated db entry" in str(e):
                # 如果数据库已存在，直接获取连接
                self.db = self.infinity_obj.get_database(self.config.DEFAULT_DATABASE)
            else:
                # 其他错误则抛出
                raise e

    def _get_table_name(self, tenant_id: str, project_id: str) -> str:
        """生成表名"""
        # 确保tenant_id和project_id只包含安全的字符
        safe_tenant_id = re.sub(r'[^a-zA-Z0-9_]', '_', tenant_id)
        safe_project_id = re.sub(r'[^a-zA-Z0-9_]', '_', project_id)
        return f"{self.config.TABLE_PREFIX}{safe_tenant_id}_{safe_project_id}"

    def _get_table(self, tenant_id: str, project_id: str):
        """获取或创建表"""
        table_name = self._get_table_name(tenant_id, project_id)
        if table_name not in self._table_cache:
            try:
                # 尝试创建新表
                table = self.db.create_table(
                    table_name,
                    {
                        "memory_id": {"type": "varchar"},
                        "content": {"type": "varchar"},
                        "embedding": {"type": f"vector,{self.config.EMBEDDING_DIM},float"},
                        "timestamp": {"type": "timestamp"},
                        "metadata": {"type": "varchar"},
                        "tags": {"type": "varchar"}
                    }
                )
                # 创建索引
                table.create_index(
                    f"{table_name}_embedding_idx",
                    ["embedding"],
                    index_type="hnsw",
                    params={
                        "M": self.config.HNSW_M,
                        "ef_construction": self.config.HNSW_EF_CONSTRUCTION
                    }
                )
                table.create_index(
                    f"{table_name}_content_idx",
                    ["content"],
                    index_type="fulltext",
                    params={"analyzer": "standard"}
                )
            except Exception as e:
                # 如果表已存在，获取现有表
                table = self.db.get_table(table_name)
            self._table_cache[table_name] = table
        return self._table_cache[table_name]

    async def _get_embedding(self, text: str) -> List[float]:
        """调用外部向量化服务获取文本的向量表示"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.EMBEDDING_API_KEY}"
        }
        payload = {
            "input": text,
            "model": self.config.EMBEDDING_MODEL
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    self.config.EMBEDDING_SERVICE_URL,
                    headers=headers,
                    json=payload,
                    ssl=self.ssl_context
            ) as response:
                if response.status != 200:
                    raise Exception(f"Embedding service error: {await response.text()}")
                result = await response.json()
                return result['data'][0]['embedding']

    async def add_memory(self,
                         tenant_id: str,
                         project_id: str,
                         content: str,
                         metadata: Dict[str, Any] = None,
                         tags: List[str] = None) -> str:
        """添加新记忆"""
        table = self._get_table(tenant_id, project_id)
        embedding = await self._get_embedding(content)
        memory_id = f"mem_{tenant_id}_{project_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        # 将 datetime 转换为 YYYY-MM-DD HH:MM:SS 格式字符串
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        table.insert([{
            "memory_id": memory_id,
            "content": content,
            "embedding": embedding,
            "timestamp": timestamp,  # 使用 YYYY-MM-DD HH:MM:SS 格式
            "metadata": json.dumps(metadata or {}),
            "tags": json.dumps(tags or [])
        }])
        return memory_id

    async def batch_add_memories(self,
                                 tenant_id: str,
                                 project_id: str,
                                 memories: List[Dict[str, Any]]) -> List[str]:
        """批量添加记忆"""
        table = self._get_table(tenant_id, project_id)
        memory_ids = []
        batch_size = 10  # 减小批次大小

        try:
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                batch_data = []

                # 并行获取embeddings
                embedding_tasks = [
                    self._get_embedding(memory['content'])
                    for memory in batch
                ]
                embeddings = await asyncio.gather(*embedding_tasks)

                for j, (memory, embedding) in enumerate(zip(batch, embeddings)):
                    memory_id = f"mem_{tenant_id}_{project_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{i}_{j}"
                    memory_ids.append(memory_id)

                    batch_data.append({
                        "memory_id": memory_id,
                        "content": memory['content'],
                        "embedding": embedding,
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "metadata": json.dumps(memory.get('metadata', {})),
                        "tags": json.dumps(memory.get('tags', []))
                    })

                table.insert(batch_data)
                await asyncio.sleep(0.1)  # 添加短暂延迟

            return memory_ids
        except Exception as e:
            print(f"Error in batch insert: {e}")
            return []

    async def get_memory(self,
                         tenant_id: str,
                         project_id: str,
                         memory_id: str) -> Optional[Dict]:
        """获取指定记忆"""
        self._ensure_connection()
        table = self._get_table(tenant_id, project_id)
        try:
            result = table.filter(f"memory_id = '{memory_id}'").output(["*"]).to_pl()
            if result and len(result) > 0:
                processed_row = self._process_row(result[0])
                return processed_row if processed_row else None
            return None
        except Exception as e:
            print(f"Error retrieving memory: {e}")
            return None

    async def list_memories(self,
                            tenant_id: str,
                            project_id: str,
                            limit: int = 10,
                            offset: int = 0) -> List[Dict]:
        """列出所有记忆"""
        self._ensure_connection()
        table = self._get_table(tenant_id, project_id)
        try:
            results = table.output(["*"]).limit(limit).offset(offset).to_pl()
            memories = []

            if results and len(results) > 0:
                for row in results:
                    processed_row = self._process_row(row)
                    if processed_row:
                        memories.append(processed_row)
            return memories
        except Exception as e:
            print(f"Error listing memories: {e}")
            return []

    async def search_memory(self,
                            tenant_id: str,
                            project_id: str,
                            query_text: Optional[str] = None,
                            filter_metadata: Optional[Dict[str, Any]] = None,
                            filter_tags: Optional[List[str]] = None,
                            limit: int = 10) -> List[Dict]:
        """搜索记忆"""
        self._ensure_connection()
        table = self._get_table(tenant_id, project_id)
        try:
            if query_text:
                # 获取查询文本的向量表示
                query_embedding = await self._get_embedding(query_text)

                # 使用 fusion 搜索
                search_query = (table
                                .match_dense("embedding", query_embedding, "float", "ip", limit)  # 向量搜索
                                .match_text("content", query_text, limit)  # 文本搜索
                                .fusion(["_score1", "_score2"], [0.5, 0.5], limit))  # 融合结果
            else:
                search_query = table.output(["*"]).limit(limit)

            # 添加过滤条件
            if filter_metadata:
                for key, value in filter_metadata.items():
                    search_query = search_query.filter(f"metadata LIKE '%\"{key}\": \"{value}\"%'")

            if filter_tags:
                for tag in filter_tags:
                    search_query = search_query.filter(f"tags LIKE '%{tag}%'")

            results = search_query.to_pl()
            memories = []

            if results and len(results) > 0:
                for row in results:
                    processed_row = self._process_row(row)
                    if processed_row:
                        memories.append(processed_row)
            return memories
        except Exception as e:
            print(f"Error searching memories: {e}")
            return []

    async def update_memory(self,
                            tenant_id: str,
                            project_id: str,
                            memory_id: str,
                            content: Optional[str] = None,
                            metadata: Optional[Dict[str, Any]] = None,
                            tags: Optional[List[str]] = None) -> bool:
        """更新记忆"""
        self._ensure_connection()
        table = self._get_table(tenant_id, project_id)
        try:
            update_data = {}

            if content is not None:
                embedding = await self._get_embedding(content)
                update_data.update({
                    "content": content,
                    "embedding": embedding
                })

            if metadata is not None:
                update_data["metadata"] = json.dumps(metadata)

            if tags is not None:
                update_data["tags"] = json.dumps(tags)

            if update_data:
                table.update(
                    cond=f"memory_id = '{memory_id}'",
                    data=update_data
                )
            return True
        except Exception as e:
            print(f"Error updating memory: {e}")
            return False

    async def delete_memory(self,
                            tenant_id: str,
                            project_id: str,
                            memory_id: str) -> bool:
        """删除指定记忆"""
        table = self._get_table(tenant_id, project_id)
        try:
            table.filter(f"memory_id = '{memory_id}'").delete()
            return True
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False

    def close(self):
        """显式关闭连接"""
        if not self._closed:
            try:
                self.infinity_obj.disconnect()
                self._closed = True
            except Exception as e:
                print(f"Warning: Error during disconnect: {e}")

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.close()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def close(self):
        """异步关闭连接"""
        if not hasattr(self, '_closed') or not self._closed:
            try:
                self.infinity_obj.disconnect()
                self._closed = True
            except Exception as e:
                print(f"Warning: Error during disconnect: {e}")