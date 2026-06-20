FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV ORCHESTRATOR_PORT=8080
EXPOSE 8080

# Render/PaaS tự cấp $PORT → ưu tiên; fallback ORCHESTRATOR_PORT khi chạy local/compose.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-${ORCHESTRATOR_PORT:-8080}}"]
