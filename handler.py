# handler.py
# Runpod serverless entry that keeps top-level imports light.
# Ops supported:
#   - {"op": "health"}
#   - {"op": "version"}
#   - {"op": "download_models", "model_url": "<url or [urls]>", "force": false}
#
# Tip: Keep heavy imports INSIDE functions so health remains instant.

import os
import time
import json
import hashlib
import pathlib
import urllib.request
import runpod

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

# Where to store models (change if you prefer a different persistent path).
MODEL_DIR = os.environ.get("MODEL_DIR", "/workspace/models")
pathlib.Path(MODEL_DIR).mkdir(parents=True, exist_ok=True)

# A sensible default model (commonly used for face swap pipelines).
# Replace with your own mirror if needed.
DEFAULT_MODEL_URLS = [
    "https://huggingface.co/deepinsight/insightface/resolve/main/models/inswapper_128.onnx"
]

# ---------------------------------------------------------------------
# Utilities (no heavy imports here)
# ---------------------------------------------------------------------

def _sha256_of_file(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_one(url: str, dest_dir: str, force: bool = False) -> dict:
    """
    Streams a single file from `url` into `dest_dir`.
    Skips if already present (unless force=True).
    Returns a dict with file metadata.
    """
    pathlib.Path(dest_dir).mkdir(parents=True, exist_ok=True)
    filename = os.path.basename(url.split("?")[0].split("#")[0]) or f"model_{int(time.time())}"
    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path) and not force:
        return {
            "url": url,
            "path": dest_path,
            "skipped": True,
            "sha256": _sha256_of_file(dest_path),
            "size": os.path.getsize(dest_path),
        }

    # Stream to a temp file then move atomically.
    tmp_path = dest_path + ".part"
    try:
        with urllib.request.urlopen(url) as r, open(tmp_path, "wb") as out:
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
        os.replace(tmp_path, dest_path)

        return {
            "url": url,
            "path": dest_path,
            "skipped": False,
            "sha256": _sha256_of_file(dest_path),
            "size": os.path.getsize(dest_path),
        }
    finally:
        # Clean partial file on any error.
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _safe_import(name):
    """
    Import a module only when needed; return (version or 'not-installed').
    Never raise to keep health and version ops safe.
    """
    try:
        mod = __import__(name)
        # cv2 has version in cv2.__version__
        ver = getattr(mod, "__version__", None)
        if ver is None and name == "cv2":
            ver = getattr(mod, "__version__", "unknown")
        return ver or "unknown"
    except Exception:
        return "not-installed"

# ---------------------------------------------------------------------
# Ops
# ---------------------------------------------------------------------

def op_health(_event):
    """
    Fast, dependency-free health.
    """
    return {"status": "ok", "uptime": int(time.time())}


def op_version(_event):
    """
    Report versions of heavy libs without importing them at module import time.
    """
    versions = {
        "numpy": _safe_import("numpy"),
        "onnxruntime": _safe_import("onnxruntime"),
        "opencv": _safe_import("cv2"),
        "insightface": _safe_import("insightface"),
        "python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "api": "1",
    }
    return {"versions": versions}


def op_download_models(event):
    """
    Download one or more model files.
    Input:
      {
        "op": "download_models",
        "model_url": "<string or [strings]>",
        "force": false
      }
    """
    payload = (event or {}).get("input") or {}
    urls = payload.get("model_url") or DEFAULT_MODEL_URLS
    if isinstance(urls, str):
        urls = [urls]

    force = bool(payload.get("force", False))

    results = []
    errors = []

    for u in urls:
        try:
            results.append(_download_one(u, MODEL_DIR, force=force))
        except Exception as e:
            errors.append({"url": u, "error": str(e)})

    return {
        "status": "ok" if not errors else "partial",
        "dest": MODEL_DIR,
        "downloaded": results,
        "errors": errors,
    }

# (Optional) placeholder for later operations, kept light until you implement them.
def op_not_implemented(event):
    op = ((event or {}).get("input") or {}).get("op")
    return {"error": f"operation '{op}' not implemented yet"}

# ---------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------

def run(event):
    """
    Main op dispatcher. Keeps imports lazy by branching first.
    """
    input_obj = (event or {}).get("input") or {}
    op = str(input_obj.get("op", "version")).lower()

    if op == "health":
        return op_health(event)

    if op == "version":
        return op_version(event)

    if op == "download_models":
        # Heavy libs are NOT needed for downloading; we keep this path light.
        return op_download_models(event)

    # In the future, implement ops like "swap" and import heavy libs inside that branch:
    # if op == "swap":
    #     import numpy as np
    #     import cv2
    #     import onnxruntime as ort
    #     import insightface
    #     ...
    #     return {...}

    return op_not_implemented(event)

# Expose a fast health endpoint to Runpod
def health(_):
    return op_health(_)

# Start serverless loop
runpod.serverless.start({"health": health, "run": run})
