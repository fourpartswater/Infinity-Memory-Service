The memory layer service based on the Infinity vector database provides high-performance memory storage and retrieval capabilities for LLM applications. It supports multi-tenant and multi-project memory management, which can be easily integrated into existing AI applications.

Characteristic

Realise efficient vector retrieval based on Infinity vector database

Support multi-tenant and multi-project isolation

Automatic vectorisation processing (using external Embedding service)

Support hybrid search (vector + full text)

Complete CRUD operation interface

Asynchronous operation support

Simple configuration management

Fix

Make sure that the Infinity database is installed and working normally

Installation dependency:

Pip install -r requirements.txt

Deploy

Create a .env file:

# Infinity Configuration

INFINITY_HOST=localhost

INFINITY_PORT=23817

# Vector service configuration

EMBEDDING_SERVICE_URL=https://your-embedding-service.com/v1/embeddings

EMBEDDING_API_KEY=your-api-key

EMBEDDING_MODEL=text-embedding-3-small

EMBEDDING_DIM=1536

# Database configuration

Default_Database=memory_store

TABLE_PREFIX=memories_

Basic use

From memory_service import InfinityMemoryService

From config import MemoryServiceConfig

Import async

Async def main ():

# Initialise the service

Config = MemoryServiceConfig()

Memory_service = InfinityMemoryService(config)

# Add memories

Memory_id = await memory_service.add_memory(

Tenant_id="tenant_001",

Project_id="project_001",

content="This is an important memory",

Metadata={"source": "conversation"},

Tags=["important"]

)

# Search memory

Results = await memory_service.search_memory(

Tenant_id="tenant_001",

Project_id="project_001",

Query_text="important memory"

)

If __name__ == "__main__":

Asyncio.run(main())

Examples of FastAPI integration

From fastapi import FastAPI, Depends

From memory_service import InfinityMemoryService

From config import MemoryServiceConfig

From typing import Optional, List, Dict

App = FastAPI()

# Service single case

Memory_service = InfinityMemoryService(MemoryServiceConfig())

# Dependent injection

Async def get_memory_service():

Return memory_service

@App.post("/memories/{tenant_id}/{project_id}")

Async def create_memory(

Tenant_id: str,

Project_id: str,

Content: str,

Metadata: Optional[Dict] = None,

Tags: Optional[List[str]] = None,

Service: InfinityMemoryService = Depends(get_memory_service)

):

Memory_id = await service.add_memory(

Tenant_id=tenant_id,

Project_id=project_id,

Content=content,

Metadata=metadata,

Tags=tags

)

Return {"memory_id": memory_id}

@App.get("/memories/{tenant_id}/{project_id}/search")

Async def search_memories(

Tenant_id: str,

Project_id: str,

Query: str,

Tags: Optional[List[str]] = None,

Limit: int = 10,

Service: InfinityMemoryService = Depends(get_memory_service)

):

Results = await service.search_memory(

Tenant_id=tenant_id,

Project_id=project_id,

Query_text=query,

Filter_tags=tags,

Limit=limit

)

Return {"results": results}

Examples of LangChain integration

From langchain.memory import BaseMemory

From typing import Dict, List, Any

Class InfinityMemory(BaseMemory):

Memory_service: InfinityMemoryService

Tenner_id: str

Project_id: str

Def __init__(self, memory_service: InfinityMemoryService, tenant_id: str, project_id: str):

Self.memory_service = memory_service

Self.tenant_id = tenant_id

Self.project_id = project_id

Async def add_memory(self, text: str, metadata: Dict[str, Any] = None):

Await self.memory_service.add_memory(

Tenant_id=self.tenant_id,

Project_id=self.project_id,

Content=text,

Metadata=metadata

)

Async def get_relevant_memories(self, query: str, k: int = 5) -> List[Dict]:

Return await self.memory_service.search_memory(

Tenant_id=self.tenant_id,

Project_id=self.project_id,

Query_text=query,

Limit=k

)

API document

Core method

Add_memory: Add new memories

Search_memory: search memory

Get_memory: Get the specified memory

List_memories: List memories

Update_memory: update memory

Delete_memory: Delete memory

For detailed method description and parameters, please refer to the code document.

Performance optimisation suggestions

1. Connection pool management

# Use the connection pool in the FastAPI application

From contextlib import asynccontextmanager

MemoryServicePool class:

Def __init__(self, config: MemoryServiceConfig, pool_size: int = 10):

Self.pool = [InfinityMemoryService(config) for _ in range(pool_size)]

Self._index = 0

@Asynccontextmanager

Async def get_service(self):

Service = self.pool[self._index]

Self._index = (self._index + 1) % len(self.pool)

Try:

Yield service

Finally:

Pass # If necessary, you can add cleaning logic here.

Two. Batch operation

# Batch add memory examples

Async def batch_add_memories(

Service: InfinityMemoryService,

Tenant_id: str,

Project_id: str,

Memories: List[Dict]

):

Tasks = []

For memory in memories:

Task = service.add_memory(

Tenant_id=tenant_id,

Project_id=project_id,

Content=memory["content"],

Metadata=memory.get("metadata"),

Tags=memory.get("tags")

)

Tasks.append(task)

Return await asyncio.gather(*tasks)

Contribute

