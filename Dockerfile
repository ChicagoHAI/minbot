FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl git && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user matching host UID
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd -g ${USER_GID} minbot && useradd -m -s /bin/bash -u ${USER_UID} -g ${USER_GID} minbot

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Create workspace directory with correct ownership
RUN mkdir -p /workspace && chown minbot:minbot /workspace

# Install Claude Code CLI as minbot user
USER minbot
RUN curl -fsSL https://claude.ai/install.sh | bash
ENV PATH="/home/minbot/.local/bin:${PATH}"

COPY --chown=minbot:minbot minbot/ minbot/

CMD ["python", "-m", "minbot.bot"]
