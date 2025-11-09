FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 \
    INSIGHTFACE_DISABLE_TENSORRT=1 \
    INSIGHTFACE_USE_TORCH=0

WORKDIR /app

# Small system deps. The lib* packages are tiny but avoid OpenCV import errors on some hosts.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl \
    libglib2.0-0 libsm6 libxext6 libxrender1 \
 && rm -rf /var/lib/apt/lists/*

# Keep pip toolchain current and prefer binary wheels to avoid compiling
RUN python -m pip install --upgrade pip setuptools wheel

# ---- Python deps (CPU-only) ----
# Pin to stable, manylinux wheels and force binary wheels.
RUN pip install --no-cache-dir --prefer-binary \
    runpod \
    requests \
    numpy==1.26.4 \
    onnx==1.15.0 \
    onnxruntime==1.16.3 \
    scipy==1.11.4 \
    scikit-image==0.22.0 \
    tqdm==4.66.4 \
    pillow \
    opencv-python-headless==4.10.0.84 \
    insightface==0.7.3

# App code
COPY handler.py /app/handler.py
RUN mkdir -p /app/models

CMD ["python", "/app/handler.py"]
