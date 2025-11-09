import runpod

def handler(event):
    """Minimal handler with a safe 'version' op."""
    inp = event.get("input", {}) if isinstance(event, dict) else {}
    op = inp.get("op", "echo")

    if op == "version":
        versions = {}

        # Report insightface version (our active stack)
        try:
            import insightface
            versions["insightface"] = getattr(insightface, "__version__", "unknown")
        except Exception as e:
            versions["insightface_error"] = str(e)

        # These imports are optional; we swallow errors so the op never fails
        try:
            import facefusion  # pragma: no cover
            versions["facefusion"] = getattr(facefusion, "__version__", "unknown")
        except Exception:
            pass
        try:
            import facefusion_core  # pragma: no cover
            versions["facefusion_core"] = getattr(facefusion_core, "__version__", "unknown")
        except Exception:
            pass

        return {"status": "ok", "versions": versions}

    # Default echo path
    return {
        "status": "ok",
        "echo": inp,
        "message": "Endpoint is alive."
    }

runpod.serverless.start({"handler": handler})
