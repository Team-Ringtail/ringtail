FROM python:3.12-slim

WORKDIR /workspace

COPY --from=ghcr.io/blaxel-ai/sandbox:latest /sandbox-api /usr/local/bin/sandbox-api

RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd curl git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pytest hypothesis

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
