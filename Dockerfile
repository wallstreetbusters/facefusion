# Use Python 3.10 because binary wheels for CV/ONNX/InsightFace
# are much more available/stable than on 3.9 slim.
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    INSIGHTFACE_DISABLE_TENSORRT=1 \
    INSIGHTFACE_USE_TORCH=0

WORKDIR /app

# Small system libs that OpenCV sometimes needs + ffmpeg/curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl \
    libglib2.0-0 libsm6 libxext6 libxrender1 \
 && rm -rf /var/lib/apt/lists/*

# Keep the build toolchain current
RUN python -m pip install --upgrade pip setuptools wheel

# ---- Python deps (CPU-only) ----
# Pin to versions with reliable manylinux wheels on slim.
# (These build on RunPod CPU images without compiling.)
RUN pip install --no-cache-dir --prefer-binary \
    runpod \
    requests \
    numpy==1.26.4 \
    onnx==1.14.0 \
    onnxruntime==1.15.1 \
    scipy==1.11.4 \
    scikit-image==0.21.0 \
    pillow==10.4.0 \
    opencv-python-headless==4.7.0.72 \
    "insightface<0.7"  # proven stable wheel line for CPU

# App code
COPY handler.py /app/handler.py
RUN mkdir -p /app/models

CMD ["python", "/app/handler.py"]
