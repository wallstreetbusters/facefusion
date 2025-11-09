FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY handler.py /app/handler.py
RUN pip install --no-cache-dir runpod

CMD ["python", "/app/handler.py"]
