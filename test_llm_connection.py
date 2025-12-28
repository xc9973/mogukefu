#!/usr/bin/env python3
"""LLM 连接测试脚本"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import ConfigStore
from src.llm_client import LLMClient


async def test_llm():
    """测试 LLM 连接"""
    print("=" * 50)
    print("LLM 连接测试")
    print("=" * 50)
    
    # 加载配置
    config = ConfigStore()
    try:
        config.load("config.yaml")
        print("✅ 配置加载成功")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return
    
    llm_config = config.get_llm_config()
    print(f"   API 地址: {llm_config.base_url}")
    print(f"   模型: {llm_config.model}")
    print()
    
    # 创建 LLM 客户端
    client = LLMClient(
        config=llm_config,
        timeout=llm_config.timeout,
        max_retries=1,
    )
    
    # 测试简单请求
    print("测试 1: 简单对话")
    print("-" * 30)
    try:
        result = await client.classify(
            message="你好",
            intents=config.get_intents(),
            keywords=[],
        )
        print(f"✅ LLM 响应成功")
        print(f"   意图: {result.intent}")
        print(f"   关键词: {result.keyword}")
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
    print()
    
    # 测试意图识别
    print("测试 2: 意图识别 - 教程类问题")
    print("-" * 30)
    try:
        result = await client.classify(
            message="请问怎么使用这个软件",
            intents=config.get_intents(),
            keywords=[],
        )
        print(f"✅ LLM 响应成功")
        print(f"   意图: {result.intent}")
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
    print()
    
    print("测试 3: 意图识别 - 问题反馈")
    print("-" * 30)
    try:
        result = await client.classify(
            message="程序报错了，打不开",
            intents=config.get_intents(),
            keywords=[],
        )
        print(f"✅ LLM 响应成功")
        print(f"   意图: {result.intent}")
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
    print()
    
    print("=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_llm())
