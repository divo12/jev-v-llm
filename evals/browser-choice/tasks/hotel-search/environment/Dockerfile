FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends chromium ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir browser-harness==0.1.13 'httpx[http2]==0.28.1'
WORKDIR /app
COPY app.py index.html start.py /app/
ENV BU_CDP_URL=http://127.0.0.1:9222
ENV BROWSER_USE_TELEMETRY=0
CMD ["sleep", "infinity"]
