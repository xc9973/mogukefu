"""LLM 客户端模块

实现 OpenAI 格式 API 调用、System Prompt 构建和 JSON 响应解析。
"""

import json
import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from src.config import IntentConfig, LLMConfig, FAQConfig, VALID_INTENT_TAGS

logger = logging.getLogger(__name__)


@dataclass
class ClassifyResult:
    """分类结果"""

    intent: str  # 意图标签
    keyword: str | None = None  # 识别的关键词（可选）
    faq_id: str | None = None  # 匹配的 FAQ ID（可选）


class LLMClient:
    """LLM 客户端
    
    负责与 OpenAI 格式 API 通信，进行意图分类。
    """

    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 30.0
    # 默认重试次数
    DEFAULT_MAX_RETRIES = 2

    def __init__(
        self,
        config: LLMConfig,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """初始化 LLM 客户端
        
        Args:
            config: LLM 配置，包含 API 地址、密钥和模型名称
            timeout: API 调用超时时间（秒）
            max_retries: API 调用失败时的最大重试次数
        """
        self._config = config
        self._client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _build_system_prompt(
        self, intents: list[IntentConfig], keywords: list[str], faqs: list[FAQConfig]
    ) -> str:
        """构建 System Prompt
        
        Args:
            intents: 意图配置列表
            keywords: 关键词列表
            faqs: FAQ 配置列表
            
        Returns:
            System Prompt 字符串
        """
        # 构建意图标签描述
        intent_descriptions = []
        for intent in intents:
            intent_descriptions.append(f"- {intent.tag}: {intent.description}")
        # 如果有 FAQ，添加 FAQ 意图说明
        if faqs:
            intent_descriptions.append("- FAQ: 用户询问常见问题（见下方 FAQ 列表）")
        intents_text = "\n".join(intent_descriptions)

        # 构建关键词列表
        keywords_text = ", ".join(keywords) if keywords else "无"

        # 构建 FAQ 列表
        if faqs:
            faq_descriptions = []
            for faq in faqs:
                faq_descriptions.append(f"- {faq.faq_id}: {faq.question}")
            faqs_text = "\n".join(faq_descriptions)
            faq_section = f"""

FAQ 列表：
{faqs_text}"""
            faq_rule = """
4. 如果消息匹配某个 FAQ，返回 intent 为 "FAQ"，并在 faq_id 字段返回对应 ID
5. FAQ 优先级高于普通意图标签"""
            output_format = '{"intent": "TAG", "keyword": "关键词或null", "faq_id": "FAQ_ID或null"}'
        else:
            faq_section = ""
            faq_rule = ""
            output_format = '{"intent": "TAG", "keyword": "关键词或null", "faq_id": null}'

        return f"""你是一个意图分类器。根据用户消息，判断其意图并返回 JSON 格式结果。

可用意图标签：
{intents_text}

可用关键词：{keywords_text}{faq_section}

规则：
1. 只输出 JSON，不要任何解释
2. 如果消息明确匹配某个关键词的语义，在 keyword 字段返回该关键词
3. 否则只返回 intent 字段，keyword 设为 null{faq_rule}
6. 不要与用户对话，不要输出任何解释性文字

输出格式：{{{output_format}}}"""

    def _parse_response(self, response_text: str) -> ClassifyResult:
        """解析 LLM 响应
        
        Args:
            response_text: LLM 返回的文本
            
        Returns:
            分类结果
            
        Note:
            如果解析失败或标签无效，返回 IGNORE
        """
        try:
            # 尝试解析 JSON
            data = json.loads(response_text.strip())
            
            if not isinstance(data, dict):
                logger.warning(f"LLM 返回非字典类型: {type(data)}")
                return ClassifyResult(intent="IGNORE")

            # 提取意图标签
            intent = data.get("intent", "IGNORE")
            if not isinstance(intent, str):
                logger.warning(f"意图标签类型错误: {type(intent)}")
                return ClassifyResult(intent="IGNORE")

            # 验证意图标签有效性
            if intent not in VALID_INTENT_TAGS:
                logger.warning(f"无效的意图标签: {intent}")
                return ClassifyResult(intent="IGNORE")

            # 提取关键词（可选）
            keyword = data.get("keyword")
            if keyword is not None and not isinstance(keyword, str):
                keyword = None

            # 提取 FAQ ID（可选）
            faq_id = data.get("faq_id")
            if faq_id is not None and not isinstance(faq_id, str):
                faq_id = None

            return ClassifyResult(intent=intent, keyword=keyword, faq_id=faq_id)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 原文: {response_text}")
            return ClassifyResult(intent="IGNORE")

    async def classify(
        self,
        message: str,
        intents: list[IntentConfig],
        keywords: list[str],
        faqs: list[FAQConfig] | None = None,
    ) -> ClassifyResult:
        """调用 LLM 进行意图分类
        
        Args:
            message: 用户消息
            intents: 意图配置列表
            keywords: 关键词列表
            faqs: FAQ 配置列表（可选）
            
        Returns:
            分类结果，包含意图标签、可选关键词和可选 FAQ ID
            
        Note:
            如果 API 调用失败，返回 IGNORE 标签
        """
        try:
            system_prompt = self._build_system_prompt(intents, keywords, faqs or [])
            
            response = await self._client.chat.completions.create(
                model=self._config.model,
                temperature=self._config.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
            )

            response_text = response.choices[0].message.content or ""
            return self._parse_response(response_text)

        except Exception as e:
            logger.warning(f"LLM 调用失败: {e}")
            return ClassifyResult(intent="IGNORE")
