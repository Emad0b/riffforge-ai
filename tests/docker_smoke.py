"""Real HTTP → Redis/Celery → ONNX → tab smoke, no mocked inference."""

import json
import time
import urllib.request

base = "http://127.0.0.1:8400/api"


def request(path, method="GET", token=None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    with urllib.request.urlopen(
        urllib.request.Request(base + path, method=method, headers=headers), timeout=30
    ) as r:
        return json.load(r)


token = request("/session", "POST")["token"]
assert request("/health")["queue"] == "celery-redis"
job = request("/demo", "POST", token)["id"]
deadline = time.time() + 180
while time.time() < deadline:
    result = request("/transcriptions/" + job, token=token)
    if result["state"] == "failed":
        raise RuntimeError(result["error"])
    if result["state"] == "complete":
        assert len(result["result"]["raw_notes"]) == 14, result
        assert len(result["result"]["notes"]) == 14
        print(
            "Redis/Celery real-model smoke passed:",
            result["result"]["seconds"],
            "seconds",
        )
        break
    time.sleep(1)
else:
    raise TimeoutError("Worker did not complete in 180 seconds")
