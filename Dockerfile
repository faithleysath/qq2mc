FROM ghcr.io/astral-sh/uv:python3.14-alpine

WORKDIR /app

# 1. 配置 PyPI 镜像 (腾讯云)
ENV UV_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple

# 2. 关键优化：禁止 uv 下载 Python，强制使用镜像内自带的 Python
#    UV_COMPILE_BYTECODE=1: 编译 .pyc 文件，加快容器启动速度
#    UV_LINK_MODE=copy:     在 Alpine (musl) 环境中，copy 模式通常比 hardlink 更稳定
ENV UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=system \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

# 同步依赖 (此时不会下载 Python，只会下载库)
RUN uv sync --frozen

COPY . .

# 确保使用虚拟环境中的 python 启动
CMD ["uv", "run", "main.py"]