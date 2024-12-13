import asyncio
import pytest
import pytest_asyncio
from memory_service import InfinityMemoryService
from config import MemoryServiceConfig
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv, find_dotenv

# 加载环境变量
load_dotenv(find_dotenv())

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 模拟对话数据
SIMULATED_CONVERSATIONS = [
    {
        "role": "user",
        "content": "我想学习Python编程，应该从哪里开始？",
        "metadata": {"type": "question", "topic": "python_learning", "difficulty": "beginner"},
        "tags": ["python", "beginner", "learning"]
    },
    {
        "role": "assistant",
        "content": "建议从Python基础语法开始，包括变量、数据类型、控制流程等。推荐使用官方文档和一些在线教程平台。",
        "metadata": {"type": "answer", "topic": "python_learning", "confidence": 0.95},
        "tags": ["python", "beginner", "tutorial"]
    },
    {
        "role": "user",
        "content": "Python中的列表和元组有什么区别？",
        "metadata": {"type": "question", "topic": "python_data_structures", "difficulty": "intermediate"},
        "tags": ["python", "list", "tuple", "data_structure"]
    },
    {
        "role": "assistant",
        "content": "列表是可变的，可以修改、添加和删除元素。元组是不可变的，创建后不能修改。列表用[]表示，元组用()表示。",
        "metadata": {"type": "answer", "topic": "python_data_structures", "confidence": 0.98},
        "tags": ["python", "list", "tuple", "comparison"]
    },
    {
        "role": "user",
        "content": "如何在Python中处理文件操作？",
        "metadata": {"type": "question", "topic": "python_file_io", "difficulty": "intermediate"},
        "tags": ["python", "file", "io"]
    },
    {
        "role": "assistant",
        "content": "Python文件操作主要使用open()函数，支持读取、写入和追加模式。建议使用with语句来自动处理文件关闭。",
        "metadata": {"type": "answer", "topic": "python_file_io", "confidence": 0.92},
        "tags": ["python", "file", "io", "best_practice"]
    }
]


@pytest_asyncio.fixture(scope="function")
async def memory_service():
    """创建内存服务实例的异步fixture"""
    config = MemoryServiceConfig()
    service = InfinityMemoryService(config)
    yield service
    await service.close()


@pytest.fixture(scope="function")
def test_params():
    """测试参数fixture"""
    return {
        "tenant_id": "test_tenant",
        "project_id": "conversation_test"
    }


@pytest.mark.asyncio
async def test_memory_service_setup(memory_service, test_params):
    """测试服务初始化和表创建"""
    tenant_id = test_params["tenant_id"]
    project_id = test_params["project_id"]

    # 验证服务实例
    assert isinstance(memory_service, InfinityMemoryService)

    # 验证数据库连接
    assert memory_service.infinity_obj is not None
    assert memory_service.db is not None

    logger.info("Memory service setup completed successfully")


@pytest.mark.asyncio
async def test_memory_service_operations(memory_service, test_params):
    """测试记忆服务的基本操作"""
    tenant_id = test_params["tenant_id"]
    project_id = test_params["project_id"]

    # 添加对话记忆
    memory_ids = []
    base_time = datetime.now()

    logger.info("Starting to add conversation memories...")
    for i, conv in enumerate(SIMULATED_CONVERSATIONS):
        memory_id = await memory_service.add_memory(
            tenant_id=tenant_id,
            project_id=project_id,
            content=conv["content"],
            metadata={
                **conv["metadata"],
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "role": conv["role"]
            },
            tags=conv["tags"]
        )
        memory_ids.append(memory_id)
        logger.info(f"Added memory {i + 1}/{len(SIMULATED_CONVERSATIONS)}")
        await asyncio.sleep(0.1)  # 短暂延迟确保写入

    assert len(memory_ids) == len(SIMULATED_CONVERSATIONS), "所有记忆都应该成功添加"

    # 测试搜索场景
    search_scenarios = [
        {
            "name": "Python基础学习搜索",
            "query": "Python学习入门",
            "tags": ["beginner"],
            "expected_count": 2
        },
        {
            "name": "数据结构相关搜索",
            "query": "Python列表和元组",
            "tags": ["data_structure"],
            "expected_count": 1
        },
        {
            "name": "文件操作搜索",
            "query": "Python文件操作",
            "tags": ["file"],
            "expected_count": 1
        }
    ]

    logger.info("Starting search scenario tests...")
    for scenario in search_scenarios:
        results = await memory_service.search_memory(
            tenant_id=tenant_id,
            project_id=project_id,
            query_text=scenario["query"],
            filter_tags=scenario["tags"],
            limit=10
        )
        logger.info(f"\nTesting: {scenario['name']}")
        logger.info(f"Found {len(results)} results")

        # 打印搜索结果
        for i, result in enumerate(results, 1):
            logger.info(f"\n--- Result {i} ---")
            logger.info(f"Content: {result['content']}")
            logger.info(f"Tags: {result['tags']}")
            logger.info(f"Score: {result['score']}")

    # 测试按角色筛选
    logger.info("\nTesting role-based filtering...")
    for role in ["user", "assistant"]:
        results = await memory_service.search_memory(
            tenant_id=tenant_id,
            project_id=project_id,
            query_text="Python",
            filter_metadata={"role": role},
            limit=10
        )
        logger.info(f"Found {len(results)} results for role: {role}")
        for result in results:
            logger.info(f"Content: {result['content']}")


@pytest.mark.asyncio
async def test_memory_service_performance(memory_service, test_params):
    """测试服务性能"""
    tenant_id = test_params["tenant_id"]
    project_id = test_params["project_id"]

    # 批量插入测试
    batch_size = 100
    test_data = [
        {
            "content": f"Test content {i}",
            "metadata": {"index": i},
            "tags": ["test", f"tag_{i}"]
        }
        for i in range(batch_size)
    ]

    # 测试批量插入性能
    logger.info(f"Testing batch insert performance with {batch_size} records...")
    start_time = datetime.now()
    memory_ids = await memory_service.batch_add_memories(
        tenant_id=tenant_id,
        project_id=project_id,
        memories=test_data
    )
    insert_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Batch insert time: {insert_time:.2f} seconds")
    assert len(memory_ids) == batch_size

    # 测试搜索性能
    logger.info("Testing search performance...")
    start_time = datetime.now()
    results = await memory_service.search_memory(
        tenant_id=tenant_id,
        project_id=project_id,
        query_text="Test content",
        limit=10
    )
    search_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Search time: {search_time:.2f} seconds")
    assert len(results) > 0

    # 清理测试数据
    logger.info("Cleaning up performance test data...")
    for memory_id in memory_ids:
        await memory_service.delete_memory(tenant_id, project_id, memory_id)


@pytest.mark.asyncio
async def test_memory_cleanup(memory_service, test_params):
    """测试清理操作"""
    tenant_id = test_params["tenant_id"]
    project_id = test_params["project_id"]

    logger.info("Starting cleanup test...")
    # 列出所有记忆
    memories = await memory_service.list_memories(tenant_id, project_id)

    # 删除所有记忆
    for memory in memories:
        success = await memory_service.delete_memory(
            tenant_id=tenant_id,
            project_id=project_id,
            memory_id=memory['memory_id']
        )
        assert success, f"删除记忆 {memory['memory_id']} 应该成功"

    logger.info("Cleanup test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])