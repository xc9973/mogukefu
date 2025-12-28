"""LLMClient 属性测试

Feature: telegram-intent-bot
Property 2: JSON 解析健壮性
Property 3: 意图标签有效性
Property 7: 错误处理降级
Validates: Requirements 2.3, 2.4, 2.5, 5.6
"""

import json

from hypothesis import given, settings, strategies as st

from src.config import VALID_INTENT_TAGS
from src.llm_client import ClassifyResult, LLMClient, LLMConfig


# ============================================================================
# 测试数据生成策略
# ============================================================================

# 有效的意图标签
valid_intent_tags = st.sampled_from(list(VALID_INTENT_TAGS))

# 无效的意图标签（不在有效集合中的字符串）
invalid_intent_tags = st.text(min_size=1, max_size=20).filter(
    lambda x: x.strip() and x not in VALID_INTENT_TAGS
)

# 可选的关键词（字符串或 None）
optional_keyword = st.one_of(st.none(), st.text(min_size=1, max_size=20))

# 非 JSON 字符串
non_json_strings = st.text(min_size=1, max_size=100).filter(
    lambda x: not _is_valid_json(x)
)


def _is_valid_json(s: str) -> bool:
    """检查字符串是否是有效的 JSON"""
    try:
        json.loads(s)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def create_test_llm_client() -> LLMClient:
    """创建测试用的 LLMClient 实例"""
    config = LLMConfig(
        base_url="https://api.example.com/v1",
        api_key="test_key",
        model="gpt-3.5-turbo",
        temperature=0.0,
    )
    return LLMClient(config)


# ============================================================================
# Property 2: JSON 解析健壮性
# Feature: telegram-intent-bot, Property 2: JSON 解析健壮性
# Validates: Requirements 2.3, 2.4
# ============================================================================

class TestProperty2JsonParsingRobustness:
    """Property 2: JSON 解析健壮性

    *For any* LLM 返回的字符串，如果是有效 JSON 且包含有效意图标签，
    则应正确解析；否则应返回 IGNORE 标签。
    """

    @given(
        intent=valid_intent_tags,
        keyword=optional_keyword,
    )
    @settings(max_examples=100)
    def test_valid_json_with_valid_intent_parses_correctly(
        self, intent: str, keyword: str | None
    ):
        """有效 JSON 且包含有效意图标签应正确解析"""
        client = create_test_llm_client()
        
        # 构造有效的 JSON 响应
        response_data = {"intent": intent, "keyword": keyword}
        response_text = json.dumps(response_data)
        
        result = client._parse_response(response_text)
        
        assert result.intent == intent
        assert result.keyword == keyword

    @given(response_text=non_json_strings)
    @settings(max_examples=100)
    def test_non_json_returns_ignore(self, response_text: str):
        """非 JSON 格式应返回 IGNORE"""
        client = create_test_llm_client()
        
        result = client._parse_response(response_text)
        
        assert result.intent == "IGNORE"

    @given(
        invalid_intent=invalid_intent_tags,
        keyword=optional_keyword,
    )
    @settings(max_examples=100)
    def test_invalid_intent_tag_returns_ignore(
        self, invalid_intent: str, keyword: str | None
    ):
        """无效意图标签应返回 IGNORE"""
        client = create_test_llm_client()
        
        response_data = {"intent": invalid_intent, "keyword": keyword}
        response_text = json.dumps(response_data)
        
        result = client._parse_response(response_text)
        
        assert result.intent == "IGNORE"

    def test_empty_string_returns_ignore(self):
        """空字符串应返回 IGNORE"""
        client = create_test_llm_client()
        
        result = client._parse_response("")
        
        assert result.intent == "IGNORE"

    def test_json_array_returns_ignore(self):
        """JSON 数组应返回 IGNORE"""
        client = create_test_llm_client()
        
        result = client._parse_response('["TUTORIAL"]')
        
        assert result.intent == "IGNORE"

    def test_json_without_intent_field_returns_ignore(self):
        """缺少 intent 字段的 JSON 应返回 IGNORE"""
        client = create_test_llm_client()
        
        result = client._parse_response('{"keyword": "test"}')
        
        assert result.intent == "IGNORE"

    @given(whitespace=st.text(alphabet=" \t\n\r", min_size=0, max_size=5))
    @settings(max_examples=100)
    def test_json_with_whitespace_parses_correctly(self, whitespace: str):
        """带空白字符的 JSON 应正确解析"""
        client = create_test_llm_client()
        
        response_text = f'{whitespace}{{"intent": "TUTORIAL", "keyword": null}}{whitespace}'
        
        result = client._parse_response(response_text)
        
        assert result.intent == "TUTORIAL"


# ============================================================================
# Property 3: 意图标签有效性
# Feature: telegram-intent-bot, Property 3: 意图标签有效性
# Validates: Requirements 2.5
# ============================================================================

