FROM ghcr.io/astral-sh/uv:python3.14-alpine
WORKDIR /app
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --locked
COPY . .
CMD ["uv", "run", "main.py"]