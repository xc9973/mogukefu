"""ConfigStore 属性测试

Feature: telegram-intent-bot
Property 5: 配置加载与验证
Property 6: 意图回复完整性
Validates: Requirements 4.1, 4.2, 4.4
"""

import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings, strategies as st

from src.config import (
    ConfigError,
    ConfigStore,
    VALID_INTENT_TAGS,
)


# ============================================================================
# 测试数据生成策略
# ============================================================================

# 生成有效的意图标签
valid_intent_tags = st.sampled_from(list(VALID_INTENT_TAGS))

# 生成非空字符串（用于必填字段）- 限制为 ASCII 可打印字符避免 YAML 序列化问题
non_empty_string = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S'), 
                           whitelist_characters=' ',
                           blacklist_characters='\x00\x85\u2028\u2029'),
    min_size=1, 
    max_size=50
).filter(lambda x: x.strip())

# 生成有效的意图配置
valid_intent_config = st.fixed_dictionaries({
    "tag": valid_intent_tags,
    "description": st.text(max_size=100),
    "reply": st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
})

# 生成有效的关键词配置
valid_keyword_config = st.fixed_dictionaries({
    "keyword": non_empty_string,
    "reply": st.text(max_size=200),
})


def make_valid_config(
    token: str = "test_token",
    base_url: str = "https://api.example.com/v1",
    api_key: str = "test_key",
    model: str = "gpt-3.5-turbo",
    intents: list | None = None,
    keywords: list | None = None,
    keyword_reply_enabled: bool = True,
    ai_reply_enabled: bool = True,
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
            "token": token,
            "keyword_reply_enabled": keyword_reply_enabled,
            "ai_reply_enabled": ai_reply_enabled,
        },
        "llm": {
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
        },
        "intents": intents,
        "keywords": keywords or [],
    }


def write_config_file(config: dict, path: Path) -> None:
    """将配置写入 YAML 文件"""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)


# ============================================================================
# Property 5: 配置加载与验证
# Feature: telegram-intent-bot, Property 5: 配置加载与验证
# Validates: Requirements 4.1, 4.2
# ============================================================================

