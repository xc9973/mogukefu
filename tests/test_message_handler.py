"""MessageHandler 属性测试

Feature: telegram-intent-bot
Property 1: 消息过滤规则
Property 10: 开关控制行为
Validates: Requirements 1.3, 1.4, 8.3, 8.4, 8.5
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml
from hypothesis import given, settings, strategies as st

from src.config import ConfigStore, KeywordConfig
from src.intent_classifier import IntentClassifier
from src.keyword_matcher import KeywordMatcher
from src.llm_client import ClassifyResult
from src.message_handler import MessageHandler, HandleResult
from src.reply_manager import ReplyManager


# ============================================================================
# 测试数据生成策略
# ============================================================================

# 生成短消息（长度 < 2）
short_message = st.text(max_size=1)

# 生成命令消息（以 / 开头）
command_message = st.text(min_size=1, max_size=50).map(lambda x: "/" + x)

# 生成有效消息（长度 >= 2，不以 / 开头）
valid_message = st.text(min_size=2, max_size=100).filter(
    lambda x: not x.startswith("/")
)

# 生成非空字符串
non_empty_string = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())


def make_valid_config(
    keyword_reply_enabled: bool = True,
    ai_reply_enabled: bool = True,
    keywords: list | None = None,
) -> dict:
    """创建有效的配置字典"""
    return {
        "bot": {
            "token": "test_token",
            "keyword_reply_enabled": keyword_reply_enabled,
            "ai_reply_enabled": ai_reply_enabled,
        },
        "llm": {
            "base_url": "https://api.example.com/v1",
            "api_key": "test_key",
            "model": "gpt-3.5-turbo",
        },
        "intents": [
            {"tag": "TUTORIAL", "description": "教程", "reply": "教程回复"},
            {"tag": "ISSUE", "description": "问题", "reply": "问题回复"},
            {"tag": "SERVICE", "description": "客服", "reply": "客服回复"},
            {"tag": "IGNORE", "description": "忽略", "reply": ""},
        ],
        "keywords": keywords or [
            {"keyword": "教程", "reply": "关键词教程回复"},
            {"keyword": "客服", "reply": "关键词客服回复"},
        ],
    }


def create_config_store(config: dict) -> ConfigStore:
    """创建并加载 ConfigStore"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(config, f, allow_unicode=True)
        config_path = Path(f.name)

    try:
        store = ConfigStore()
        store.load(config_path)
        return store
    finally:
        config_path.unlink()


def create_message_handler(
    config: dict,
    classifier_result: ClassifyResult | None = None,
) -> MessageHandler:
    """创建 MessageHandler 实例"""
    store = create_config_store(config)
    keywords = store.get_keywords()
    keyword_matcher = KeywordMatcher(keywords)
    reply_manager = ReplyManager(store)
    
    # 创建 mock 的 IntentClassifier
    mock_classifier = AsyncMock(spec=IntentClassifier)
    if classifier_result:
        mock_classifier.classify.return_value = classifier_result
    else:
        mock_classifier.classify.return_value = ClassifyResult(intent="IGNORE")
    
    return MessageHandler(
        config=store,
        keyword_matcher=keyword_matcher,
        classifier=mock_classifier,
        reply_manager=reply_manager,
    )


# ============================================================================
# Property 1: 消息过滤规则
# Feature: telegram-intent-bot, Property 1: 消息过滤规则
# Validates: Requirements 1.3, 1.4
# ============================================================================

