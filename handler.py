# handler.py — minimal RunPod serverless handler (we’ll wire FaceFusion next)
import runpod

def handler(event):
    # event["input"] is what RunPod sends us
    inp = event.get("input", {}) if isinstance(event, dict) else {}
    return {
        "status": "ok",
        "echo": inp,               # sends back whatever was sent in (for testing)
        "message": "FaceFusion serverless endpoint is alive."
    }

# start the serverless worker
runpod.serverless.start({"handler": handler})
