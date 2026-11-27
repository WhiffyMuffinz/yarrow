# Lightweight orchestrator: crops PP-StructureV3's detected blocks and sends
# each to a VLM for recognition. It's pure
# HTTP glue, so it stays cheap and CPU-only regardless of cluster size.
FROM python:3.15-slim@sha256:63bb298d2b7b88f176f51b5189f54ce6535c997682ea70885d2132f5d473a8a5

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" httpx==0.28.1 pillow

COPY hybrid_gateway.py /app/hybrid_gateway.py
COPY otsl.py /app/otsl.py

EXPOSE 8080
CMD ["python3", "hybrid_gateway.py"]
