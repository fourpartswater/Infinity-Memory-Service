import asyncio
import time
from memory_service import InfinityMemoryService
from config import MemoryServiceConfig
from dotenv import load_dotenv, find_dotenv
import polars as pl

load_dotenv(find_dotenv())

async def main():
    # 从环境变量或配置文件加载配置
    config = MemoryServiceConfig()

    # 初始化记忆服务
    memory_service = InfinityMemoryService(config)

    # 打印数据库信息
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
            table = db.get_table(table_name)
            try:
                # 使用 select 查询获取数据
                result = table.output(["*"]).to_pl()
                row_count = len(result) if isinstance(result, pl.DataFrame) else 0
                print(f"Row Count: {row_count}")

                if row_count > 0:
                    print("\nSample Data (up to 5 rows):")
                    if isinstance(result, pl.DataFrame):
                        sample = result.slice(0, 5)
                        print(sample)
                    else:
                        print("Data format not supported for display")
            except Exception as e:
                print(f"Error accessing table data: {e}")

    # 示例租户和项目
    tenant_id = "tenant_001"
    project_id = "project_001"

    print("\n=== Dropped Existing Table ===")
    # 删除已存在的表
    table_name = memory_service._get_table_name(tenant_id, project_id)
    try:
        memory_service.db.drop_table(table_name)
        print(f"Dropped existing table: {table_name}")
    except Exception as e:
        print(f"Table {table_name} does not exist or could not be dropped: {e}")

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
    await asyncio.sleep(1)  # 等待数据写入

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
    await asyncio.sleep(1)  # 等待数据更新

    # 列出记忆
    print("\nListing memories...")
    start_time = time.time()
    memories = await memory_service.list_memories(tenant_id, project_id, limit=5)
    end_time = time.time()
    print(f"Memories listed: {memories} in {end_time - start_time:.4f} seconds")

    await asyncio.sleep(1)  # 等待索引更新
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

    # 性能测试：批量添加记忆
    print("\nPerformance test: Adding multiple memories...")
    num_memories = 1
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

if __name__ == "__main__":
    asyncio.run(main())