Welcome to submit Issue and Pull Request!



# Infinity Memory Service

基于 Infinity 向量数据库实现的记忆层服务，为 LLM 应用提供高性能的记忆存储和检索能力。支持多租户、多项目的记忆管理，可以轻松集成到现有的 AI 应用中。

## 特性

- 基于 Infinity 向量数据库实现高效的向量检索
- 支持多租户和多项目隔离
- 自动向量化处理（使用外部 Embedding 服务）
- 支持混合搜索（向量 + 全文）
- 完整的 CRUD 操作接口
- 异步操作支持
- 简单的配置管理

## 安装

1. 确保已安装 Infinity 数据库并正常运行

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 配置
1. 创建 .env 文件：
```
# Infinity 配置
INFINITY_HOST=localhost
INFINITY_PORT=23817

# 向量服务配置
EMBEDDING_SERVICE_URL=https://your-embedding-service.com/v1/embeddings
EMBEDDING_API_KEY=your-api-key
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# 数据库配置
DEFAULT_DATABASE=memory_store
TABLE_PREFIX=memories_
```

## 基础使用
```python
from memory_service import InfinityMemoryService
from config import MemoryServiceConfig
import asyncio

async def main():
    # 初始化服务
    config = MemoryServiceConfig()
    memory_service = InfinityMemoryService(config)
    
    # 添加记忆
    memory_id = await memory_service.add_memory(
        tenant_id="tenant_001",
        project_id="project_001",
        content="这是一条重要的记忆",
        metadata={"source": "conversation"},
        tags=["important"]
    )
    
    # 搜索记忆
    results = await memory_service.search_memory(
        tenant_id="tenant_001",
        project_id="project_001",
        query_text="重要的记忆"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## FastAPI 集成示例 

```python
from fastapi import FastAPI, Depends
from memory_service import InfinityMemoryService
from config import MemoryServiceConfig
from typing import Optional, List, Dict

app = FastAPI()

# 服务单例
memory_service = InfinityMemoryService(MemoryServiceConfig())

# 依赖注入
async def get_memory_service():
    return memory_service

@app.post("/memories/{tenant_id}/{project_id}")
async def create_memory(
    tenant_id: str,
    project_id: str,
    content: str,
    metadata: Optional[Dict] = None,
    tags: Optional[List[str]] = None,
    service: InfinityMemoryService = Depends(get_memory_service)
):
    memory_id = await service.add_memory(
        tenant_id=tenant_id,
        project_id=project_id,
        content=content,
        metadata=metadata,
        tags=tags
    )
    return {"memory_id": memory_id}

@app.get("/memories/{tenant_id}/{project_id}/search")
async def search_memories(
    tenant_id: str,
    project_id: str,
    query: str,
    tags: Optional[List[str]] = None,
    limit: int = 10,
    service: InfinityMemoryService = Depends(get_memory_service)
):
    results = await service.search_memory(
        tenant_id=tenant_id,
        project_id=project_id,
        query_text=query,
        filter_tags=tags,
        limit=limit
    )
    return {"results": results}
```

## LangChain 集成示例
```python
from langchain.memory import BaseMemory
from typing import Dict, List, Any

class InfinityMemory(BaseMemory):
    memory_service: InfinityMemoryService
    tenant_id: str
    project_id: str
    
    def __init__(self, memory_service: InfinityMemoryService, tenant_id: str, project_id: str):
        self.memory_service = memory_service
        self.tenant_id = tenant_id
        self.project_id = project_id
    
    async def add_memory(self, text: str, metadata: Dict[str, Any] = None):
        await self.memory_service.add_memory(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            content=text,
            metadata=metadata
        )
    
    async def get_relevant_memories(self, query: str, k: int = 5) -> List[Dict]:
        return await self.memory_service.search_memory(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            query_text=query,
            limit=k
        )
```

## API 文档
### 核心方法
* add_memory: 添加新记忆
* search_memory: 搜索记忆
* get_memory: 获取指定记忆
* list_memories: 列出记忆
* update_memory: 更新记忆
* delete_memory: 删除记忆

  详细的方法说明和参数请参考代码文档。

## 性能优化建议
### 1. 连接池管理
```python
# 在 FastAPI 应用中使用连接池
from contextlib import asynccontextmanager

class MemoryServicePool:
    def __init__(self, config: MemoryServiceConfig, pool_size: int = 10):
        self.pool = [InfinityMemoryService(config) for _ in range(pool_size)]
        self._index = 0
    
    @asynccontextmanager
    async def get_service(self):
        service = self.pool[self._index]
        self._index = (self._index + 1) % len(self.pool)
        try:
            yield service
        finally:
            pass # 如果需要，这里可以添加清理逻辑
```

### 2.批量操作
```python
# 批量添加记忆示例
async def batch_add_memories(
    service: InfinityMemoryService,
    tenant_id: str,
    project_id: str,
    memories: List[Dict]
):
    tasks = []
    for memory in memories:
        task = service.add_memory(
            tenant_id=tenant_id,
            project_id=project_id,
            content=memory["content"],
            metadata=memory.get("metadata"),
            tags=memory.get("tags")
        )
        tasks.append(task)
    return await asyncio.gather(*tasks)
```

## 贡献
欢迎提交 Issue 和 Pull Request！
