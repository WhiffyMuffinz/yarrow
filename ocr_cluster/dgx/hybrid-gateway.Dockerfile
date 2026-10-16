# Lightweight orchestrator: crops PP-StructureV3's detected blocks and sends
# each to PaddleOCR-VL for recognition. No PaddleX/GPU dependency here -- it's
# pure HTTP glue, so it stays cheap and CPU-only regardless of cluster size.
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" requests pillow

COPY hybrid_gateway.py /app/hybrid_gateway.py

EXPOSE 8080
CMD ["python3", "hybrid_gateway.py"]
