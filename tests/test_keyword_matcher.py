"""KeywordMatcher 属性测试

Feature: telegram-intent-bot
Property 8: 关键词精确匹配
Validates: Requirements 7.2, 7.3
"""

from hypothesis import given, settings, strategies as st

from src.config import KeywordConfig
from src.keyword_matcher import KeywordMatcher


# ============================================================================
# 测试数据生成策略
# ============================================================================

# 生成非空关键词
non_empty_keyword = st.text(min_size=1, max_size=20).filter(lambda x: x.strip())

# 生成关键词配置
keyword_config_strategy = st.builds(
    KeywordConfig,
    keyword=non_empty_keyword,
    reply=st.text(max_size=100),
)

# 生成关键词配置列表（至少1个，最多5个）
keyword_configs_strategy = st.lists(keyword_config_strategy, min_size=1, max_size=5)


# ============================================================================
# Property 8: 关键词精确匹配
# Feature: telegram-intent-bot, Property 8: 关键词精确匹配
# Validates: Requirements 7.2, 7.3
# ============================================================================

class TestProperty8KeywordExactMatch:
    """Property 8: 关键词精确匹配

    *For any* 消息文本和关键词列表，如果消息包含某个关键词，应返回第一个匹配的关键词；
    如果匹配多个，返回配置顺序中的第一个。
    """

    @given(
        keywords=keyword_configs_strategy,
        prefix=st.text(max_size=20),
        suffix=st.text(max_size=20),
    )
    @settings(max_examples=100)
    def test_message_containing_keyword_returns_match(
        self, keywords: list[KeywordConfig], prefix: str, suffix: str
    ):
        """消息包含关键词时应返回该关键词"""
        matcher = KeywordMatcher(keywords)
        
        # 取第一个关键词构造消息
        target_keyword = keywords[0].keyword
        message = f"{prefix}{target_keyword}{suffix}"
        
        result = matcher.match(message)
        
        # 应该匹配到某个关键词
        assert result is not None
        # 匹配到的关键词应该在消息中
        assert result in message

    @given(
        keywords=keyword_configs_strategy,
        message=st.text(max_size=50),
    )
    @settings(max_examples=100)
    def test_message_not_containing_any_keyword_returns_none(
        self, keywords: list[KeywordConfig], message: str
    ):
        """消息不包含任何关键词时应返回 None"""
        # 过滤掉包含任何关键词的消息
        if any(kw.keyword in message for kw in keywords):
            return  # 跳过这个测试用例
        
        matcher = KeywordMatcher(keywords)
        result = matcher.match(message)
        
        assert result is None

    @given(
        first_keyword=non_empty_keyword,
        second_keyword=non_empty_keyword,
        prefix=st.text(max_size=10),
        middle=st.text(max_size=10),
        suffix=st.text(max_size=10),
    )
    @settings(max_examples=100)
    def test_multiple_matches_returns_first_in_config_order(
        self, first_keyword: str, second_keyword: str, prefix: str, middle: str, suffix: str
    ):
        """匹配多个关键词时应返回配置顺序中的第一个"""
        # 确保两个关键词不同且互不包含
        if first_keyword == second_keyword:
            return
        if first_keyword in second_keyword or second_keyword in first_keyword:
            return
        
        keywords = [
            KeywordConfig(keyword=first_keyword, reply="回复1"),
            KeywordConfig(keyword=second_keyword, reply="回复2"),
        ]
        matcher = KeywordMatcher(keywords)
        
        # 构造同时包含两个关键词的消息
        message = f"{prefix}{first_keyword}{middle}{second_keyword}{suffix}"
        
        result = matcher.match(message)
        
        # 应该返回配置顺序中的第一个关键词
        assert result == first_keyword

    def test_empty_keywords_returns_none(self):
        """空关键词列表应返回 None"""
        matcher = KeywordMatcher([])
        result = matcher.match("任何消息")
        assert result is None

    def test_empty_message_returns_none(self):
        """空消息应返回 None"""
        keywords = [KeywordConfig(keyword="测试", reply="回复")]
        matcher = KeywordMatcher(keywords)
        result = matcher.match("")
        assert result is None

    @given(keyword=non_empty_keyword)
    @settings(max_examples=100)
    def test_exact_keyword_as_message_matches(self, keyword: str):
        """消息正好是关键词时应匹配"""
        keywords = [KeywordConfig(keyword=keyword, reply="回复")]
        matcher = KeywordMatcher(keywords)
        
        result = matcher.match(keyword)
        
        assert result == keyword
