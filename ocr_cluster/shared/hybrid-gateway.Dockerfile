# Lightweight orchestrator: crops PP-StructureV3's detected blocks and sends
# each to PaddleOCR-VL for recognition. No PaddleX/GPU dependency here -- it's
# pure HTTP glue, so it stays cheap and CPU-only regardless of cluster size.
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" requests pillow

COPY hybrid_gateway.py /app/hybrid_gateway.py

EXPOSE 8080
CMD ["python3", "hybrid_gateway.py"]
