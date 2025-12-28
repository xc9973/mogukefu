"""Bot 集成测试

测试消息接收和回复、讨论组消息处理。
Validates: Requirements 1.1, 1.2, 9.1, 9.3
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.bot import TelegramBot, setup_logging
from src.config import ConfigStore
from src.message_handler import HandleResult


def make_valid_config() -> dict:
    """创建有效的配置字典"""
    return {
        "bot": {
            "token": "test_token_123456",
            "keyword_reply_enabled": True,
            "ai_reply_enabled": True,
        },
        "llm": {
            "base_url": "https://api.example.com/v1",
            "api_key": "test_key",
            "model": "gpt-3.5-turbo",
        },
        "intents": [
            {"tag": "TUTORIAL", "description": "教程", "reply": "教程回复"},
            {"tag": "ISSUE", "description": "问题", "reply": "问题回复"},
            {"tag": "SERVICE", "description": "客服", "reply": "客服回复"},
            {"tag": "IGNORE", "description": "忽略", "reply": ""},
        ],
        "keywords": [
            {"keyword": "教程", "reply": "关键词教程回复"},
            {"keyword": "客服", "reply": "关键词客服回复"},
        ],
    }


def create_config_file(config: dict) -> Path:
    """创建临时配置文件"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(config, f, allow_unicode=True)
        return Path(f.name)


def create_mock_message(
    text: str,
    chat_id: int = 12345,
    message_id: int = 1,
    message_thread_id: int | None = None,
) -> MagicMock:
    """创建模拟的 Telegram Message 对象"""
    message = MagicMock()
    message.text = text
    message.chat_id = chat_id
    message.message_id = message_id
    message.message_thread_id = message_thread_id
    message.reply_text = AsyncMock()
    return message


def create_mock_update(message: MagicMock) -> MagicMock:
    """创建模拟的 Telegram Update 对象"""
    update = MagicMock()
    update.message = message
    return update


class TestBotInitialization:
    """测试 Bot 初始化"""

    def test_bot_creation(self):
        """测试 Bot 实例创建"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            assert bot._config_path == config_path
            assert bot._config is None  # 未初始化
            assert bot._application is None
        finally:
            config_path.unlink()

    def test_bot_init_components(self):
        """测试 Bot 组件初始化"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            # 模拟 Application.builder
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
                
                # 验证组件已初始化
                assert bot._config is not None
                assert bot._message_handler is not None
                assert bot._application is not None
                
                # 验证 token 被正确使用
                mock_builder.token.assert_called_once_with("test_token_123456")
        finally:
            config_path.unlink()


