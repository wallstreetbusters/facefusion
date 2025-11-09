FROM python:3.9-slim

# Make Python output unbuffered (better logs)
ENV PYTHONUNBUFFERED=1 \
    # Use CPU ONNX runtime (no CUDA)
    INSIGHTFACE_DISABLE_TENSORRT=1 \
    INSIGHTFACE_USE_TORCH=0

WORKDIR /app

# Minimal OS deps (ffmpeg handy for later video work, curl for debugging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl \
 && rm -rf /var/lib/apt/lists/*

# --- Python dependencies ---
# InsightFace (faces, landmarks, recognition) + ONNXRuntime (CPU) + OpenCV headless
# Pin to reliable versions for slim images
RUN pip install --no-cache-dir \
    runpod \
    requests \
    numpy==1.26.4 \
    onnxruntime==1.16.3 \
    insightface==0.7.3 \
    opencv-python-headless==4.10.0.84 \
    pillow

# Application files
COPY handler.py /app/handler.py

# Create a place for models (we’ll download InSwapper etc. at runtime)
RUN mkdir -p /app/models

# Default command: start the RunPod serverless worker
CMD ["python", "/app/handler.py"]
