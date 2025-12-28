"""配置管理模块

实现配置文件的加载、验证和访问功能。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """配置错误异常"""

    pass


@dataclass
class LLMConfig:
    """LLM 配置"""

    base_url: str
    api_key: str
    model: str
    temperature: float = 0.0
    timeout: float = 30.0  # API 超时时间（秒）
    max_retries: int = 2   # 最大重试次数

    def __post_init__(self) -> None:
        """验证配置值"""
        if not 0.0 <= self.temperature <= 2.0:
            raise ConfigError(f"temperature 必须在 0.0-2.0 之间，当前值: {self.temperature}")
        if self.timeout <= 0:
            raise ConfigError(f"timeout 必须大于 0，当前值: {self.timeout}")
        if self.max_retries < 0:
            raise ConfigError(f"max_retries 不能为负数，当前值: {self.max_retries}")


@dataclass
class BotConfig:
    """Bot 配置"""

    token: str
    keyword_reply_enabled: bool = True
    ai_reply_enabled: bool = True


@dataclass
class IntentConfig:
    """意图配置"""

    tag: str
    description: str
    reply: str


@dataclass
class KeywordConfig:
    """关键词配置"""

    keyword: str
    reply: str


@dataclass
class FAQConfig:
    """FAQ 配置"""

    faq_id: str
    question: str
    answer: str


# 有效的意图标签
VALID_INTENT_TAGS = {"TUTORIAL", "ISSUE", "SERVICE", "IGNORE", "FAQ"}


@dataclass
class ConfigStore:
    """配置存储类

    负责加载、验证和提供配置数据的访问。
    """

    _bot_config: BotConfig | None = field(default=None, repr=False)
    _llm_config: LLMConfig | None = field(default=None, repr=False)
    _intents: list[IntentConfig] = field(default_factory=list, repr=False)
    _keywords: list[KeywordConfig] = field(default_factory=list, repr=False)
    _faqs: list[FAQConfig] = field(default_factory=list, repr=False)
    _intent_reply_map: dict[str, str] = field(default_factory=dict, repr=False)
    _keyword_reply_map: dict[str, str] = field(default_factory=dict, repr=False)
    _faq_reply_map: dict[str, str] = field(default_factory=dict, repr=False)

    def load(self, path: str | Path) -> None:
        """从 YAML 文件加载配置

        Args:
            path: 配置文件路径

        Raises:
            ConfigError: 配置文件不存在、格式错误或验证失败
        """
        path = Path(path)

        if not path.exists():
            raise ConfigError(f"配置文件不存在: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"YAML 格式错误: {e}")

        if not isinstance(data, dict):
            raise ConfigError("配置文件格式错误: 根节点必须是字典")

        self._parse_bot_config(data)
        self._parse_llm_config(data)
        self._parse_intents(data)
        self._parse_keywords(data)
        self._parse_faqs(data)
        self._validate_intents()

    def _parse_bot_config(self, data: dict[str, Any]) -> None:
        """解析 Bot 配置"""
        bot_data = data.get("bot")
        if not bot_data:
            raise ConfigError("缺少 bot 配置节")

        if not isinstance(bot_data, dict):
            raise ConfigError("bot 配置节必须是字典")

        token = bot_data.get("token")
        if not token or not isinstance(token, str):
            raise ConfigError("bot.token 必须是非空字符串")

        self._bot_config = BotConfig(
            token=token,
            keyword_reply_enabled=bool(bot_data.get("keyword_reply_enabled", True)),
            ai_reply_enabled=bool(bot_data.get("ai_reply_enabled", True)),
        )

    def _parse_llm_config(self, data: dict[str, Any]) -> None:
        """解析 LLM 配置"""
        llm_data = data.get("llm")
        if not llm_data:
            raise ConfigError("缺少 llm 配置节")

        if not isinstance(llm_data, dict):
            raise ConfigError("llm 配置节必须是字典")

        base_url = llm_data.get("base_url")
        if not base_url or not isinstance(base_url, str):
            raise ConfigError("llm.base_url 必须是非空字符串")

        api_key = llm_data.get("api_key")
        if not api_key or not isinstance(api_key, str):
            raise ConfigError("llm.api_key 必须是非空字符串")

        model = llm_data.get("model")
        if not model or not isinstance(model, str):
            raise ConfigError("llm.model 必须是非空字符串")

        temperature = llm_data.get("temperature", 0.0)
        if not isinstance(temperature, (int, float)):
            raise ConfigError("llm.temperature 必须是数字")

        timeout = llm_data.get("timeout", 30.0)
        if not isinstance(timeout, (int, float)):
            raise ConfigError("llm.timeout 必须是数字")

        max_retries = llm_data.get("max_retries", 2)
        if not isinstance(max_retries, int):
            raise ConfigError("llm.max_retries 必须是整数")

        self._llm_config = LLMConfig(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=float(temperature),
            timeout=float(timeout),
            max_retries=max_retries,
        )

    def _parse_intents(self, data: dict[str, Any]) -> None:
        """解析意图配置"""
        intents_data = data.get("intents", [])
        if not isinstance(intents_data, list):
            raise ConfigError("intents 配置节必须是列表")

        self._intents = []
        self._intent_reply_map = {}

        for i, intent_data in enumerate(intents_data):
            if not isinstance(intent_data, dict):
                raise ConfigError(f"intents[{i}] 必须是字典")

            tag = intent_data.get("tag")
            if not tag or not isinstance(tag, str):
                raise ConfigError(f"intents[{i}].tag 必须是非空字符串")

            if tag not in VALID_INTENT_TAGS:
                raise ConfigError(
                    f"intents[{i}].tag '{tag}' 无效，必须是 {VALID_INTENT_TAGS} 之一"
                )

            description = intent_data.get("description", "")
            if not isinstance(description, str):
                raise ConfigError(f"intents[{i}].description 必须是字符串")

            reply = intent_data.get("reply", "")
            if not isinstance(reply, str):
                raise ConfigError(f"intents[{i}].reply 必须是字符串")

            intent = IntentConfig(tag=tag, description=description, reply=reply)
            self._intents.append(intent)
            self._intent_reply_map[tag] = reply

    def _parse_keywords(self, data: dict[str, Any]) -> None:
        """解析关键词配置"""
        keywords_data = data.get("keywords", [])
        if not isinstance(keywords_data, list):
            raise ConfigError("keywords 配置节必须是列表")

        self._keywords = []
        self._keyword_reply_map = {}

        for i, kw_data in enumerate(keywords_data):
            if not isinstance(kw_data, dict):
                raise ConfigError(f"keywords[{i}] 必须是字典")

            keyword = kw_data.get("keyword")
            if not keyword or not isinstance(keyword, str):
                raise ConfigError(f"keywords[{i}].keyword 必须是非空字符串")

            reply = kw_data.get("reply", "")
            if not isinstance(reply, str):
                raise ConfigError(f"keywords[{i}].reply 必须是字符串")

            kw_config = KeywordConfig(keyword=keyword, reply=reply)
            self._keywords.append(kw_config)
            self._keyword_reply_map[keyword] = reply

    def _parse_faqs(self, data: dict[str, Any]) -> None:
        """解析 FAQ 配置"""
        faqs_data = data.get("faq", [])
        if not isinstance(faqs_data, list):
            raise ConfigError("faq 配置节必须是列表")

        self._faqs = []
        self._faq_reply_map = {}

        for i, faq_data in enumerate(faqs_data):
            if not isinstance(faq_data, dict):
                raise ConfigError(f"faq[{i}] 必须是字典")

            faq_id = faq_data.get("faq_id")
            if not faq_id or not isinstance(faq_id, str):
                raise ConfigError(f"faq[{i}].faq_id 必须是非空字符串")

            question = faq_data.get("question", "")
            if not isinstance(question, str):
                raise ConfigError(f"faq[{i}].question 必须是字符串")

            answer = faq_data.get("answer", "")
            if not isinstance(answer, str):
                raise ConfigError(f"faq[{i}].answer 必须是字符串")

            faq_config = FAQConfig(faq_id=faq_id, question=question, answer=answer)
            self._faqs.append(faq_config)
            self._faq_reply_map[faq_id] = answer

    def _validate_intents(self) -> None:
        """验证意图配置完整性"""
        # 检查非 IGNORE 意图是否都有回复内容
        for intent in self._intents:
            if intent.tag != "IGNORE" and not intent.reply.strip():
                raise ConfigError(f"意图 {intent.tag} 必须有非空的回复内容")

    def get_bot_config(self) -> BotConfig:
        """获取 Bot 配置"""
        if self._bot_config is None:
            raise ConfigError("配置未加载")
        return self._bot_config

    def get_llm_config(self) -> LLMConfig:
        """获取 LLM 配置"""
        if self._llm_config is None:
            raise ConfigError("配置未加载")
        return self._llm_config

    def get_intents(self) -> list[IntentConfig]:
        """获取所有意图配置"""
        return self._intents.copy()

    def get_keywords(self) -> list[KeywordConfig]:
        """获取所有关键词配置"""
        return self._keywords.copy()

    def get_faqs(self) -> list[FAQConfig]:
        """获取所有 FAQ 配置"""
        return self._faqs.copy()

    def get_reply_by_intent(self, tag: str) -> str | None:
        """根据意图标签获取回复内容

        Args:
            tag: 意图标签

        Returns:
            回复内容，如果标签不存在返回 None
        """
        return self._intent_reply_map.get(tag)

    def get_reply_by_keyword(self, keyword: str) -> str | None:
        """根据关键词获取回复内容

        Args:
            keyword: 关键词

        Returns:
            回复内容，如果关键词不存在返回 None
        """
        return self._keyword_reply_map.get(keyword)

    def get_reply_by_faq_id(self, faq_id: str) -> str | None:
        """根据 FAQ ID 获取回复内容

        Args:
            faq_id: FAQ 唯一标识

        Returns:
            回复内容，如果 FAQ ID 不存在返回 None
        """
        return self._faq_reply_map.get(faq_id)