class TestProperty3IntentTagValidity:
    """Property 3: 意图标签有效性

    *For any* 分类结果，返回的意图标签必须是 TUTORIAL、ISSUE、SERVICE、IGNORE 之一。
    """

    @given(
        intent=valid_intent_tags,
        keyword=optional_keyword,
    )
    @settings(max_examples=100)
    def test_parsed_intent_is_always_valid(self, intent: str, keyword: str | None):
        """解析结果的意图标签始终有效"""
        client = create_test_llm_client()
        
        response_data = {"intent": intent, "keyword": keyword}
        response_text = json.dumps(response_data)
        
        result = client._parse_response(response_text)
        
        assert result.intent in VALID_INTENT_TAGS

    @given(response_text=st.text(max_size=200))
    @settings(max_examples=100)
    def test_any_input_returns_valid_intent(self, response_text: str):
        """任意输入都应返回有效的意图标签"""
        client = create_test_llm_client()
        
        result = client._parse_response(response_text)
        
        # 无论输入是什么，返回的意图标签必须是有效的
        assert result.intent in VALID_INTENT_TAGS

    def test_all_valid_tags_are_accepted(self):
        """所有有效标签都应被接受"""
        client = create_test_llm_client()
        
        for tag in VALID_INTENT_TAGS:
            response_text = json.dumps({"intent": tag, "keyword": None})
            result = client._parse_response(response_text)
            assert result.intent == tag


# ============================================================================
# Property 7: 错误处理降级
# Feature: telegram-intent-bot, Property 7: 错误处理降级
# Validates: Requirements 2.4, 5.6
# ============================================================================

class TestProperty7ErrorHandlingDegradation:
    """Property 7: 错误处理降级

    *For any* LLM 调用失败或返回无效数据的情况，
    系统应返回 IGNORE 标签，确保不会因异常而崩溃。
    """

    @given(
        malformed_json=st.one_of(
            st.just("{"),
            st.just("}"),
            st.just('{"intent":}'),
            st.just('{"intent": "TUTORIAL"'),
            st.text(min_size=1, max_size=50).filter(lambda x: not _is_valid_json(x)),
        )
    )
    @settings(max_examples=100)
    def test_malformed_json_returns_ignore(self, malformed_json: str):
        """格式错误的 JSON 应返回 IGNORE"""
        client = create_test_llm_client()
        
        result = client._parse_response(malformed_json)
        
        assert result.intent == "IGNORE"
        # 确保不会抛出异常
        assert isinstance(result, ClassifyResult)

    @given(
        non_string_intent=st.one_of(
            st.integers(),
            st.floats(allow_nan=False),
            st.booleans(),
            st.lists(st.text(max_size=10), max_size=3),
        )
    )
    @settings(max_examples=100)
    def test_non_string_intent_returns_ignore(self, non_string_intent):
        """非字符串类型的意图应返回 IGNORE"""
        client = create_test_llm_client()
        
        response_data = {"intent": non_string_intent, "keyword": None}
        response_text = json.dumps(response_data)
        
        result = client._parse_response(response_text)
        
        assert result.intent == "IGNORE"

    def test_null_intent_returns_ignore(self):
        """null 意图应返回 IGNORE"""
        client = create_test_llm_client()
        
        result = client._parse_response('{"intent": null, "keyword": null}')
        
        assert result.intent == "IGNORE"

    @given(
        non_string_keyword=st.one_of(
            st.integers(),
            st.floats(allow_nan=False),
            st.booleans(),
            st.lists(st.text(max_size=10), max_size=3),
        )
    )
    @settings(max_examples=100)
    def test_non_string_keyword_is_ignored(self, non_string_keyword):
        """非字符串类型的关键词应被忽略（设为 None）"""
        client = create_test_llm_client()
        
        response_data = {"intent": "TUTORIAL", "keyword": non_string_keyword}
        response_text = json.dumps(response_data)
        
        result = client._parse_response(response_text)
        
        # 意图应正确解析
        assert result.intent == "TUTORIAL"
        # 非字符串关键词应被设为 None
        assert result.keyword is None

    def test_deeply_nested_json_returns_ignore(self):
        """深度嵌套的 JSON 应返回 IGNORE（因为不是预期格式）"""
        client = create_test_llm_client()
        
        result = client._parse_response('{"intent": {"nested": "TUTORIAL"}}')
        
        assert result.intent == "IGNORE"

    @given(extra_fields=st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=20), max_size=5))
    @settings(max_examples=100)
    def test_extra_fields_are_ignored(self, extra_fields: dict):
        """额外字段应被忽略，不影响解析"""
        client = create_test_llm_client()
        
        response_data = {"intent": "TUTORIAL", "keyword": "test", **extra_fields}
        response_text = json.dumps(response_data)
        
        result = client._parse_response(response_text)
        
        assert result.intent == "TUTORIAL"
        assert result.keyword == "test"
