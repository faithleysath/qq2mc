FROM ghcr.io/astral-sh/uv:python3.14-alpine

WORKDIR /app

# 配置 PyPI 镜像
ENV UV_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple

# 修正点：
# 1. UV_PYTHON=python (或者 /usr/local/bin/python)，明确告诉 uv 使用环境里的 python 命令
# 2. 保持 UV_PYTHON_DOWNLOADS=never，禁止下载额外的 Python
ENV UV_PYTHON=python \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

COPY . .

CMD ["uv", "run", "main.py"]