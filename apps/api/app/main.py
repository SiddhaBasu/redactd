"""redactd API — PII detection and redaction service.

Privacy rules enforced here:
  * request bodies are processed in memory and never logged or stored
  * only usage counts (chars, finding count, timing, salted client hash) go to the database
  * errors never echo document text back
"""
from __future__ import annotations
import asyncio, logging, os, sys, threading, time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import settings, ROOT
from . import db
from .jobs import jobs

sys.path.insert(0, ROOT)
from redactd.pipeline import Pipeline, spans_json  # noqa: E402
from redactd.vault import redact as do_redact, leak_check  # noqa: E402

log = logging.getLogger("redactd.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
for noisy in ("uvicorn.access",):  # default access log is fine (no bodies), but we use our own metadata-only line
    logging.getLogger(noisy).disabled = True

pipeline = Pipeline(settings.openmed_dir, settings.gliner_dir, settings.model_threads)
run_slots = threading.BoundedSemaphore(settings.max_concurrent_runs)
state = {"ready": set()}

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    def warm():
        for m in [x for x in settings.preload.split(",") if x]:
            pipeline.warm(m); state["ready"].add(m)
            if m == "thorough": state["ready"].add("standard")
        state["ready"].add("rules")
    threading.Thread(target=warm, daemon=True).start()
    yield

app = FastAPI(title="redactd API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "Authorization"], max_age=600)

# ---------- metadata-only access log + simple per-client rate limit ----------
hits: dict[str, deque] = defaultdict(deque)

@app.middleware("http")
async def guard(request: Request, call_next):
    client = db.client_id(request.headers.get("authorization") or (request.client.host if request.client else "?"))
    request.state.client = client
    if request.url.path.startswith("/v1/") and request.method == "POST":
        q, now = hits[client], time.time()
        while q and now - q[0] > 60: q.popleft()
        if len(q) >= settings.rate_per_minute:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429, headers={"Retry-After": "60"})
        q.append(now)
        if int(request.headers.get("content-length") or 0) > settings.max_chars * 4 + 10_000:
            return JSONResponse({"detail": "request too large"}, status_code=413)
    t0 = time.perf_counter()
    resp = await call_next(request)
    log.info("%s %s %s %.0fms client=%s", request.method, request.url.path, resp.status_code,
             (time.perf_counter() - t0) * 1000, client)
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.exception_handler(Exception)
async def no_leak_errors(request: Request, exc: Exception):
    log.error("unhandled %s on %s", type(exc).__name__, request.url.path)  # no message: it may contain text
    return JSONResponse({"detail": "internal error"}, status_code=500)

# ---------- schemas ----------
Mode = Literal["rules", "standard", "thorough"]

class DetectIn(BaseModel):
    text: str = Field(..., max_length=settings.max_chars)
    mode: Mode = "thorough"
    sensitivity: float = Field(0.35, ge=0.05, le=0.95)

class RedactIn(DetectIn):
    style: Literal["placeholder", "label", "block"] = "placeholder"

def _run(text: str, mode: str, sensitivity: float):
    with run_slots:
        return pipeline.detect(text, mode, sensitivity)

def _render(text, spans, style):
    tuples = [(s.start, s.end, s.type) for s in spans]
    red, vault = do_redact(text, tuples)
    if style != "placeholder":
        # re-render placeholders as labels or blocks; vault is not returned for irreversible styles
        import re
        red = re.sub(r"\[([A-Z_]+?)_\d+\]", (lambda m: f"[{m.group(1)}]") if style == "label" else (lambda m: "█" * 6), red)
        return red, None, leak_check(red, vault)
    return red, vault, leak_check(red, vault)

# ---------- endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok", "ready_modes": sorted(state["ready"])}

@app.post("/v1/detect")
async def detect(body: DetectIn, request: Request):
    if len(body.text) > settings.sync_limit_chars:
        raise HTTPException(413, f"documents over {settings.sync_limit_chars} chars must use POST /v1/jobs")
    spans, timings = await run_in_threadpool(_run, body.text, body.mode, body.sensitivity)
    db.record(request.state.client, "detect", body.mode, len(body.text), len(spans), timings["total_ms"])
    return {"mode": body.mode, "spans": spans_json(spans), "timings": {k: round(v, 1) for k, v in timings.items()}}

@app.post("/v1/redact")
async def redact(body: RedactIn, request: Request):
    if len(body.text) > settings.sync_limit_chars:
        raise HTTPException(413, f"documents over {settings.sync_limit_chars} chars must use POST /v1/jobs")
    spans, timings = await run_in_threadpool(_run, body.text, body.mode, body.sensitivity)
    out, vault, leaks = _render(body.text, spans, body.style)
    db.record(request.state.client, "redact", body.mode, len(body.text), len(spans), timings["total_ms"])
    return {"output": out, "vault": vault, "leaks": len(leaks), "findings": len(spans),
            "timings": {k: round(v, 1) for k, v in timings.items()}}

@app.post("/v1/jobs", status_code=202)
async def create_job(body: DetectIn, request: Request):
    jid = jobs.create(); client = request.state.client
    def work(text=body.text, mode=body.mode, sens=body.sensitivity):
        try:
            jobs.update(jid, status="running")
            spans, timings = _run(text, mode, sens)
            db.record(client, "job", mode, len(text), len(spans), timings["total_ms"])
            jobs.update(jid, status="done", result={"mode": mode, "spans": spans_json(spans),
                                                    "timings": {k: round(v, 1) for k, v in timings.items()}})
        except Exception as e:  # noqa: BLE001
            log.error("job failed: %s", type(e).__name__)
            jobs.update(jid, status="error", error="detection failed")
    asyncio.get_running_loop().run_in_executor(None, work)
    return {"job_id": jid, "status": "queued"}

@app.get("/v1/jobs/{jid}")
def get_job(jid: str):
    j = jobs.take(jid)
    if not j: raise HTTPException(404, "job not found or already collected")
    return {k: v for k, v in j.items() if k != "created"}
