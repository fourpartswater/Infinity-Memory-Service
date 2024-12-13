import asyncio
import time
from memory_service import InfinityMemoryService
from config import MemoryServiceConfig
from dotenv import load_dotenv, find_dotenv
import polars as pl

load_dotenv(find_dotenv())

async def print_table_info(db, table_name):
    """打印表的详细信息"""
    table = db.get_table(table_name)
    try:
        result = table.output(["*"]).to_pl()
        row_count = len(result)
        print(f"Row Count: {row_count}")

        if row_count > 0:
            print("\nSample Data (up to 5 rows):")
            # 只显示前5行数据
            sample_data = result[:5] if row_count > 5 else result
            print(sample_data)
    except Exception as e:
        print(f"Error accessing table  {e}")

async def print_database_info(memory_service):
    """打印数据库信息"""
    print("\n=== Database Information ===")
    databases = memory_service.infinity_obj.list_databases()
    print(f"Available Databases: {databases.db_names}")

    for db_name in databases.db_names:
        print(f"\n=== Database: {db_name} ===")
        db = memory_service.infinity_obj.get_database(db_name)
        tables = db.list_tables()
        print(f"Available Tables: {tables.table_names}")

        for table_name in tables.table_names:
            print(f"\n=== Table: {table_name} ===")
            await print_table_info(db, table_name)

async def run_memory_tests(memory_service):
    """运行记忆服务测试"""
    tenant_id = "tenant_001"
    project_id = "project_001"

    print("\n=== Memory Service Tests ===")

    # 添加记忆
    print("\nAdding memory...")
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
    print("\nRetrieving memory...")
    start_time = time.time()
    memory = await memory_service.get_memory(tenant_id, project_id, memory_id)
    end_time = time.time()
    print(f"Memory retrieved: {memory} in {end_time - start_time:.4f} seconds")

    # 更新记忆
    print("\nUpdating memory...")
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
    print("\nListing memories...")
    start_time = time.time()
    memories = await memory_service.list_memories(tenant_id, project_id, limit=5)
    end_time = time.time()
    print(f"Memories listed: {memories} in {end_time - start_time:.4f} seconds")

    # 搜索记忆
    print("\nSearching memory...")
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
    print("\nDeleting memory...")
    start_time = time.time()
    delete_success = await memory_service.delete_memory(tenant_id, project_id, memory_id)
    end_time = time.time()
    print(f"Memory deleted: {delete_success} in {end_time - start_time:.4f} seconds")

    return memory_service, tenant_id, project_id

async def run_batch_test(memory_service, tenant_id, project_id):
    """运行批量添加测试"""
    print("\nPerformance test: Adding multiple memories...")
    num_memories = 10
    memories_to_add = [
        {
            "content": f"批量记忆内容 {i}",
            "metadata": {"batch": True, "index": i},
            "tags": ["batch", "test"]
        }
        for i in range(num_memories)
    ]
    start_time = time.time()
    memory_ids = await memory_service.batch_add_memories(tenant_id, project_id, memories_to_add)
    end_time = time.time()
    print(f"Added {len(memory_ids)} memories in {end_time - start_time:.4f} seconds")

async def main():
    try:
        # 从环境变量或配置文件加载配置
        config = MemoryServiceConfig()

        # 使用上下文管理器初始化记忆服务
        async with InfinityMemoryService(config) as memory_service:
            # 打印数据库信息
            await print_database_info(memory_service)

            # 运行记忆服务测试
            memory_service, tenant_id, project_id = await run_memory_tests(memory_service)

            # 运行批量添加测试
            await run_batch_test(memory_service, tenant_id, project_id)

            # 再次打印数据库信息以查看变化
            print("\n=== Final Database State ===")
            await print_database_info(memory_service)

    except Exception as e:
        print(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())