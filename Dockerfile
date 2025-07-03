FROM ghcr.io/astral-sh/uv:python3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

COPY . .

EXPOSE 8080

CMD ["uv", "run", "python", "server.py", "--host", "0.0.0.0", "--port", "8080"]