"""回复管理模块

实现意图标签回复获取和关键词回复优先级处理。
"""

import logging

from src.config import ConfigStore
from src.llm_client import ClassifyResult

logger = logging.getLogger(__name__)


class ReplyManager:
    """回复管理器
    
    根据分类结果获取回复内容，实现关键词优先于意图回复的逻辑。
    """

    def __init__(self, config: ConfigStore) -> None:
        """初始化回复管理器
        
        Args:
            config: 配置存储实例
        """
        self._config = config

    def get_reply(self, result: ClassifyResult) -> str | None:
        """根据分类结果获取回复内容
        
        优先级规则：
        1. 如果意图为 IGNORE，返回 None（静默）
        2. 如果意图为 FAQ 且 faq_id 有效，使用 FAQ 预设答案
        3. 如果分类结果包含关键词，优先使用关键词字典的回复
        4. 否则使用意图标签对应的预设回复
        
        Args:
            result: 分类结果，包含意图标签、可选关键词和可选 FAQ ID
            
        Returns:
            回复内容字符串，如果应保持静默则返回 None
        """
        # IGNORE 意图保持静默
        if result.intent == "IGNORE":
            logger.debug("意图为 IGNORE，保持静默")
            return None

        # FAQ 意图处理
        if result.intent == "FAQ" and result.faq_id:
            faq_reply = self._config.get_reply_by_faq_id(result.faq_id)
            if faq_reply is not None:
                logger.debug(f"使用 FAQ 回复: faq_id={result.faq_id}")
                return faq_reply
            else:
                # 无效的 faq_id，回退到 IGNORE
                logger.warning(f"无效的 FAQ ID: {result.faq_id}，回退到静默")
                return None

        # 如果有关键词，优先使用关键词回复
        if result.keyword:
            keyword_reply = self._config.get_reply_by_keyword(result.keyword)
            if keyword_reply is not None:
                logger.debug(f"使用关键词回复: keyword={result.keyword}")
                return keyword_reply

        # 使用意图标签对应的回复
        intent_reply = self._config.get_reply_by_intent(result.intent)
        if intent_reply:
            logger.debug(f"使用意图回复: intent={result.intent}")
            return intent_reply

        # 如果没有找到对应回复，返回 None
        logger.warning(f"未找到回复内容: intent={result.intent}, keyword={result.keyword}, faq_id={result.faq_id}")
        return None
