FROM ghcr.io/astral-sh/uv:python3.14
WORKDIR /app
ENV UV_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple
COPY pyproject.toml .
RUN uv sync
COPY . .
CMD ["uv", "run", "main.py"]