class TestProperty1MessageFilterRules:
    """Property 1: 消息过滤规则

    *For any* 消息文本，如果长度小于 2 或以 "/" 开头，则该消息应被忽略，
    不触发任何回复逻辑。
    """

    @given(text=short_message)
    @settings(max_examples=100)
    def test_short_messages_are_ignored(self, text: str):
        """长度小于 2 的消息应被忽略"""
        config = make_valid_config()
        handler = create_message_handler(config)
        
        result = handler.should_ignore_message(text)
        
        assert result is True

    @given(text=command_message)
    @settings(max_examples=100)
    def test_command_messages_are_ignored(self, text: str):
        """以 / 开头的命令消息应被忽略"""
        config = make_valid_config()
        handler = create_message_handler(config)
        
        result = handler.should_ignore_message(text)
        
        assert result is True

    @given(text=valid_message)
    @settings(max_examples=100)
    def test_valid_messages_are_not_ignored(self, text: str):
        """有效消息（长度 >= 2 且不以 / 开头）不应被忽略"""
        config = make_valid_config()
        handler = create_message_handler(config)
        
        result = handler.should_ignore_message(text)
        
        assert result is False

    @pytest.mark.asyncio
    @given(text=short_message)
    @settings(max_examples=100)
    async def test_short_messages_return_no_reply(self, text: str):
        """短消息处理后应返回不回复"""
        config = make_valid_config()
        handler = create_message_handler(config)
        
        result = await handler.handle(text)
        
        assert result.should_reply is False
        assert result.reply_text is None

    @pytest.mark.asyncio
    @given(text=command_message)
    @settings(max_examples=100)
    async def test_command_messages_return_no_reply(self, text: str):
        """命令消息处理后应返回不回复"""
        config = make_valid_config()
        handler = create_message_handler(config)
        
        result = await handler.handle(text)
        
        assert result.should_reply is False
        assert result.reply_text is None

    def test_empty_message_is_ignored(self):
        """空消息应被忽略"""
        config = make_valid_config()
        handler = create_message_handler(config)
        
        result = handler.should_ignore_message("")
        
        assert result is True

    def test_single_char_message_is_ignored(self):
        """单字符消息应被忽略"""
        config = make_valid_config()
        handler = create_message_handler(config)
        
        result = handler.should_ignore_message("a")
        
        assert result is True

    def test_two_char_message_is_not_ignored(self):
        """两字符消息不应被忽略"""
        config = make_valid_config()
        handler = create_message_handler(config)
        
        result = handler.should_ignore_message("ab")
        
        assert result is False


# ============================================================================
# Property 10: 开关控制行为
# Feature: telegram-intent-bot, Property 10: 开关控制行为
# Validates: Requirements 8.3, 8.4, 8.5
# ============================================================================

