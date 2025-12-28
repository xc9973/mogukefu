"""IntentClassifier 单元测试

测试意图分类器的正常分类流程和异常处理。
Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.config import ConfigStore, IntentConfig, KeywordConfig, LLMConfig
from src.intent_classifier import IntentClassifier
from src.llm_client import ClassifyResult, LLMClient


# ============================================================================
# 测试辅助函数
# ============================================================================

def create_mock_config() -> MagicMock:
    """创建模拟的 ConfigStore"""
    config = MagicMock(spec=ConfigStore)
    config.get_intents.return_value = [
        IntentConfig(tag="TUTORIAL", description="教程相关", reply="教程回复"),
        IntentConfig(tag="ISSUE", description="问题反馈", reply="问题回复"),
        IntentConfig(tag="SERVICE", description="客服相关", reply="客服回复"),
        IntentConfig(tag="IGNORE", description="忽略内容", reply=""),
    ]
    config.get_keywords.return_value = [
        KeywordConfig(keyword="教程", reply="教程关键词回复"),
        KeywordConfig(keyword="客服", reply="客服关键词回复"),
    ]
    return config


def create_mock_llm_client() -> MagicMock:
    """创建模拟的 LLMClient"""
    return MagicMock(spec=LLMClient)


# ============================================================================
# 正常分类流程测试
# Validates: Requirements 2.1, 2.2, 2.3, 2.6
# ============================================================================

class TestNormalClassificationFlow:
    """测试正常分类流程"""

    @pytest.mark.asyncio
    async def test_classify_returns_intent_from_llm(self):
        """分类应返回 LLM 的意图结果"""
        config = create_mock_config()
        llm = create_mock_llm_client()
        llm.classify = AsyncMock(return_value=ClassifyResult(intent="TUTORIAL", keyword=None))
        
        classifier = IntentClassifier(llm=llm, config=config)
        result = await classifier.classify("如何使用这个功能？")
        
        assert result.intent == "TUTORIAL"
        assert result.keyword is None

    @pytest.mark.asyncio
    async def test_classify_returns_keyword_from_llm(self):
        """分类应返回 LLM 识别的关键词"""
        config = create_mock_config()
        llm = create_mock_llm_client()
        llm.classify = AsyncMock(return_value=ClassifyResult(intent="TUTORIAL", keyword="教程"))
        
        classifier = IntentClassifier(llm=llm, config=config)
        result = await classifier.classify("我想看教程")
        
        assert result.intent == "TUTORIAL"
        assert result.keyword == "教程"

    @pytest.mark.asyncio
    async def test_classify_passes_intents_to_llm(self):
        """分类应将意图配置传递给 LLM"""
        config = create_mock_config()
        llm = create_mock_llm_client()
        llm.classify = AsyncMock(return_value=ClassifyResult(intent="IGNORE", keyword=None))
        
        classifier = IntentClassifier(llm=llm, config=config)
        await classifier.classify("测试消息")
        
        # 验证 LLM 被调用时传入了正确的意图配置
        llm.classify.assert_called_once()
        call_args = llm.classify.call_args
        assert call_args.kwargs["message"] == "测试消息"
        assert len(call_args.kwargs["intents"]) == 4

    @pytest.mark.asyncio
    async def test_classify_passes_keywords_to_llm(self):
        """分类应将关键词列表传递给 LLM"""
        config = create_mock_config()
        llm = create_mock_llm_client()
        llm.classify = AsyncMock(return_value=ClassifyResult(intent="IGNORE", keyword=None))
        
        classifier = IntentClassifier(llm=llm, config=config)
        await classifier.classify("测试消息")
        
        # 验证 LLM 被调用时传入了正确的关键词列表
        call_args = llm.classify.call_args
        assert call_args.kwargs["keywords"] == ["教程", "客服"]

    @pytest.mark.asyncio
    async def test_classify_all_valid_intents(self):
        """分类应能返回所有有效的意图标签"""
        config = create_mock_config()
        llm = create_mock_llm_client()
        
        classifier = IntentClassifier(llm=llm, config=config)
        
        for intent_tag in ["TUTORIAL", "ISSUE", "SERVICE", "IGNORE"]:
            llm.classify = AsyncMock(return_value=ClassifyResult(intent=intent_tag, keyword=None))
            result = await classifier.classify("测试消息")
            assert result.intent == intent_tag


# ============================================================================
# 异常处理测试
# Validates: Requirements 2.4, 2.5
# ============================================================================

class TestExceptionHandling:
    """测试异常处理"""

    @pytest.mark.asyncio
    async def test_llm_exception_returns_ignore(self):
        """LLM 调用异常应返回 IGNORE"""
        config = create_mock_config()
        llm = create_mock_llm_client()
        llm.classify = AsyncMock(side_effect=Exception("API 调用失败"))
        
        classifier = IntentClassifier(llm=llm, config=config)
        result = await classifier.classify("测试消息")
        
        assert result.intent == "IGNORE"
        assert result.keyword is None

    @pytest.mark.asyncio
    async def test_config_exception_returns_ignore(self):
        """配置获取异常应返回 IGNORE"""
        config = create_mock_config()
        config.get_intents.side_effect = Exception("配置错误")
        llm = create_mock_llm_client()
        
        classifier = IntentClassifier(llm=llm, config=config)
        result = await classifier.classify("测试消息")
        
        assert result.intent == "IGNORE"
        assert result.keyword is None

    @pytest.mark.asyncio
    async def test_timeout_exception_returns_ignore(self):
        """超时异常应返回 IGNORE"""
        config = create_mock_config()
        llm = create_mock_llm_client()
        llm.classify = AsyncMock(side_effect=TimeoutError("请求超时"))
        
        classifier = IntentClassifier(llm=llm, config=config)
        result = await classifier.classify("测试消息")
        
        assert result.intent == "IGNORE"
        assert result.keyword is None

    @pytest.mark.asyncio
    async def test_connection_error_returns_ignore(self):
        """连接错误应返回 IGNORE"""
        config = create_mock_config()
        llm = create_mock_llm_client()
        llm.classify = AsyncMock(side_effect=ConnectionError("网络连接失败"))
        
        classifier = IntentClassifier(llm=llm, config=config)
        result = await classifier.classify("测试消息")
        
        assert result.intent == "IGNORE"
        assert result.keyword is None

    @pytest.mark.asyncio
    async def test_result_is_always_classify_result(self):
        """返回结果始终是 ClassifyResult 类型"""
        config = create_mock_config()
        llm = create_mock_llm_client()
        
        classifier = IntentClassifier(llm=llm, config=config)
        
        # 正常情况
        llm.classify = AsyncMock(return_value=ClassifyResult(intent="TUTORIAL", keyword=None))
        result = await classifier.classify("测试消息")
        assert isinstance(result, ClassifyResult)
        
        # 异常情况
        llm.classify = AsyncMock(side_effect=Exception("错误"))
        result = await classifier.classify("测试消息")
        assert isinstance(result, ClassifyResult)

    @pytest.mark.asyncio
    async def test_empty_intents_still_works(self):
        """空意图配置应正常工作"""
        config = create_mock_config()
        config.get_intents.return_value = []
        llm = create_mock_llm_client()
        llm.classify = AsyncMock(return_value=ClassifyResult(intent="IGNORE", keyword=None))
        
        classifier = IntentClassifier(llm=llm, config=config)
        result = await classifier.classify("测试消息")
        
        assert result.intent == "IGNORE"

    @pytest.mark.asyncio
    async def test_empty_keywords_still_works(self):
        """空关键词配置应正常工作"""
        config = create_mock_config()
        config.get_keywords.return_value = []
        llm = create_mock_llm_client()
        llm.classify = AsyncMock(return_value=ClassifyResult(intent="TUTORIAL", keyword=None))
        
        classifier = IntentClassifier(llm=llm, config=config)
        result = await classifier.classify("测试消息")
        
        assert result.intent == "TUTORIAL"
