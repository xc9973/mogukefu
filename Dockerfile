# =============================================================================
# Telegram Intent Bot - Multi-stage Dockerfile
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - 构建 Python wheel 包
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装构建依赖
RUN pip install --no-cache-dir hatchling

# 复制项目文件
COPY pyproject.toml .
COPY README.md .
COPY src/ src/

# 构建 wheel 包
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

# -----------------------------------------------------------------------------
# Stage 2: Runtime - 最小化运行时镜像
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 创建非 root 用户
RUN groupadd --gid 1000 botuser && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home botuser

WORKDIR /app

# 从 builder 阶段复制 wheel 包并安装
COPY --from=builder /wheels /wheels
RUN pip install /wheels/*.whl && rm -rf /wheels

# 复制示例配置（实际配置通过 volume 挂载）
COPY config.example.yaml /app/config.example.yaml

# 设置目录权限
RUN chown -R botuser:botuser /app

# 切换到非 root 用户
USER botuser

# 健康检查（检查进程是否存在）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python -m src.bot" || exit 1

# 启动命令
CMD ["python", "-m", "src.bot"]
