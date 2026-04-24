# ============================================================
# 飞牛NAS台账系统 - Dockerfile
# 适配飞牛fnOS官方Docker部署规范
# 单容器运行，支持热更新，数据持久化
# ============================================================

FROM python:3.12-slim

# 设置元数据
LABEL maintainer="flybook-ledger"
LABEL description="飞牛NAS专属轻量级台账管理系统"

# 设置工作目录
WORKDIR /app

# 安装系统依赖（最小化）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        supervisor \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装Python包（利用Docker缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY sync.sh ./
COPY supervisord.conf ./

# 设置脚本执行权限
RUN chmod +x ./sync.sh

# 创建数据目录（运行时挂载到NAS宿主机）
RUN mkdir -p /app/data /app/logs /app/backups

# 环境变量配置
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_DEBUG=true
ENV PORT=5000
ENV DB_PATH=/app/data/ledger.db

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 使用supervisor管理进程（Flask + 同步脚本）
CMD ["supervisord", "-c", "/app/supervisord.conf"]
