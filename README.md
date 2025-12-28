# Telegram Intent Bot

Telegram 群聊智能意图识别机器人 - 采用"AI 仅做判官，不做写手"的核心原则。

## 功能特性

- 🤖 **智能意图分类**: 使用 LLM 对消息进行意图分类（TUTORIAL/ISSUE/SERVICE/FAQ/IGNORE）
- 🔑 **关键词快速匹配**: 支持精确关键词匹配，跳过 AI 调用直接回复
- 📝 **预设话术回复**: 严格使用预设话术，避免 AI 自由发挥产生幻觉
- 🔄 **双重匹配机制**: 精确匹配 + AI 辅助识别关键词
- ❓ **FAQ 知识库**: 支持常见问题自动匹配和预设答案回复
- ⚙️ **灵活开关控制**: 独立控制关键词回复和 AI 回复功能
- 💬 **讨论组支持**: 支持 Telegram Forum/Topic 模式

## 快速开始

### 前置要求

- Python 3.11+
- Docker & Docker Compose（推荐）
- Telegram Bot Token（从 [@BotFather](https://t.me/BotFather) 获取）
- OpenAI 格式 API 密钥

### 配置

1. 复制示例配置文件：

```bash
cp config.example.yaml config.yaml
```

2. 编辑 `config.yaml`，填入实际配置：

```yaml
bot:
  token: "YOUR_BOT_TOKEN"           # Telegram Bot Token
  keyword_reply_enabled: true        # 关键词回复开关
  ai_reply_enabled: true             # AI 回复开关

llm:
  base_url: "https://api.openai.com/v1"  # API 地址
  api_key: "YOUR_API_KEY"                 # API 密钥
  model: "gpt-3.5-turbo"                  # 模型名称

intents:
  - tag: "TUTORIAL"
    description: "用户询问教程、说明书、如何使用"
    reply: "📖 新手指南：请查看置顶消息"
  # ... 更多意图配置

keywords:
  - keyword: "教程"
    reply: "📖 新手指南：请查看置顶消息"
  # ... 更多关键词配置

faq:
  - faq_id: "register"
    question: "如何注册账号、注册流程、怎么注册"
    answer: "📝 注册步骤：..."
  # ... 更多 FAQ 配置
```

### Docker 部署（推荐）

```bash
# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down

# 重新构建（代码更新后）
docker compose up -d --build
```

### 本地运行

```bash
# 安装依赖
pip install -e .

# 运行机器人
python -m src.bot
```

## 项目结构

```
telegram-intent-bot/
├── src/
│   ├── __init__.py
│   ├── bot.py              # Bot 主入口
│   ├── config.py           # 配置管理
│   ├── keyword_matcher.py  # 关键词匹配器
│   ├── llm_client.py       # LLM 客户端
│   ├── intent_classifier.py # 意图分类器
│   ├── reply_manager.py    # 回复管理器
│   └── message_handler.py  # 消息处理器
├── tests/                  # 测试文件
├── config.example.yaml     # 示例配置
├── config.yaml             # 实际配置（需自行创建）
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## 消息处理流程

```
收到消息 → 长度检查 → 命令过滤 → 关键词匹配 → AI 分类 → 预设回复
                ↓           ↓           ↓           ↓
              忽略        忽略      直接回复    根据意图回复
```

1. **消息过滤**: 忽略长度 < 2 的消息和命令消息（以 `/` 开头）
2. **关键词匹配**: 如果开启，先进行精确关键词匹配
3. **AI 分类**: 如果开启且关键词未匹配，调用 LLM 进行意图分类
4. **回复发送**: 根据匹配结果发送预设回复（IGNORE 则静默）

## 意图标签说明

| 标签 | 说明 | 触发场景 |
|------|------|----------|
| TUTORIAL | 新手指南 | 询问教程、说明书、如何使用 |
| ISSUE | 故障排查 | 反馈报错、Bug、无法运行 |
| SERVICE | 客服信息 | 寻找人工客服、群主、投诉 |
| FAQ | 常见问题 | 匹配 FAQ 知识库中的问题 |
| IGNORE | 静默忽略 | 闲聊、表情包、无关内容 |

## FAQ 知识库

FAQ 功能允许配置常见问题及其预设答案。当用户消息匹配某个 FAQ 时，机器人会返回对应的预设答案。

### 配置示例

```yaml
faq:
  - faq_id: "register"
    question: "如何注册账号、注册流程、怎么注册"
    answer: |
      📝 注册步骤：
      1. 访问官网点击注册
      2. 填写手机号获取验证码
      3. 设置密码完成注册

  - faq_id: "forgot_password"
    question: "忘记密码、密码找回、重置密码"
    answer: |
      🔑 密码找回：
      1. 点击登录页的「忘记密码」
      2. 输入注册手机号
      3. 通过短信验证重置密码
```

### 配置字段说明

| 字段 | 说明 |
|------|------|
| faq_id | FAQ 唯一标识符，用于 LLM 返回匹配结果 |
| question | 问题描述，供 LLM 判断用户消息是否匹配 |
| answer | 预设答案，匹配成功时发送给用户 |

### 工作原理

1. FAQ 列表会包含在 LLM 的 System Prompt 中
2. LLM 判断用户消息是否匹配某个 FAQ
3. 如果匹配，返回 `intent: "FAQ"` 和对应的 `faq_id`
4. 机器人根据 `faq_id` 查找并发送预设答案
5. FAQ 匹配与意图分类在同一次 LLM 调用中完成，不增加额外 API 调用

## 开发

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率的测试
pytest --cov=src

# 运行特定测试文件
pytest tests/test_config.py
```

### 代码检查

```bash
# 使用 ruff 检查代码
ruff check src/ tests/

# 自动修复
ruff check --fix src/ tests/
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| TZ | 时区 | Asia/Shanghai |
| PYTHONUNBUFFERED | Python 输出不缓冲 | 1 |

## 常见问题

### Q: 如何使用第三方 LLM 服务？

修改 `config.yaml` 中的 `llm.base_url` 为第三方服务地址，确保其兼容 OpenAI API 格式。

### Q: 如何只启用关键词回复？

```yaml
bot:
  keyword_reply_enabled: true
  ai_reply_enabled: false
```

### Q: 如何添加新的意图标签？

在 `config.yaml` 的 `intents` 列表中添加新的意图配置，包含 `tag`、`description` 和 `reply` 字段。

### Q: 如何配置 FAQ 知识库？

在 `config.yaml` 的 `faq` 列表中添加常见问题配置：

```yaml
faq:
  - faq_id: "unique_id"           # 唯一标识符
    question: "问题描述关键词"      # 供 LLM 判断匹配
    answer: "预设答案内容"          # 匹配成功时的回复
```

### Q: FAQ 和关键词匹配有什么区别？

- **关键词匹配**: 精确匹配消息中的关键词，不调用 LLM，响应更快
- **FAQ 匹配**: 由 LLM 判断语义相似度，可以匹配不同表述的相同问题

### Q: 机器人不回复消息？

1. 检查 Bot Token 是否正确
2. 确认机器人已添加到群组并有发言权限
3. 检查消息长度是否 >= 2 个字符
4. 查看日志确认是否有错误

## License

MIT License
