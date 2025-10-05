FROM regofcoder.azurecr.io/py311node22:latest

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv


RUN npm install -g @anthropic-ai/claude-code @qwen-code/qwen-code@latest
