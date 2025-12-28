"""ReplyManager 属性测试

Feature: telegram-intent-bot
Property 4: IGNORE 静默规则
Property 9: 关键词优先于 AI 回复
Validates: Requirements 3.4, 2.7
"""

import tempfile
from pathlib import Path

import yaml
from hypothesis import given, settings, strategies as st

from src.config import ConfigStore, VALID_INTENT_TAGS
from src.llm_client import ClassifyResult
from src.reply_manager import ReplyManager


# ============================================================================
# 测试数据生成策略
# ============================================================================

# 生成非空字符串 - 限制为 ASCII 可打印字符避免 YAML 序列化问题
non_empty_string = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S'),
                           whitelist_characters=' ',
                           blacklist_characters='\x00\x85\u2028\u2029'),
    min_size=1, 
    max_size=50
).filter(lambda x: x.strip())

# 生成非 IGNORE 的意图标签
non_ignore_intent_tags = st.sampled_from(["TUTORIAL", "ISSUE", "SERVICE"])


def make_valid_config(
    intents: list | None = None,
    keywords: list | None = None,
) -> dict:
    """创建有效的配置字典"""
    if intents is None:
        intents = [
            {"tag": "TUTORIAL", "description": "教程", "reply": "教程回复"},
            {"tag": "ISSUE", "description": "问题", "reply": "问题回复"},
            {"tag": "SERVICE", "description": "客服", "reply": "客服回复"},
            {"tag": "IGNORE", "description": "忽略", "reply": ""},
        ]
    return {
        "bot": {
            "token": "test_token",
            "keyword_reply_enabled": True,
            "ai_reply_enabled": True,
        },
        "llm": {
            "base_url": "https://api.example.com/v1",
            "api_key": "test_key",
            "model": "gpt-3.5-turbo",
        },
        "intents": intents,
        "keywords": keywords or [],
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


# ============================================================================
# Property 4: IGNORE 静默规则
# Feature: telegram-intent-bot, Property 4: IGNORE 静默规则
# Validates: Requirements 3.4
# ============================================================================

class TestProperty4IgnoreSilentRule:
    """Property 4: IGNORE 静默规则

    *For any* 分类结果为 IGNORE 的情况，Reply_Manager 应返回 None，不产生任何回复。
    """

    @given(keyword=st.one_of(st.none(), non_empty_string))
    @settings(max_examples=100)
    def test_ignore_intent_returns_none(self, keyword: str | None):
        """IGNORE 意图应返回 None，无论是否有关键词"""
        config = make_valid_config(
            keywords=[{"keyword": "测试关键词", "reply": "关键词回复"}]
        )
        store = create_config_store(config)
        manager = ReplyManager(store)

        # 创建 IGNORE 意图的分类结果
        result = ClassifyResult(intent="IGNORE", keyword=keyword)

        # 验证返回 None
        reply = manager.get_reply(result)
        assert reply is None

    def test_ignore_intent_with_valid_keyword_still_returns_none(self):
        """即使 IGNORE 结果包含有效关键词，也应返回 None"""
        config = make_valid_config(
            keywords=[{"keyword": "教程", "reply": "关键词教程回复"}]
        )
        store = create_config_store(config)
        manager = ReplyManager(store)

        # IGNORE 意图但包含有效关键词
        result = ClassifyResult(intent="IGNORE", keyword="教程")

        # 验证仍然返回 None（IGNORE 优先）
        reply = manager.get_reply(result)
        assert reply is None


# ============================================================================
# Property 9: 关键词优先于 AI 回复
# Feature: telegram-intent-bot, Property 9: 关键词优先于 AI 回复
# Validates: Requirements 2.7
# ============================================================================

class TestProperty9KeywordPriorityOverAI:
    """Property 9: 关键词优先于 AI 回复

    *For any* 同时匹配关键词和 AI 分类结果的情况，如果 AI 返回了关键词，
    应优先使用关键词字典的回复。
    """

    @given(
        intent=non_ignore_intent_tags,
        keyword=non_empty_string,
        keyword_reply=non_empty_string,
    )
    @settings(max_examples=100)
    def test_keyword_reply_takes_priority(
        self, intent: str, keyword: str, keyword_reply: str
    ):
        """当有关键词时，应优先使用关键词回复"""
        config = make_valid_config(
            keywords=[{"keyword": keyword, "reply": keyword_reply}]
        )
        store = create_config_store(config)
        manager = ReplyManager(store)

        # 创建包含关键词的分类结果
        result = ClassifyResult(intent=intent, keyword=keyword)

        # 验证使用关键词回复
        reply = manager.get_reply(result)
        assert reply == keyword_reply

    @given(intent=non_ignore_intent_tags)
    @settings(max_examples=100)
    def test_intent_reply_used_when_no_keyword(self, intent: str):
        """当没有关键词时，应使用意图回复"""
        config = make_valid_config()
        store = create_config_store(config)
        manager = ReplyManager(store)

        # 创建不包含关键词的分类结果
        result = ClassifyResult(intent=intent, keyword=None)

        # 验证使用意图回复
        reply = manager.get_reply(result)
        expected_reply = store.get_reply_by_intent(intent)
        assert reply == expected_reply
        assert reply is not None

    @given(intent=non_ignore_intent_tags)
    @settings(max_examples=100)
    def test_intent_reply_used_when_keyword_not_in_config(self, intent: str):
        """当关键词不在配置中时，应使用意图回复"""
        config = make_valid_config(
            keywords=[{"keyword": "已配置关键词", "reply": "关键词回复"}]
        )
        store = create_config_store(config)
        manager = ReplyManager(store)

        # 创建包含未配置关键词的分类结果
        result = ClassifyResult(intent=intent, keyword="未配置的关键词")

        # 验证使用意图回复（因为关键词不在配置中）
        reply = manager.get_reply(result)
        expected_reply = store.get_reply_by_intent(intent)
        assert reply == expected_reply

    def test_keyword_reply_priority_example(self):
        """具体示例：关键词回复优先于意图回复"""
        config = make_valid_config(
            intents=[
                {"tag": "TUTORIAL", "description": "教程", "reply": "意图教程回复"},
                {"tag": "ISSUE", "description": "问题", "reply": "意图问题回复"},
                {"tag": "SERVICE", "description": "客服", "reply": "意图客服回复"},
                {"tag": "IGNORE", "description": "忽略", "reply": ""},
            ],
            keywords=[
                {"keyword": "教程", "reply": "关键词教程回复"},
            ]
        )
        store = create_config_store(config)
        manager = ReplyManager(store)

        # AI 返回 TUTORIAL 意图和 "教程" 关键词
        result = ClassifyResult(intent="TUTORIAL", keyword="教程")

        # 应使用关键词回复，而非意图回复
        reply = manager.get_reply(result)
        assert reply == "关键词教程回复"
        assert reply != "意图教程回复"


# ============================================================================
# Property 11: FAQ 匹配与回复
# Feature: telegram-intent-bot, Property 11: FAQ 匹配与回复
# Validates: Requirements 10.3, 10.4
# ============================================================================

class TestProperty11FAQMatchAndReply:
    """Property 11: FAQ 匹配与回复

    *For any* 分类结果为 FAQ 且 faq_id 有效的情况，Reply_Manager 应返回该 FAQ 的预设答案；
    如果 faq_id 无效，应回退到 IGNORE 处理。
    """

    @given(
        faq_id=non_empty_string,
        faq_answer=non_empty_string,
    )
    @settings(max_examples=100)
    def test_valid_faq_id_returns_faq_answer(self, faq_id: str, faq_answer: str):
        """有效的 FAQ ID 应返回对应的预设答案"""
        config = make_valid_config()
        config["faq"] = [
            {"faq_id": faq_id, "question": "测试问题", "answer": faq_answer}
        ]
        store = create_config_store(config)
        manager = ReplyManager(store)

        # 创建 FAQ 意图的分类结果
        result = ClassifyResult(intent="FAQ", faq_id=faq_id)

        # 验证返回 FAQ 答案
        reply = manager.get_reply(result)
        assert reply == faq_answer

    @given(invalid_faq_id=non_empty_string)
    @settings(max_examples=100)
    def test_invalid_faq_id_returns_none(self, invalid_faq_id: str):
        """无效的 FAQ ID 应回退到静默（返回 None）"""
        config = make_valid_config()
        config["faq"] = [
            {"faq_id": "valid_faq", "question": "有效问题", "answer": "有效答案"}
        ]
        store = create_config_store(config)
        manager = ReplyManager(store)

        # 确保使用的是无效的 FAQ ID
        if invalid_faq_id == "valid_faq":
            invalid_faq_id = "definitely_invalid_faq"

        # 创建 FAQ 意图但使用无效 faq_id
        result = ClassifyResult(intent="FAQ", faq_id=invalid_faq_id)

        # 验证返回 None（回退到静默）
        reply = manager.get_reply(result)
        assert reply is None

    def test_faq_intent_without_faq_id_returns_none(self):
        """FAQ 意图但没有 faq_id 应返回 None"""
        config = make_valid_config()
        config["faq"] = [
            {"faq_id": "test_faq", "question": "测试问题", "answer": "测试答案"}
        ]
        store = create_config_store(config)
        manager = ReplyManager(store)

        # FAQ 意图但 faq_id 为 None
        result = ClassifyResult(intent="FAQ", faq_id=None)

        # 验证返回 None
        reply = manager.get_reply(result)
        assert reply is None

    def test_faq_reply_example(self):
        """具体示例：FAQ 回复正常工作"""
        config = make_valid_config()
        config["faq"] = [
            {"faq_id": "register", "question": "如何注册", "answer": "📝 注册步骤：1. 访问官网..."},
            {"faq_id": "pricing", "question": "价格多少", "answer": "💰 基础版免费..."},
        ]
        store = create_config_store(config)
        manager = ReplyManager(store)

        # 测试 register FAQ
        result1 = ClassifyResult(intent="FAQ", faq_id="register")
        reply1 = manager.get_reply(result1)
        assert reply1 == "📝 注册步骤：1. 访问官网..."

        # 测试 pricing FAQ
        result2 = ClassifyResult(intent="FAQ", faq_id="pricing")
        reply2 = manager.get_reply(result2)
        assert reply2 == "💰 基础版免费..."

        # 测试无效 FAQ ID
        result3 = ClassifyResult(intent="FAQ", faq_id="nonexistent")
        reply3 = manager.get_reply(result3)
        assert reply3 is None