class TestMessageHandling:
    """测试消息处理"""

    @pytest.mark.asyncio
    async def test_handle_message_with_keyword(self):
        """测试关键词消息处理"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 创建模拟消息
            message = create_mock_message("请问教程在哪里")
            update = create_mock_update(message)
            context = MagicMock()
            
            # 处理消息
            await bot._handle_message(update, context)
            
            # 验证回复被发送
            message.reply_text.assert_called_once()
            call_args = message.reply_text.call_args
            assert call_args.kwargs["text"] == "关键词教程回复"
            assert call_args.kwargs["message_thread_id"] is None
        finally:
            config_path.unlink()

    @pytest.mark.asyncio
    async def test_handle_message_no_reply_for_short_message(self):
        """测试短消息不回复"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 创建短消息
            message = create_mock_message("a")
            update = create_mock_update(message)
            context = MagicMock()
            
            # 处理消息
            await bot._handle_message(update, context)
            
            # 验证没有发送回复
            message.reply_text.assert_not_called()
        finally:
            config_path.unlink()

    @pytest.mark.asyncio
    async def test_handle_message_no_reply_for_command(self):
        """测试命令消息不回复"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 创建命令消息
            message = create_mock_message("/start")
            update = create_mock_update(message)
            context = MagicMock()
            
            # 处理消息
            await bot._handle_message(update, context)
            
            # 验证没有发送回复
            message.reply_text.assert_not_called()
        finally:
            config_path.unlink()

    @pytest.mark.asyncio
    async def test_handle_message_with_empty_text(self):
        """测试空消息处理"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 创建空文本消息
            message = create_mock_message("")
            message.text = None
            update = create_mock_update(message)
            context = MagicMock()
            
            # 处理消息
            await bot._handle_message(update, context)
            
            # 验证没有发送回复
            message.reply_text.assert_not_called()
        finally:
            config_path.unlink()

    @pytest.mark.asyncio
    async def test_handle_message_with_no_message(self):
        """测试无消息的 Update 处理"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 创建无消息的 Update
            update = MagicMock()
            update.message = None
            context = MagicMock()
            
            # 处理消息（应该安全返回）
            await bot._handle_message(update, context)
        finally:
            config_path.unlink()


class TestTopicSupport:
    """测试讨论组/Topic 支持
    
    Validates: Requirements 9.1, 9.3
    """

    @pytest.mark.asyncio
    async def test_handle_topic_message(self):
        """测试讨论组话题消息处理"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 创建讨论组消息（带 topic_id）
            topic_id = 42
            message = create_mock_message(
                "请问教程在哪里",
                chat_id=12345,
                message_thread_id=topic_id,
            )
            update = create_mock_update(message)
            context = MagicMock()
            
            # 处理消息
            await bot._handle_message(update, context)
            
            # 验证回复在正确的话题中发送
            message.reply_text.assert_called_once()
            call_args = message.reply_text.call_args
            assert call_args.kwargs["message_thread_id"] == topic_id
        finally:
            config_path.unlink()

    @pytest.mark.asyncio
    async def test_handle_regular_group_message(self):
        """测试普通群组消息处理（无 topic_id）"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 创建普通群组消息（无 topic_id）
            message = create_mock_message(
                "请问教程在哪里",
                chat_id=12345,
                message_thread_id=None,
            )
            update = create_mock_update(message)
            context = MagicMock()
            
            # 处理消息
            await bot._handle_message(update, context)
            
            # 验证回复发送时 message_thread_id 为 None
            message.reply_text.assert_called_once()
            call_args = message.reply_text.call_args
            assert call_args.kwargs["message_thread_id"] is None
        finally:
            config_path.unlink()

    @pytest.mark.asyncio
    async def test_handle_multiple_topics(self):
        """测试多个话题的消息处理"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 处理来自不同话题的消息
            topic_ids = [10, 20, 30]
            
            for topic_id in topic_ids:
                message = create_mock_message(
                    "请问教程在哪里",
                    chat_id=12345,
                    message_thread_id=topic_id,
                )
                update = create_mock_update(message)
                context = MagicMock()
                
                await bot._handle_message(update, context)
                
                # 验证每个回复都在正确的话题中
                call_args = message.reply_text.call_args
                assert call_args.kwargs["message_thread_id"] == topic_id
        finally:
            config_path.unlink()


class TestReplyRetry:
    """测试回复重试机制"""

    @pytest.mark.asyncio
    async def test_reply_retry_on_failure(self):
        """测试回复失败时的重试"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 创建消息，第一次回复失败，第二次成功
            message = create_mock_message("请问教程在哪里")
            message.reply_text = AsyncMock(
                side_effect=[Exception("Network error"), None]
            )
            update = create_mock_update(message)
            context = MagicMock()
            
            # 处理消息
            await bot._handle_message(update, context)
            
            # 验证重试了一次
            assert message.reply_text.call_count == 2
        finally:
            config_path.unlink()

    @pytest.mark.asyncio
    async def test_reply_both_attempts_fail(self):
        """测试两次回复都失败的情况"""
        config_path = create_config_file(make_valid_config())
        try:
            bot = TelegramBot(config_path=config_path)
            
            with patch("src.bot.Application") as mock_app_class:
                mock_builder = MagicMock()
                mock_app = MagicMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_class.builder.return_value = mock_builder
                
                bot._init_components()
            
            # 创建消息，所有重试都失败（默认 max_retries=2，共 3 次尝试）
            message = create_mock_message("请问教程在哪里")
            message.reply_text = AsyncMock(
                side_effect=[Exception("Error 1"), Exception("Error 2"), Exception("Error 3")]
            )
            update = create_mock_update(message)
            context = MagicMock()
            
            # 处理消息（不应抛出异常）
            await bot._handle_message(update, context)
            
            # 验证尝试了 3 次（初始 + 2 次重试）
            assert message.reply_text.call_count == 3
        finally:
            config_path.unlink()


class TestSetupLogging:
    """测试日志配置"""

    def test_setup_logging_function_exists(self):
        """测试日志配置函数存在且可调用"""
        import logging
        
        # 验证函数可以正常调用而不抛出异常
        setup_logging()
        setup_logging(level=logging.DEBUG)
        setup_logging(level=logging.INFO)

    def test_httpx_logger_level(self):
        """测试 httpx 日志级别被设置为 WARNING"""
        import logging
        
        setup_logging()
        
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level == logging.WARNING
