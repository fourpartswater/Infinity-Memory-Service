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


class InfinityMemoryService:
    def __init__(self, config: Optional[MemoryServiceConfig] = None):
        """初始化记忆服务"""
        self.config = config or MemoryServiceConfig()
        self.infinity_obj = infinity.connect(
            NetworkAddress(self.config.INFINITY_HOST, self.config.INFINITY_PORT)
        )
        self._init_database()
        self._table_cache = {}  # 缓存已创建的表对象

        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

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

    async def get_memory(self,
                         tenant_id: str,
                         project_id: str,
                         memory_id: str) -> Optional[Dict]:
        """获取指定记忆"""
        table = self._get_table(tenant_id, project_id)
        try:
            # 指定要查询的字段
            result = table.filter(f"memory_id = '{memory_id}'").output(["*"]).to_pl()
            if len(result) > 0:
                row = result[0]
                return {
                    "memory_id": row['memory_id'],
                    "content": row['content'],
                    "timestamp": row['timestamp'],
                    "metadata": json.loads(row['metadata']),
                    "tags": json.loads(row['tags'])
                }
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
        table = self._get_table(tenant_id, project_id)
        try:
            results = table.output(["*"]).limit(limit).offset(offset).to_pl()
            memories = []
            for _, row in results.iterrows():
                memory = {
                    "memory_id": row['memory_id'],
                    "content": row['content'],
                    "timestamp": row['timestamp'],
                    "metadata": json.loads(row['metadata']),
                    "tags": json.loads(row['tags'])
                }
                memories.append(memory)
            return memories
        except Exception as e:
            print(f"Error listing memories: {e}")
            return []

    async def update_memory(self,
                            tenant_id: str,
                            project_id: str,
                            memory_id: str,
                            content: Optional[str] = None,
                            metadata: Optional[Dict[str, Any]] = None,
                            tags: Optional[List[str]] = None) -> bool:
        """更新记忆"""
        table = self._get_table(tenant_id, project_id)
        update_dict = {}

        try:
            if content is not None:
                embedding = await self._get_embedding(content)
                update_dict["content"] = content
                update_dict["embedding"] = embedding
            if metadata is not None:
                update_dict["metadata"] = json.dumps(metadata)
            if tags is not None:
                update_dict["tags"] = json.dumps(tags)

            if update_dict:
                # 使用正确的更新语法
                table.filter(f"memory_id = '{memory_id}'").update(data=update_dict)
                return True
        except Exception as e:
            print(f"Error updating memory: {e}")
        return False

    async def search_memory(self,
                            tenant_id: str,
                            project_id: str,
                            query_text: Optional[str] = None,
                            filter_metadata: Optional[Dict[str, Any]] = None,
                            filter_tags: Optional[List[str]] = None,
                            limit: int = 10) -> List[Dict]:
        """搜索记忆"""
        table = self._get_table(tenant_id, project_id)
        try:
            search_query = table.output(["*"])

            if query_text:
                # 获取查询文本的向量表示
                query_embedding = await self._get_embedding(query_text)

                # 混合搜索：向量 + 全文
                search_query = (search_query
                                .match_dense("embedding", query_embedding, "float", "ip", limit)
                                .match_text("content", query_text, topn=limit))  # 使用 match_text 替代 match_fulltext

            if filter_metadata:
                for key, value in filter_metadata.items():
                    metadata_filter = f'metadata LIKE "%{key}":"{value}%"'
                    search_query = search_query.filter(metadata_filter)

            if filter_tags:
                for tag in filter_tags:
                    tag_filter = f'tags LIKE "%{tag}%"'
                    search_query = search_query.filter(tag_filter)

            results = search_query.to_pl()
            memories = []

            for _, row in results.iterrows():
                memory = {
                    "memory_id": row['memory_id'],
                    "content": row['content'],
                    "timestamp": row['timestamp'],
                    "metadata": json.loads(row['metadata']),
                    "tags": json.loads(row['tags']),
                    "score": row.get('score', None)
                }
                memories.append(memory)

            return memories
        except Exception as e:
            print(f"Error searching memories: {e}")
            return []


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