class TestProperty10SwitchControlBehavior:
    """Property 10: 开关控制行为

    *For any* 消息处理流程：
    - 当 AI 开关关闭时，不应调用 LLM
    - 当关键词开关关闭时，不应进行关键词匹配
    - 当两个开关都关闭时，不应产生任何回复
    """

    @pytest.mark.asyncio
    async def test_both_switches_off_no_reply(self):
        """两个开关都关闭时不应产生任何回复"""
        config = make_valid_config(
            keyword_reply_enabled=False,
            ai_reply_enabled=False,
        )
        handler = create_message_handler(config)
        
        # 使用包含关键词的有效消息
        result = await handler.handle("请问教程在哪里")
        
        assert result.should_reply is False
        assert result.reply_text is None

    @pytest.mark.asyncio
    async def test_ai_switch_off_no_llm_call(self):
        """AI 开关关闭时不应调用 LLM"""
        config = make_valid_config(
            keyword_reply_enabled=True,
            ai_reply_enabled=False,
            keywords=[],  # 无关键词配置
        )
        store = create_config_store(config)
        keywords = store.get_keywords()
        keyword_matcher = KeywordMatcher(keywords)
        reply_manager = ReplyManager(store)
        
        # 创建 mock classifier
        mock_classifier = AsyncMock(spec=IntentClassifier)
        mock_classifier.classify.return_value = ClassifyResult(intent="TUTORIAL")
        
        handler = MessageHandler(
            config=store,
            keyword_matcher=keyword_matcher,
            classifier=mock_classifier,
            reply_manager=reply_manager,
        )
        
        # 使用不包含关键词的有效消息
        result = await handler.handle("这是一条测试消息")
        
        # AI 开关关闭，不应调用 LLM
        mock_classifier.classify.assert_not_called()
        assert result.should_reply is False

    @pytest.mark.asyncio
    async def test_keyword_switch_off_no_keyword_match(self):
        """关键词开关关闭时不应进行关键词匹配"""
        config = make_valid_config(
            keyword_reply_enabled=False,
            ai_reply_enabled=True,
            keywords=[{"keyword": "教程", "reply": "关键词回复"}],
        )
        # 设置 AI 返回 IGNORE
        handler = create_message_handler(
            config,
            classifier_result=ClassifyResult(intent="IGNORE"),
        )
        
        # 使用包含关键词的消息
        result = await handler.handle("请问教程在哪里")
        
        # 关键词开关关闭，不应匹配关键词，应走 AI 流程
        # AI 返回 IGNORE，所以不回复
        assert result.should_reply is False
        assert result.matched_keyword is None

    @pytest.mark.asyncio
    async def test_keyword_switch_on_matches_keyword(self):
        """关键词开关开启时应进行关键词匹配"""
        config = make_valid_config(
            keyword_reply_enabled=True,
            ai_reply_enabled=True,
            keywords=[{"keyword": "教程", "reply": "关键词教程回复"}],
        )
        handler = create_message_handler(config)
        
        # 使用包含关键词的消息
        result = await handler.handle("请问教程在哪里")
        
        assert result.should_reply is True
        assert result.reply_text == "关键词教程回复"
        assert result.matched_keyword == "教程"

    @pytest.mark.asyncio
    async def test_ai_switch_on_calls_llm_when_no_keyword_match(self):
        """AI 开关开启且关键词未匹配时应调用 LLM"""
        config = make_valid_config(
            keyword_reply_enabled=True,
            ai_reply_enabled=True,
            keywords=[{"keyword": "特定关键词", "reply": "关键词回复"}],
        )
        store = create_config_store(config)
        keywords = store.get_keywords()
        keyword_matcher = KeywordMatcher(keywords)
        reply_manager = ReplyManager(store)
        
        # 创建 mock classifier
        mock_classifier = AsyncMock(spec=IntentClassifier)
        mock_classifier.classify.return_value = ClassifyResult(intent="TUTORIAL")
        
        handler = MessageHandler(
            config=store,
            keyword_matcher=keyword_matcher,
            classifier=mock_classifier,
            reply_manager=reply_manager,
        )
        
        # 使用不包含关键词的有效消息
        result = await handler.handle("这是一条测试消息")
        
        # 应调用 LLM
        mock_classifier.classify.assert_called_once_with("这是一条测试消息")
        assert result.should_reply is True
        assert result.intent == "TUTORIAL"

    @pytest.mark.asyncio
    @given(
        keyword_enabled=st.booleans(),
        ai_enabled=st.booleans(),
    )
    @settings(max_examples=100)
    async def test_switch_combinations(self, keyword_enabled: bool, ai_enabled: bool):
        """测试开关组合的行为"""
        config = make_valid_config(
            keyword_reply_enabled=keyword_enabled,
            ai_reply_enabled=ai_enabled,
            keywords=[],  # 无关键词，确保不会匹配
        )
        store = create_config_store(config)
        keywords = store.get_keywords()
        keyword_matcher = KeywordMatcher(keywords)
        reply_manager = ReplyManager(store)
        
        mock_classifier = AsyncMock(spec=IntentClassifier)
        mock_classifier.classify.return_value = ClassifyResult(intent="TUTORIAL")
        
        handler = MessageHandler(
            config=store,
            keyword_matcher=keyword_matcher,
            classifier=mock_classifier,
            reply_manager=reply_manager,
        )
        
        result = await handler.handle("这是测试消息")
        
        if not keyword_enabled and not ai_enabled:
            # 两个开关都关闭，不应回复
            assert result.should_reply is False
            mock_classifier.classify.assert_not_called()
        elif ai_enabled:
            # AI 开关开启，应调用 LLM（因为无关键词匹配）
            mock_classifier.classify.assert_called_once()
        else:
            # 只有关键词开关开启但无匹配，不应回复
            assert result.should_reply is False
            mock_classifier.classify.assert_not_called()

    @pytest.mark.asyncio
    async def test_keyword_priority_over_ai(self):
        """关键词匹配优先于 AI 分类"""
        config = make_valid_config(
            keyword_reply_enabled=True,
            ai_reply_enabled=True,
            keywords=[{"keyword": "教程", "reply": "关键词教程回复"}],
        )
        store = create_config_store(config)
        keywords = store.get_keywords()
        keyword_matcher = KeywordMatcher(keywords)
        reply_manager = ReplyManager(store)
        
        mock_classifier = AsyncMock(spec=IntentClassifier)
        mock_classifier.classify.return_value = ClassifyResult(intent="ISSUE")
        
        handler = MessageHandler(
            config=store,
            keyword_matcher=keyword_matcher,
            classifier=mock_classifier,
            reply_manager=reply_manager,
        )
        
        # 使用包含关键词的消息
        result = await handler.handle("请问教程在哪里")
        
        # 关键词匹配成功，不应调用 LLM
        mock_classifier.classify.assert_not_called()
        assert result.should_reply is True
        assert result.reply_text == "关键词教程回复"
        assert result.matched_keyword == "教程"
