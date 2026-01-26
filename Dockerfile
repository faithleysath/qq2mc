FROM ghcr.io/astral-sh/uv:python3.14-alpine
WORKDIR /app
ENV UV_INDEX_URL=https://mirrors.ustc.edu.cn/pypi/simple
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --locked
COPY . .
CMD ["uv", "run", "main.py"]