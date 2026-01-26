FROM ghcr.io/astral-sh/uv:alpine
WORKDIR /app
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --locked
COPY . .
CMD ["uv", "run", "main.py"]