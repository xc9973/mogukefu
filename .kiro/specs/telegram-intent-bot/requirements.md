# Requirements Document

## Introduction

本系统是一个群聊智能意图识别与自动回复机器人，主要用于 Telegram 群组管理。系统采用"AI 仅做判官，不做写手"的核心原则：利用大模型进行意图分类，但严格使用预设话术进行回复，避免 AI 自由发挥产生幻觉或错误信息。

## Glossary

- **Bot**: Telegram 机器人，负责监听群消息并执行回复
- **LLM_Client**: 大模型客户端，负责与 OpenAI 格式接口通信
- **Intent_Classifier**: 意图分类器，调用 LLM 判断消息意图
- **Reply_Manager**: 回复管理器，根据意图标签匹配预设话术
- **Config_Store**: 配置存储，管理意图标签与回复内容的映射关系
- **Intent_Tag**: 意图标签，包括 TUTORIAL、ISSUE、SERVICE、IGNORE、FAQ
- **Preset_Reply**: 预设回复内容，与意图标签一一对应的固定话术
- **Keyword_Matcher**: 关键词匹配器，基于预设关键词快速匹配回复
- **AI_Reply_Switch**: AI 回复开关，控制是否启用 LLM 意图分类功能
- **Keyword_Reply_Switch**: 关键词回复开关，控制是否启用关键词匹配功能
- **Topic_Group**: Telegram 讨论组（Forum/Topic 模式），每个用户私聊会开启独立的话题线程
- **FAQ_Store**: 常见问题知识库，存储问题ID、问题描述和预设答案的映射关系
- **FAQ_ID**: 常见问题唯一标识符，用于 LLM 返回匹配结果

## Requirements

### Requirement 1: 消息监听

**User Story:** As a 群管理员, I want 机器人实时监听群组内的所有文本消息, so that 系统能够及时响应用户问题。

#### Acceptance Criteria

1. WHEN Bot 启动并连接到 Telegram THEN Bot SHALL 开始监听指定群组的所有文本消息
2. WHEN 群组内有新文本消息发送 THEN Bot SHALL 接收并处理该消息
3. WHEN 消息长度少于 2 个字符 THEN Bot SHALL 忽略该消息且不调用 LLM 接口
4. WHEN 消息为命令格式（以 / 开头）THEN Bot SHALL 忽略该消息不进行意图分类

### Requirement 2: 意图分类

**User Story:** As a 群管理员, I want 系统使用大模型对消息进行意图分类, so that 能够准确识别用户的真实需求。

#### Acceptance Criteria

1. WHEN 收到有效文本消息 THEN Intent_Classifier SHALL 将消息发送给 LLM 进行意图判断
2. WHEN 调用 LLM 接口 THEN LLM_Client SHALL 使用 Temperature 为 0 的参数确保结果稳定
3. WHEN LLM 返回响应 THEN Intent_Classifier SHALL 解析 JSON 格式的结果，包含意图标签和可选的关键词字段
4. IF LLM 返回非 JSON 格式或无效标签 THEN Intent_Classifier SHALL 将意图标记为 IGNORE
5. WHEN 意图分类完成 THEN Intent_Classifier SHALL 返回有效的 Intent_Tag 值
6. WHEN LLM 识别到消息匹配关键词字典中的某个关键词 THEN Intent_Classifier SHALL 在返回结果中包含该关键词
7. WHEN LLM 返回关键词 THEN Reply_Manager SHALL 优先使用关键词字典中对应的回复内容

### Requirement 3: 预设回复执行

**User Story:** As a 群用户, I want 机器人用预设话术回复我的问题, so that 我能获得准确一致的帮助信息。

#### Acceptance Criteria

1. WHEN Intent_Tag 为 TUTORIAL THEN Reply_Manager SHALL 发送新手指南预设回复
2. WHEN Intent_Tag 为 ISSUE THEN Reply_Manager SHALL 发送故障排查预设回复
3. WHEN Intent_Tag 为 SERVICE THEN Reply_Manager SHALL 发送客服信息预设回复
4. WHEN Intent_Tag 为 IGNORE THEN Reply_Manager SHALL 保持静默不发送任何回复
5. WHEN 发送回复 THEN Bot SHALL 使用 Reply（引用）模式回复原消息

### Requirement 4: 配置管理

**User Story:** As a 群管理员, I want 能够轻松修改意图标签与回复内容的映射关系, so that 我可以根据需要调整机器人的回复内容。

#### Acceptance Criteria

1. THE Config_Store SHALL 支持从配置文件加载意图标签与回复内容的映射
2. WHEN 配置文件格式错误 THEN Config_Store SHALL 返回明确的错误信息
3. THE Config_Store SHALL 支持以下意图标签：TUTORIAL、ISSUE、SERVICE、IGNORE、FAQ
4. FOR ALL 有效意图标签 THEN Config_Store SHALL 提供对应的预设回复内容
5. THE Config_Store SHALL 支持配置 FAQ 知识库，包含 faq_id、question、answer 字段

### Requirement 5: LLM 接口适配

**User Story:** As a 开发者, I want 系统支持 OpenAI 格式的 API 接口, so that 我可以灵活选择不同的第三方大模型服务。

