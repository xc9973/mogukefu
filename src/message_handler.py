"""消息处理模块

实现消息过滤、完整处理流程和开关控制逻辑。
"""

import logging
from dataclasses import dataclass

from src.config import ConfigStore
from src.intent_classifier import IntentClassifier
from src.keyword_matcher import KeywordMatcher
from src.llm_client import ClassifyResult
from src.reply_manager import ReplyManager

logger = logging.getLogger(__name__)


@dataclass
class HandleResult:
    """消息处理结果"""

    should_reply: bool  # 是否应该回复
    reply_text: str | None = None  # 回复内容
    matched_keyword: str | None = None  # 匹配的关键词（如果有）
    intent: str | None = None  # 意图标签（如果有）


class MessageHandler:
    """消息处理器
    
    负责完整的消息处理流程：
    1. 消息过滤（长度、命令）
    2. 关键词匹配（如果开关开启）
    3. AI 意图分类（如果开关开启且关键词未匹配）
    4. 获取回复内容
    """

    # 最小消息长度
    MIN_MESSAGE_LENGTH = 2

    def __init__(
        self,
        config: ConfigStore,
        keyword_matcher: KeywordMatcher,
        classifier: IntentClassifier,
        reply_manager: ReplyManager,
    ) -> None:
        """初始化消息处理器
        
        Args:
            config: 配置存储实例
            keyword_matcher: 关键词匹配器实例
            classifier: 意图分类器实例
            reply_manager: 回复管理器实例
        """
        self._config = config
        self._keyword_matcher = keyword_matcher
        self._classifier = classifier
        self._reply_manager = reply_manager

    def should_ignore_message(self, text: str) -> bool:
        """判断消息是否应被忽略
        
        过滤规则：
        - 消息长度小于 2 个字符
        - 消息以 "/" 开头（命令格式）
        
        Args:
            text: 消息文本
            
        Returns:
            True 表示应忽略，False 表示应处理
        """
        # 检查消息长度
        if len(text) < self.MIN_MESSAGE_LENGTH:
            logger.debug(f"消息过短，忽略: len={len(text)}")
            return True

        # 检查是否为命令格式
        if text.startswith("/"):
            logger.debug(f"命令消息，忽略: {text[:20]}")
            return True

        return False

    async def handle(self, text: str) -> HandleResult:
        """处理消息
        
        完整处理流程：
        1. 消息过滤
        2. 检查开关状态
        3. 关键词匹配（如果开启）
        4. AI 分类（如果开启且关键词未匹配）
        5. 获取回复
        
        Args:
            text: 消息文本
            
        Returns:
            处理结果，包含是否回复、回复内容等信息
        """
        # 1. 消息过滤
        if self.should_ignore_message(text):
            return HandleResult(should_reply=False)

        # 2. 获取开关状态
        bot_config = self._config.get_bot_config()
        keyword_enabled = bot_config.keyword_reply_enabled
        ai_enabled = bot_config.ai_reply_enabled

        # 如果两个开关都关闭，不做任何回复
        if not keyword_enabled and not ai_enabled:
            logger.debug("所有回复开关已关闭")
            return HandleResult(should_reply=False)

        # 3. 关键词匹配（如果开启）
        if keyword_enabled:
            matched_keyword = self._keyword_matcher.match(text)
            if matched_keyword:
                # 关键词匹配成功，直接获取回复
                reply = self._config.get_reply_by_keyword(matched_keyword)
                logger.debug(f"关键词匹配成功: keyword={matched_keyword}")
                return HandleResult(
                    should_reply=True,
                    reply_text=reply,
                    matched_keyword=matched_keyword,
                )

        # 4. AI 分类（如果开启）
        if ai_enabled:
            result = await self._classifier.classify(text)
            
            # 5. 获取回复
            reply = self._reply_manager.get_reply(result)
            
            if reply:
                return HandleResult(
                    should_reply=True,
                    reply_text=reply,
                    matched_keyword=result.keyword,
                    intent=result.intent,
                )
            else:
                # IGNORE 或无回复
                return HandleResult(
                    should_reply=False,
                    intent=result.intent,
                )

        # 关键词未匹配且 AI 关闭
        return HandleResult(should_reply=False)
