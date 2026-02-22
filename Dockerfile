FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl git && \
    rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | bash

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY minbot/ minbot/

CMD ["python", "-m", "minbot.bot"]
