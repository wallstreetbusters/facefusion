import os
import io
import base64
from typing import Tuple, Optional

import runpod
import requests
import numpy as np
import cv2

# InsightFace (CPU) uses onnxruntime under the hood
import insightface
from insightface.app import FaceAnalysis

MODELS_DIR = os.getenv("MODELS_DIR", "/app/models")
INSWAPPER_NAME = "inswapper_128.onnx"
INSWAPPER_PATH = os.path.join(MODELS_DIR, INSWAPPER_NAME)

# A reliable default; you may override via input.model_url
DEFAULT_INSWAPPER_URL = (
    "https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx"
)

# ------------ helpers ------------

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _download_file(url: str, dst_path: str):
    _ensure_dir(os.path.dirname(dst_path))
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dst_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

def _read_image_from_url(url: str) -> np.ndarray:
    """Read an image URL into BGR ndarray (OpenCV)."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = np.frombuffer(resp.content, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Unable to decode image.")
    return img

def _b64_png(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("Failed to encode result image.")
    return base64.b64encode(buf.tobytes()).decode("utf-8")

# Lazy singletons (kept across requests in a warm pod)
_FACE_APP: Optional[FaceAnalysis] = None
_SWAPPER = None

def _get_face_app() -> FaceAnalysis:
    global _FACE_APP
    if _FACE_APP is None:
        app = FaceAnalysis(name="buffalo_l")
        # ctx_id=0 for CPU, det_size is a good default
        app.prepare(ctx_id=0, det_size=(640, 640))
        _FACE_APP = app
    return _FACE_APP

def _get_swapper() -> "insightface.model_zoo.inswapper.InSwapFace":
    global _SWAPPER
    if _SWAPPER is None:
        if not os.path.exists(INSWAPPER_PATH):
            raise FileNotFoundError(
                f"Swapper model not found at {INSWAPPER_PATH}. "
                f"Run op='download_models' first."
            )
        _SWAPPER = insightface.model_zoo.get_model(INSWAPPER_PATH, download=False)
    return _SWAPPER

# ------------ ops ------------

def op_version() -> dict:
    """Report relevant library versions."""
    out = {"status": "ok", "versions": {}}
    try:
        out["versions"]["insightface"] = getattr(insightface, "__version__", "unknown")
    except Exception as e:
        out["versions"]["insightface_error"] = str(e)
    try:
        import onnxruntime  # noqa
        import onnx  # noqa
        out["versions"]["onnxruntime"] = getattr(onnxruntime, "__version__", "unknown")
        out["versions"]["onnx"] = getattr(onnx, "__version__", "unknown")
    except Exception as e:
        out["versions"]["onnx/onnxruntime_error"] = str(e)
    return out

def op_download_models(model_url: Optional[str]) -> dict:
    """Download inswapper_128.onnx into /app/models."""
    url = model_url or DEFAULT_INSWAPPER_URL
    _ensure_dir(MODELS_DIR)
    _download_file(url, INSWAPPER_PATH)
    size = os.path.getsize(INSWAPPER_PATH)
    return {
        "status": "ok",
        "model_path": INSWAPPER_PATH,
        "bytes": size,
        "source": url,
    }

def op_swap(source_url: str, target_url: str, face_index_source: int = 0, face_index_target: int = 0) -> dict:
    """
    Swap the first (or specified) face from source onto target.
    Returns a base64 PNG.
    """
    # Load images
    src = _read_image_from_url(source_url)
    tgt = _read_image_from_url(target_url)

    # Detect faces
    app = _get_face_app()
    src_faces = app.get(src)
    tgt_faces = app.get(tgt)

    if not src_faces:
        raise ValueError("No face detected in source image.")
    if not tgt_faces:
        raise ValueError("No face detected in target image.")

    si = min(max(face_index_source, 0), len(src_faces) - 1)
    ti = min(max(face_index_target, 0), len(tgt_faces) - 1)

    # Swap
    swapper = _get_swapper()
    result = swapper.get(
        tgt, tgt_faces[ti], src_faces[si],
        paste_back=True  # keep full target image with swapped face
    )

    return {
        "status": "ok",
        "image_base64": _b64_png(result),
        "source_face_index": si,
        "target_face_index": ti,
    }

# ------------ runpod entry ------------

def handler(event):
    inp = event.get("input", {}) if isinstance(event, dict) else {}

    op = inp.get("op", "echo")
    try:
        if op == "version":
            return op_version()

        if op == "download_models":
            return op_download_models(inp.get("model_url"))

        if op == "swap":
            return op_swap(
                source_url=inp["source_url"],
                target_url=inp["target_url"],
                face_index_source=int(inp.get("source_face", 0)),
                face_index_target=int(inp.get("target_face", 0)),
            )

        # default echo
        return {"status": "ok", "echo": inp, "message": "Endpoint is alive."}

    except Exception as e:
        # Always return JSON error, never crash the pod
        return {"status": "error", "error": str(e)}

runpod.serverless.start({"handler": handler})
