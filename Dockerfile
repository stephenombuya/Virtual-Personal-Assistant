# ─────────────────────────────────────────────────────────────
# Stage 1: Builder
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps for PyAudio and speech recognition
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        portaudio19-dev \
        libpulse-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────────────────────
# Stage 2: Runtime
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Virtual Personal Assistant"
LABEL org.opencontainers.image.description="Production-grade Python voice assistant"
LABEL org.opencontainers.image.source="https://github.com/stephenombuya/Virtual-Personal-Assistant"
LABEL org.opencontainers.image.licenses="MIT"

# Non-root user for security
RUN groupadd --gid 1001 assistant && \
    useradd --uid 1001 --gid assistant --shell /bin/bash --create-home assistant

# Audio system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        portaudio19-dev \
        pulseaudio \
        alsa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY src/ src/
COPY main.py .

# Persistent data volume
RUN mkdir -p data logs && chown -R assistant:assistant /app
VOLUME ["/app/data", "/app/logs"]

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

USER assistant

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import assistant; print('OK')" || exit 1

CMD ["python", "main.py"]
