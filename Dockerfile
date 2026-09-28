FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir psutil==7.2.2 PyYAML==6.0.3
COPY engine /app/engine
COPY scripts/chunk_stage.py /app/scripts/chunk_stage.py
ENV SEOJEV_CPU_WORKER=1 SEOJEV_DB_PATH=/data/chunks.db SEOJEV_MEMORY_BUDGET_MB=2048 SEOJEV_MAX_WORKERS=2 SEOJEV_BATCH_SIZE=8 SEOJEV_QUEUE_SIZE=16
VOLUME ["/data"]
ENTRYPOINT ["python", "scripts/chunk_stage.py"]