class TestProperty5ConfigLoadAndValidation:
    """Property 5: 配置加载与验证

    *For any* 有效的 YAML 配置文件，Config_Store 应能正确加载；
    对于无效配置，应抛出明确的错误。
    """

    @given(
        token=non_empty_string,
        base_url=non_empty_string,
        api_key=non_empty_string,
        model=non_empty_string,
    )
    @settings(max_examples=100)
    def test_valid_config_loads_successfully(
        self, token: str, base_url: str, api_key: str, model: str
    ):
        """有效配置应能成功加载"""
        config = make_valid_config(
            token=token,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config, f, allow_unicode=True)
            config_path = Path(f.name)

        try:
            store = ConfigStore()
            store.load(config_path)

            # 验证加载的配置
            bot_config = store.get_bot_config()
            assert bot_config.token == token

            llm_config = store.get_llm_config()
            assert llm_config.base_url == base_url
            assert llm_config.api_key == api_key
            assert llm_config.model == model
        finally:
            config_path.unlink()

    def test_missing_file_raises_error(self):
        """不存在的配置文件应抛出错误"""
        store = ConfigStore()
        with pytest.raises(ConfigError, match="配置文件不存在"):
            store.load("/nonexistent/path/config.yaml")

    def test_invalid_yaml_raises_error(self):
        """无效 YAML 格式应抛出错误"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("invalid: yaml: content: [")
            config_path = Path(f.name)

        try:
            store = ConfigStore()
            with pytest.raises(ConfigError, match="YAML 格式错误"):
                store.load(config_path)
        finally:
            config_path.unlink()

    def test_missing_bot_section_raises_error(self):
        """缺少 bot 配置节应抛出错误"""
        config = {"llm": {"base_url": "url", "api_key": "key", "model": "model"}}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config, f)
            config_path = Path(f.name)

        try:
            store = ConfigStore()
            with pytest.raises(ConfigError, match="缺少 bot 配置节"):
                store.load(config_path)
        finally:
            config_path.unlink()

    def test_missing_llm_section_raises_error(self):
        """缺少 llm 配置节应抛出错误"""
        config = {"bot": {"token": "token"}}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config, f)
            config_path = Path(f.name)

        try:
            store = ConfigStore()
            with pytest.raises(ConfigError, match="缺少 llm 配置节"):
                store.load(config_path)
        finally:
            config_path.unlink()

    @given(invalid_tag=st.text(min_size=1).filter(lambda x: x not in VALID_INTENT_TAGS))
    @settings(max_examples=100)
    def test_invalid_intent_tag_raises_error(self, invalid_tag: str):
        """无效的意图标签应抛出错误"""
        config = make_valid_config(
            intents=[{"tag": invalid_tag, "description": "desc", "reply": "reply"}]
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config, f, allow_unicode=True)
            config_path = Path(f.name)

        try:
            store = ConfigStore()
            with pytest.raises(ConfigError, match="无效"):
                store.load(config_path)
        finally:
            config_path.unlink()


# ============================================================================
# Property 6: 意图回复完整性
# Feature: telegram-intent-bot, Property 6: 意图回复完整性
# Validates: Requirements 4.4
# ============================================================================

class TestProperty6IntentReplyCompleteness:
    """Property 6: 意图回复完整性

    *For any* 有效意图标签（非 IGNORE），Config_Store 应能提供对应的非空预设回复内容。
    """

    @given(
        tag=st.sampled_from(["TUTORIAL", "ISSUE", "SERVICE"]),
        reply=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100)
    def test_non_ignore_intent_has_reply(self, tag: str, reply: str):
        """非 IGNORE 意图应有非空回复"""
        # 构建包含所有必需意图的配置
        intents = [
            {"tag": "TUTORIAL", "description": "教程", "reply": "教程回复" if tag != "TUTORIAL" else reply},
            {"tag": "ISSUE", "description": "问题", "reply": "问题回复" if tag != "ISSUE" else reply},
            {"tag": "SERVICE", "description": "客服", "reply": "客服回复" if tag != "SERVICE" else reply},
            {"tag": "IGNORE", "description": "忽略", "reply": ""},
        ]
        config = make_valid_config(intents=intents)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config, f, allow_unicode=True)
            config_path = Path(f.name)

        try:
            store = ConfigStore()
            store.load(config_path)

            # 验证非 IGNORE 意图有回复
            result = store.get_reply_by_intent(tag)
            assert result is not None
            assert result.strip() != ""
        finally:
            config_path.unlink()

    def test_ignore_intent_can_have_empty_reply(self):
        """IGNORE 意图可以有空回复"""
        config = make_valid_config()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config, f, allow_unicode=True)
            config_path = Path(f.name)

        try:
            store = ConfigStore()
            store.load(config_path)

            # IGNORE 意图的回复可以为空
            result = store.get_reply_by_intent("IGNORE")
            assert result == ""
        finally:
            config_path.unlink()

    @given(tag=st.sampled_from(["TUTORIAL", "ISSUE", "SERVICE"]))
    @settings(max_examples=100)
    def test_non_ignore_intent_without_reply_raises_error(self, tag: str):
        """非 IGNORE 意图缺少回复应抛出错误"""
        # 构建一个非 IGNORE 意图没有回复的配置
        intents = [
            {"tag": tag, "description": "描述", "reply": ""},  # 空回复
        ]
        config = make_valid_config(intents=intents)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config, f, allow_unicode=True)
            config_path = Path(f.name)

        try:
            store = ConfigStore()
            with pytest.raises(ConfigError, match="必须有非空的回复内容"):
                store.load(config_path)
        finally:
            config_path.unlink()

    def test_all_valid_intents_have_replies(self):
        """所有有效意图标签都应能获取回复"""
        config = make_valid_config()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config, f, allow_unicode=True)
            config_path = Path(f.name)

        try:
            store = ConfigStore()
            store.load(config_path)

            # 验证所有配置的意图都能获取回复
            for tag in ["TUTORIAL", "ISSUE", "SERVICE", "IGNORE"]:
                result = store.get_reply_by_intent(tag)
                assert result is not None
                if tag != "IGNORE":
                    assert result.strip() != ""
        finally:
            config_path.unlink()
