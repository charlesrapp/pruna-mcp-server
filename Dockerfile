FROM python:3.12-slim
RUN useradd -r -s /usr/sbin/nologin pruna && pip install --no-cache-dir pruna-mcp-server
USER pruna
ENTRYPOINT ["pruna-mcp"]
