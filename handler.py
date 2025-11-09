import runpod

def handler(event):
    inp = event.get("input", {}) if isinstance(event, dict) else {}
    op = inp.get("op")

    if op == "version":
        try:
            import facefusion
            ver = getattr(facefusion, "__version__", "unknown")
            return {"status": "ok", "facefusion_version": ver}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # default echo path
    return {
        "status": "ok",
        "echo": inp,
        "message": "FaceFusion serverless endpoint is alive."
    }

runpod.serverless.start({"handler": handler})
