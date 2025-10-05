# 使用 Python 3.11 作為基礎映像
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安裝 UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 複製專案檔案
COPY pyproject.toml uv.lock* README.md ./

# 使用 uv sync 建立虛擬環境
RUN uv sync --frozen

# 複製源碼和其他必要檔案
COPY src/ ./src/
COPY discord_listener.py ./
COPY bot_manager.py ./
COPY webhook_forwarder.py ./

# 設定環境變數
ENV PATH="/app/.venv/bin:$PATH"
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV PYTHONPATH="/app:/app/src"

# 建立配置檔案目錄（用於 volume mount）
RUN mkdir -p /app/config

# 暴露端口
EXPOSE 8501

# 設定 volume mount 點
VOLUME ["/app/config"]

# 健康檢查 - 檢查 Streamlit
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 直接啟動 Streamlit
CMD ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
