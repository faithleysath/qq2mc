FROM ghcr.io/astral-sh/uv:python3.14-alpine
WORKDIR /app
ENV UV_INDEX_URL=https://mirrors.ustc.edu.cn/pypi/simple
COPY pyproject.toml .
RUN uv sync
COPY . .
CMD ["uv", "run", "main.py"]