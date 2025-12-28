"""意图分类器模块

实现消息意图分类逻辑，调用 LLM 进行意图判断。
"""

import logging

from src.config import ConfigStore
from src.llm_client import ClassifyResult, LLMClient

logger = logging.getLogger(__name__)


class IntentClassifier:
    """意图分类器
    
    负责调用 LLM 对消息进行意图分类，处理异常情况。
    """

    def __init__(self, llm: LLMClient, config: ConfigStore) -> None:
        """初始化意图分类器
        
        Args:
            llm: LLM 客户端实例
            config: 配置存储实例
        """
        self._llm = llm
        self._config = config

    async def classify(self, message: str) -> ClassifyResult:
        """分类消息意图
        
        调用 LLM 对消息进行意图分类，如果发生异常则返回 IGNORE。
        
        Args:
            message: 用户消息文本
            
        Returns:
            分类结果，包含意图标签和可选的关键词
            
        Note:
            - 如果 LLM 调用失败，返回 IGNORE 标签
            - 如果 LLM 返回无效数据，返回 IGNORE 标签
            - 如果 LLM 识别到关键词，结果中会包含该关键词
        """
        try:
            # 获取意图配置和关键词列表
            intents = self._config.get_intents()
            keywords = self._config.get_keywords()
            keyword_list = [kw.keyword for kw in keywords]
            
            # 调用 LLM 进行分类
            result = await self._llm.classify(
                message=message,
                intents=intents,
                keywords=keyword_list,
            )
            
            logger.debug(
                f"消息分类完成: message={message[:50]}..., "
                f"intent={result.intent}, keyword={result.keyword}"
            )
            
            return result
            
        except Exception as e:
            # 任何异常都返回 IGNORE，确保系统稳定
            logger.warning(f"意图分类失败: {e}")
            return ClassifyResult(intent="IGNORE", keyword=None)