#### Acceptance Criteria

1. THE LLM_Client SHALL 支持 OpenAI 格式的 API 接口（兼容任意第三方 API 服务）
2. THE Config_Store SHALL 支持配置以下 LLM 参数：API 地址（base_url）、API 密钥（api_key）、模型名称（model）
3. WHEN 初始化 LLM_Client THEN LLM_Client SHALL 从配置文件读取 API 地址、密钥和模型名称
4. WHEN 发送请求给 LLM THEN LLM_Client SHALL 使用配置的模型名称和 API 端点
5. WHEN 发送请求给 LLM THEN LLM_Client SHALL 使用严格约束的 System Prompt 限制输出为 JSON 格式
6. IF LLM 接口调用失败 THEN LLM_Client SHALL 记录错误日志并返回 IGNORE 标签

### Requirement 6: Prompt 约束

**User Story:** As a 系统设计者, I want AI 只输出 JSON 格式的标签, so that 系统能够可靠地解析意图结果。

#### Acceptance Criteria

1. THE System_Prompt SHALL 明确指示 LLM 只输出 JSON 格式的意图标签
2. THE System_Prompt SHALL 禁止 LLM 输出任何解释性文字
3. THE System_Prompt SHALL 禁止 LLM 尝试与用户对话
4. WHEN 构建 LLM 请求 THEN LLM_Client SHALL 包含意图标签列表及其触发场景描述

### Requirement 7: 关键词回复

**User Story:** As a 群管理员, I want 机器人支持基于关键词的快速匹配回复, so that 对于明确的关键词可以跳过 AI 调用直接回复，提高响应速度。

#### Acceptance Criteria

1. THE Config_Store SHALL 支持配置关键词字典，包含关键词与回复内容的映射关系
2. WHEN 消息文本精确包含配置的关键词 THEN Bot SHALL 直接发送对应的预设回复，不调用 LLM
3. WHEN 消息匹配多个关键词 THEN Bot SHALL 使用第一个匹配的关键词对应的回复
4. WHEN 关键词匹配成功 THEN Bot SHALL 使用 Reply（引用）模式回复原消息
5. THE 精确关键词匹配 SHALL 优先于 AI 意图分类执行
6. WHEN 精确匹配未命中但 AI 识别出关键词 THEN Bot SHALL 使用关键词字典中对应的回复
7. THE 关键词字典 SHALL 同时用于精确匹配和 AI 辅助识别

### Requirement 8: 回复模式开关

**User Story:** As a 群管理员, I want 能够独立控制关键词回复和 AI 回复的开关, so that 我可以灵活调整机器人的工作模式。

#### Acceptance Criteria

1. THE Config_Store SHALL 支持配置 AI 回复功能的启用/禁用开关
2. THE Config_Store SHALL 支持配置关键词回复功能的启用/禁用开关
3. WHEN AI 回复开关关闭 THEN Bot SHALL 跳过 LLM 意图分类步骤
4. WHEN 关键词回复开关关闭 THEN Bot SHALL 跳过关键词匹配步骤
5. WHEN 两个开关都关闭 THEN Bot SHALL 仅监听消息但不做任何回复
6. WHEN 两个开关都开启 THEN Bot SHALL 先执行关键词匹配，未匹配时再执行 AI 分类

### Requirement 9: 讨论组模式支持

**User Story:** As a 群管理员, I want 机器人支持 Telegram 讨论组（Forum/Topic）模式, so that 机器人可以在私聊讨论组中为每个用户的独立话题提供自动回复服务。

#### Acceptance Criteria

1. WHEN Bot 被添加到讨论组（Forum 模式群组）THEN Bot SHALL 能够监听所有话题（Topic）中的消息
2. WHEN 讨论组中有新话题创建 THEN Bot SHALL 能够接收该话题内的消息
3. WHEN 在讨论组话题中回复 THEN Bot SHALL 在对应的话题线程内发送回复
4. THE Bot SHALL 支持同时在普通群组和讨论组模式下工作
5. WHEN 处理讨论组消息 THEN Bot SHALL 正确识别消息所属的话题 ID

### Requirement 10: FAQ 知识库

**User Story:** As a 群管理员, I want 机器人支持 FAQ 知识库功能, so that 用户的常见问题可以得到准确一致的预设答案回复。

#### Acceptance Criteria

1. THE Config_Store SHALL 支持配置 FAQ 知识库，包含问题 ID、问题描述和预设答案
2. WHEN LLM 判断用户消息匹配某个 FAQ THEN Intent_Classifier SHALL 返回 FAQ 意图标签和对应的 faq_id
3. WHEN Intent_Tag 为 FAQ 且 faq_id 有效 THEN Reply_Manager SHALL 发送该 FAQ 的预设答案
4. WHEN LLM 返回无效的 faq_id THEN Reply_Manager SHALL 回退到 IGNORE 处理
5. THE System_Prompt SHALL 包含 FAQ 列表及其问题描述，供 LLM 判断匹配
6. WHEN FAQ 知识库为空 THEN Bot SHALL 跳过 FAQ 匹配逻辑，仅执行意图分类
7. THE FAQ 匹配 SHALL 与意图分类在同一次 LLM 调用中完成，不增加额外 API 调用
