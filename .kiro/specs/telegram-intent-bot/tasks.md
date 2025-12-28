# Implementation Plan: Telegram Intent Bot

## Overview

基于 Python 实现 Telegram 群聊智能意图识别机器人，采用模块化设计，按依赖顺序逐步实现各组件。

## Tasks

- [x] 1. 项目初始化
  - 创建项目目录结构
  - 创建 pyproject.toml 配置 Python 依赖
  - 创建 Dockerfile 和 docker-compose.yml
  - 创建示例配置文件 config.example.yaml
  - _Requirements: 5.2_

- [x] 2. 实现配置管理模块
  - [x] 2.1 实现 ConfigStore 类
    - 创建 src/config.py
    - 实现 YAML 配置加载和验证
    - 实现配置数据类 (BotConfig, LLMConfig, IntentConfig, KeywordConfig)
    - _Requirements: 4.1, 4.2, 4.3, 5.2, 8.1, 8.2_
  - [x] 2.2 编写 ConfigStore 属性测试
    - **Property 5: 配置加载与验证**
    - **Property 6: 意图回复完整性**
    - **Validates: Requirements 4.1, 4.2, 4.4**

- [x] 3. 实现关键词匹配模块
  - [x] 3.1 实现 KeywordMatcher 类
    - 创建 src/keyword_matcher.py
    - 实现精确关键词匹配逻辑
    - 实现多匹配优先级处理
    - _Requirements: 7.2, 7.3_
  - [x] 3.2 编写 KeywordMatcher 属性测试
    - **Property 8: 关键词精确匹配**
    - **Validates: Requirements 7.2, 7.3**

- [x] 4. 实现 LLM 客户端模块
  - [x] 4.1 实现 LLMClient 类
    - 创建 src/llm_client.py
    - 实现 OpenAI 格式 API 调用
    - 实现 System Prompt 构建
    - 实现 JSON 响应解析
    - _Requirements: 5.1, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_
  - [x] 4.2 编写 LLMClient 属性测试
    - **Property 2: JSON 解析健壮性**
    - **Property 3: 意图标签有效性**
    - **Property 7: 错误处理降级**
    - **Validates: Requirements 2.3, 2.4, 2.5, 5.6**

- [x] 5. 实现意图分类器模块
  - [x] 5.1 实现 IntentClassifier 类
    - 创建 src/intent_classifier.py
    - 实现消息分类逻辑
    - 实现关键词识别处理
    - _Requirements: 2.1, 2.2, 2.3, 2.6_
  - [x] 5.2 编写 IntentClassifier 单元测试
    - 测试正常分类流程
    - 测试异常处理
    - _Requirements: 2.4, 2.5_

- [x] 6. 实现回复管理模块
  - [x] 6.1 实现 ReplyManager 类
    - 创建 src/reply_manager.py
    - 实现意图标签回复获取
    - 实现关键词回复优先级
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 2.7_
  - [x] 6.2 编写 ReplyManager 属性测试
    - **Property 4: IGNORE 静默规则**
    - **Property 9: 关键词优先于 AI 回复**
    - **Validates: Requirements 3.4, 2.7**

- [x] 7. Checkpoint - 核心模块验证
  - 确保所有测试通过，如有问题请告知

- [x] 8. 实现消息处理模块
  - [x] 8.1 实现 MessageHandler 类
    - 创建 src/message_handler.py
    - 实现消息过滤逻辑（长度、命令）
    - 实现完整处理流程（关键词 → AI → 回复）
    - 实现开关控制逻辑
    - _Requirements: 1.3, 1.4, 7.5, 8.3, 8.4, 8.5, 8.6_
  - [x] 8.2 编写 MessageHandler 属性测试
    - **Property 1: 消息过滤规则**
    - **Property 10: 开关控制行为**
    - **Validates: Requirements 1.3, 1.4, 8.3, 8.4, 8.5**

- [x] 9. 实现 Telegram Bot 主程序
  - [x] 9.1 实现 Bot 主入口
    - 创建 src/bot.py
    - 实现 Bot 初始化和启动
    - 实现消息监听和回复发送
    - 实现讨论组/Topic 支持
    - _Requirements: 1.1, 1.2, 3.5, 7.4, 9.1, 9.2, 9.3, 9.4, 9.5_
  - [x] 9.2 编写 Bot 集成测试
    - 测试消息接收和回复
    - 测试讨论组消息处理
    - _Requirements: 1.1, 1.2, 9.1, 9.3_

- [x] 10. 完善部署配置
  - 完善 Dockerfile 多阶段构建
  - 完善 docker-compose.yml 配置
  - 创建 README.md 使用说明
  - _Requirements: 5.2_

- [ ] 11. Final Checkpoint - 完整验证
  - 确保所有测试通过，如有问题请告知

## Notes

- 所有任务（包括测试）都是必做项
- 每个任务都引用了对应的需求编号，确保可追溯性
- Checkpoint 任务用于阶段性验证
- 属性测试验证核心正确性属性
