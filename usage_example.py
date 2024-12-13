import asyncio
import time
from memory_service import InfinityMemoryService
from config import MemoryServiceConfig
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

async def main():
    # 从环境变量或配置文件加载配置
    config = MemoryServiceConfig()

    # 初始化记忆服务
    memory_service = InfinityMemoryService(config)

    # 示例租户和项目
    tenant_id = "tenant_001"
    project_id = "project_001"

    # 添加记忆
    print("Adding memory...")
    start_time = time.time()
    memory_id = await memory_service.add_memory(
        tenant_id=tenant_id,
        project_id=project_id,
        content="这是一个关于Python编程的重要记忆",
        metadata={"source": "conversation", "importance": "high"},
        tags=["python", "programming"]
    )
    end_time = time.time()
    print(f"Memory added with ID: {memory_id} in {end_time - start_time:.4f} seconds")

    # 获取记忆
    print("Retrieving memory...")
    start_time = time.time()
    memory = await memory_service.get_memory(tenant_id, project_id, memory_id)
    end_time = time.time()
    print(f"Memory retrieved: {memory} in {end_time - start_time:.4f} seconds")

    # 更新记忆
    print("Updating memory...")
    start_time = time.time()
    update_success = await memory_service.update_memory(
        tenant_id=tenant_id,
        project_id=project_id,
        memory_id=memory_id,
        content="更新后的Python编程记忆",
        metadata={"source": "updated_conversation", "importance": "medium"},
        tags=["python", "coding"]
    )
    end_time = time.time()
    print(f"Memory updated: {update_success} in {end_time - start_time:.4f} seconds")

    # 列出记忆
    print("Listing memories...")
    start_time = time.time()
    memories = await memory_service.list_memories(tenant_id, project_id, limit=5)
    end_time = time.time()
    print(f"Memories listed: {memories} in {end_time - start_time:.4f} seconds")

    # 搜索记忆
    print("Searching memory...")
    start_time = time.time()
    search_results = await memory_service.search_memory(
        tenant_id=tenant_id,
        project_id=project_id,
        query_text="Python编程",
        filter_tags=["coding"],
        limit=10
    )
    end_time = time.time()
    print(f"Search results: {search_results} in {end_time - start_time:.4f} seconds")

    # 删除记忆
    print("Deleting memory...")
    start_time = time.time()
    delete_success = await memory_service.delete_memory(tenant_id, project_id, memory_id)
    end_time = time.time()
    print(f"Memory deleted: {delete_success} in {end_time - start_time:.4f} seconds")

    # 性能测试：批量添加记忆
    print("Performance test: Adding multiple memories...")
    num_memories = 100
    start_time = time.time()
    for i in range(num_memories):
        await memory_service.add_memory(
            tenant_id=tenant_id,
            project_id=project_id,
            content=f"批量记忆内容 {i}",
            metadata={"batch": True, "index": i},
            tags=["batch", "test"]
        )
    end_time = time.time()
    print(f"Added {num_memories} memories in {end_time - start_time:.4f} seconds")


if __name__ == "__main__":
    asyncio.run(main())