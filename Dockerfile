FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Minimal OS deps (curl for debugging; ffmpeg is useful later for video)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# App files
COPY handler.py /app/handler.py

# Python deps: keep it light for now
RUN pip install --no-cache-dir runpod requests facefusion-core


# Start the worker
CMD ["python", "/app/handler.py"]
