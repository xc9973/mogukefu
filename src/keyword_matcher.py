"""关键词匹配模块

实现精确关键词匹配逻辑，支持多匹配优先级处理。
"""

from src.config import KeywordConfig


class KeywordMatcher:
    """关键词匹配器
    
    根据配置的关键词列表，对消息文本进行精确匹配。
    匹配规则：
    - 检查消息文本是否包含关键词
    - 如果匹配多个关键词，返回配置顺序中的第一个
    """

    def __init__(self, keywords: list[KeywordConfig]) -> None:
        """初始化关键词匹配器
        
        Args:
            keywords: 关键词配置列表，按优先级排序
        """
        self._keywords = keywords

    def match(self, text: str) -> str | None:
        """精确匹配关键词
        
        检查消息文本是否包含配置的关键词。
        如果匹配多个关键词，返回配置顺序中的第一个。
        
        Args:
            text: 消息文本
            
        Returns:
            匹配到的关键词，无匹配返回 None
        """
        for kw_config in self._keywords:
            if kw_config.keyword in text:
                return kw_config.keyword
        return None
