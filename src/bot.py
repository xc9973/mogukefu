"""Telegram Bot 主程序模块

实现 Bot 初始化、启动、消息监听和回复发送功能。
支持普通群组和讨论组（Forum/Topic）模式。
"""

import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler as TelegramMessageHandler,
    filters,
)

from src.config import ConfigStore
from src.intent_classifier import IntentClassifier
from src.keyword_matcher import KeywordMatcher
from src.llm_client import LLMClient
from src.message_handler import MessageHandler
from src.reply_manager import ReplyManager

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram 意图识别机器人
    
    负责：
    - 初始化所有组件
    - 监听群组和讨论组消息
    - 使用 Reply（引用）模式发送回复
    - 支持讨论组 Topic 模式
    """

    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        """初始化 Bot
        
        Args:
            config_path: 配置文件路径
        """
        self._config_path = Path(config_path)
        self._config: ConfigStore | None = None
        self._application: Application | None = None
        self._message_handler: MessageHandler | None = None

    def _init_components(self) -> None:
        """初始化所有组件"""
        # 加载配置
        self._config = ConfigStore()
        self._config.load(self._config_path)
        
        # 获取配置
        bot_config = self._config.get_bot_config()
        llm_config = self._config.get_llm_config()
        keywords = self._config.get_keywords()
        
        # 初始化各组件
        keyword_matcher = KeywordMatcher(keywords)
        llm_client = LLMClient(
            config=llm_config,
            timeout=llm_config.timeout,
            max_retries=llm_config.max_retries,
        )
        classifier = IntentClassifier(llm_client, self._config)
        reply_manager = ReplyManager(self._config)
        
        # 初始化消息处理器
        self._message_handler = MessageHandler(
            config=self._config,
            keyword_matcher=keyword_matcher,
            classifier=classifier,
            reply_manager=reply_manager,
        )
        
        # 初始化 Telegram Application
        self._application = (
            Application.builder()
            .token(bot_config.token)
            .build()
        )
        
        # 注册消息处理器
        # 支持：普通群组、超级群组（Forum）、私聊（包括 Bot 私聊讨论组）
        message_filter = filters.TEXT & ~filters.COMMAND & (
            filters.ChatType.GROUP | 
            filters.ChatType.SUPERGROUP | 
            filters.ChatType.PRIVATE
        )
        
        logger.info("注册消息处理器: 群组 + 讨论组 + 私聊")
        
        self._application.add_handler(
            TelegramMessageHandler(message_filter, self._handle_message)
        )
        
        # 添加调试处理器：捕获所有更新，用于排查问题
        async def debug_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"[DEBUG] 收到更新: {update}")
        
        # 捕获所有文本消息（无过滤）
        self._application.add_handler(
            TelegramMessageHandler(filters.ALL, debug_handler),
            group=1  # 放在不同的 group，不影响主处理器
        )
        
        logger.info("Bot 组件初始化完成")

    async def _handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理 Telegram 消息
        
        Args:
            update: Telegram 更新对象
            context: 上下文对象
        """
        message = update.message
        if not message or not message.text:
            return
        
        text = message.text
        chat_id = message.chat_id
        message_id = message.message_id
        
        # 获取 Topic ID（如果是讨论组消息）
        # message_thread_id 表示消息所属的话题 ID
        topic_id = message.message_thread_id
        
        # 检查是否是讨论组（Forum）
        is_forum = message.chat.is_forum if message.chat else False
        
        # 记录日志
        if is_forum:
            logger.info(
                f"收到讨论组消息: chat_id={chat_id}, topic_id={topic_id}, "
                f"text={text[:50]}..."
            )
        elif topic_id:
            logger.info(
                f"收到话题消息: chat_id={chat_id}, topic_id={topic_id}, "
                f"text={text[:50]}..."
            )
        else:
            logger.info(f"收到群组消息: chat_id={chat_id}, text={text[:50]}...")
        
        # 处理消息
        if self._message_handler is None:
            logger.error("消息处理器未初始化")
            return
        
        result = await self._message_handler.handle(text)
        
        # 如果需要回复
        if result.should_reply and result.reply_text:
            await self._send_reply_with_retry(
                message=message,
                reply_text=result.reply_text,
                topic_id=topic_id,
                chat_id=chat_id,
                matched_keyword=result.matched_keyword,
                intent=result.intent,
            )

    async def _send_reply_with_retry(
        self,
        message,
        reply_text: str,
        topic_id: int | None,
        chat_id: int,
        matched_keyword: str | None,
        intent: str | None,
        max_retries: int = 2,
        retry_delay: float = 0.5,
    ) -> None:
        """发送回复，支持指数退避重试
        
        Args:
            message: Telegram 消息对象
            reply_text: 回复文本
            topic_id: 话题 ID（讨论组模式）
            chat_id: 聊天 ID
            matched_keyword: 匹配的关键词
            intent: 意图标签
            max_retries: 最大重试次数
            retry_delay: 初始重试延迟（秒）
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                await message.reply_text(
                    text=reply_text,
                    message_thread_id=topic_id,
                )
                
                # 成功发送，记录日志
                if matched_keyword:
                    logger.info(
                        f"关键词回复: keyword={matched_keyword}, chat_id={chat_id}"
                    )
                elif intent:
                    logger.info(
                        f"意图回复: intent={intent}, chat_id={chat_id}"
                    )
                return  # 成功，退出
                
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(
                        f"发送回复失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}, "
                        f"{delay:.1f}s 后重试"
                    )
                    await asyncio.sleep(delay)
        
        # 所有重试都失败
        logger.error(f"发送回复最终失败: {last_error}")

    def run(self) -> None:
        """启动 Bot（阻塞运行）
        
        使用 polling 模式监听消息。
        """
        logger.info("正在启动 Bot...")
        
        # 初始化组件
        self._init_components()
        
        if self._application is None:
            raise RuntimeError("Application 未初始化")
        
        logger.info("Bot 启动成功，开始监听消息...")
        
        # 使用 polling 模式运行
        self._application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,  # 忽略启动前的消息
        )

    async def start_async(self) -> None:
        """异步启动 Bot
        
        用于测试或需要异步控制的场景。
        """
        logger.info("正在异步启动 Bot...")
        
        # 初始化组件
        self._init_components()
        
        if self._application is None:
            raise RuntimeError("Application 未初始化")
        
        # 初始化 Application
        await self._application.initialize()
        await self._application.start()
        
        # 启动 polling
        await self._application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        
        logger.info("Bot 异步启动成功")

    async def stop_async(self) -> None:
        """异步停止 Bot"""
        if self._application is None:
            return
        
        logger.info("正在停止 Bot...")
        
        if self._application.updater and self._application.updater.running:
            await self._application.updater.stop()
        
        await self._application.stop()
        await self._application.shutdown()
        
        logger.info("Bot 已停止")


def setup_logging(level: int = logging.INFO) -> None:
    """配置日志
    
    Args:
        level: 日志级别
    """
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level,
    )
    # 降低 httpx 日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    """主入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Telegram Intent Bot")
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细日志",
    )
    args = parser.parse_args()
    
    # 配置日志
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    # 启动 Bot
    bot = TelegramBot(config_path=args.config)
    bot.run()


if __name__ == "__main__":
    main()
