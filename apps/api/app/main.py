"""redactd API — PII detection and redaction service.

Privacy rules enforced here:
  * request bodies are processed in memory and never logged or stored
  * only usage counts (chars, finding count, timing, salted client hash) go to the database
  * logs and traces carry metadata only (app/obs.py rejects any field that is not on its allow-list)
  * errors never echo document text back
"""
from __future__ import annotations
import asyncio, json, logging, os, sys, threading, time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import settings, ROOT
from . import db, obs
from .extract import extract, Unsupported
from .jobs import jobs
from .limits import make_limiter

sys.path.insert(0, ROOT)
from redactd.pipeline import Pipeline, Options, spans_json  # noqa: E402
from redactd.vault import redact as do_redact, leak_check  # noqa: E402

obs.setup_logging()
pipeline = Pipeline(settings.openmed_dir, settings.gliner_dir, settings.model_threads, settings.distilled_dir)
run_slots = threading.BoundedSemaphore(settings.max_concurrent_runs)
limiter = make_limiter()
state = {"ready": set()}

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    def warm():
        for m in [x for x in settings.preload.split(",") if x]:
            try:
                pipeline.warm(m); state["ready"].add(m)
                if m == "thorough": state["ready"].add("standard")
            except Exception as e:  # noqa: BLE001
                obs.event("warm_failed", logging.ERROR, mode=m, error_type=type(e).__name__)
        state["ready"].add("rules")
    threading.Thread(target=warm, daemon=True).start()
    yield

app = FastAPI(title="redactd API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_origin_regex=settings.allowed_origin_regex or None, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "Authorization"], expose_headers=["X-Request-Id"], max_age=600)

# ---------- auth, rate limit, metadata-only access log ----------
def _identify(request: Request):
    """-> (client_hash, per-minute limit, monthly char quota, auth kind) or a JSONResponse to return."""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        key = auth[7:].strip(); rec = db.find_api_key(key)
        if rec is None: return JSONResponse({"detail": "invalid API key"}, status_code=401)
        return db.client_id("key:" + db.hash_key(key)), rec["rate_per_minute"] or settings.rate_per_minute, rec["monthly_chars"], "key"
    if settings.require_api_key and request.url.path.startswith("/v1/"):
        return JSONResponse({"detail": "API key required"}, status_code=401)
    return db.client_id(request.client.host if request.client else "?"), settings.anon_rate_per_minute, None, "anon"

@app.middleware("http")
async def guard(request: Request, call_next):
    rid = obs.new_request_id(); request.state.request_id = rid; t0 = time.perf_counter()
    path = request.scope.get("route").path if request.scope.get("route") else request.url.path.split("/jobs/")[0] + ("/jobs/{id}" if "/jobs/" in request.url.path else "")
    def done(resp, client="-", auth="-"):
        if not request.url.path.startswith("/models/"): resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Request-Id"] = rid
        obs.event("request", request_id=rid, method=request.method, path=path, status=resp.status_code,
                  ms=round((time.perf_counter() - t0) * 1000, 1), client=client, auth=auth)
        return resp
    if request.method == "OPTIONS" or request.url.path == "/health" or request.url.path.startswith("/models/"):
        return done(await call_next(request))
    who = await run_in_threadpool(_identify, request)
    if isinstance(who, JSONResponse): return done(who)
    client, limit, quota, auth = who
    request.state.client = client; request.state.quota = quota
    if request.url.path.startswith("/v1/") and request.method == "POST":
        if not limiter.allow(client, limit):
            r = JSONResponse({"detail": "rate limit exceeded"}, status_code=429, headers={"Retry-After": "60"}); return done(r, client, auth)
        if int(request.headers.get("content-length") or 0) > max(settings.max_chars * 4, settings.max_upload_bytes) + 10_000:
            return done(JSONResponse({"detail": "request too large"}, status_code=413), client, auth)
        if quota is not None and await run_in_threadpool(db.chars_this_month, client) >= quota:
            return done(JSONResponse({"detail": "monthly quota exceeded"}, status_code=429), client, auth)
    return done(await call_next(request), client, auth)

@app.exception_handler(Exception)
async def no_leak_errors(request: Request, exc: Exception):
    obs.event("unhandled", logging.ERROR, request_id=getattr(request.state, "request_id", "-"), error_type=type(exc).__name__)  # no message: it may contain text
    return JSONResponse({"detail": "internal error"}, status_code=500)

@app.exception_handler(RequestValidationError)
async def no_leak_validation(request: Request, exc: RequestValidationError):
    # FastAPI's default 422 body echoes the offending input, which can be document text. Return field names only.
    errs = [{"field": ".".join(str(x) for x in e.get("loc", [])[1:]), "type": e.get("type", "")} for e in exc.errors()]
    return JSONResponse({"detail": "invalid request", "errors": errs}, status_code=422)

# ---------- schemas ----------
Mode = Literal["rules", "standard", "thorough"]
PiiTypeName = Literal["NAME", "CONTACT", "ADDRESS", "GOV_ID", "FIN_ID", "SECRET", "NETWORK", "DATE", "ORG", "DEMOGRAPHIC", "CUSTOM"]

class DetectIn(BaseModel):
    text: str = Field(..., max_length=settings.max_chars)
    mode: Mode = "thorough"
    sensitivity: float = Field(0.35, ge=0.05, le=0.95)
    org_allowlist: bool = True              # keep public bodies / regulators / card networks
    drop_nonpersonal_dates: bool = True     # keep "Q3 2025", "FY2024"
    keep_last4: bool = False
    custom_terms: list[str] = Field(default_factory=list, max_length=500)   # user content: never logged or stored
    allow_terms: list[str] = Field(default_factory=list, max_length=500)
    exclude_types: list[PiiTypeName] = Field(default_factory=list)
    raw: bool = False   # return unmerged findings; the web app then runs the same post-processing locally, so presets,
                        # custom terms and the allow-list can change without sending the document again

    def options(self) -> Options:
        return Options(sensitivity=self.sensitivity, org_allowlist=self.org_allowlist, drop_nonpersonal_dates=self.drop_nonpersonal_dates,
                       keep_last4=self.keep_last4, custom_terms=self.custom_terms, allow_terms=self.allow_terms, exclude_types=list(self.exclude_types))

class RedactIn(DetectIn):
    style: Literal["placeholder", "label", "block"] = "placeholder"

def _run(body: DetectIn, progress=None):
    with run_slots:
        if getattr(body, "raw", False) and not isinstance(body, RedactIn):
            spans, timings = pipeline.detect_raw(body.text, body.mode, body.sensitivity, progress)
            timings["total_ms"] = sum(timings.values()); return spans, timings
        return pipeline.detect(body.text, body.mode, body.sensitivity, body.options(), progress)

def _render(text, spans, style):
    red, vault = do_redact(text, [(s.start, s.end, s.type) for s in spans], style=style)
    # the vault is not returned for irreversible styles
    return red, (vault if style == "placeholder" else None), leak_check(red, vault)

def _timings(t): return {k: round(v, 1) for k, v in t.items()}

def _account(request: Request, endpoint: str, body: DetectIn, spans, timings, **extra):
    db.record(request.state.client, endpoint, body.mode, len(body.text), len(spans), timings["total_ms"])
    obs.event("detect", request_id=request.state.request_id, endpoint=endpoint, mode=body.mode, chars=len(body.text), findings=len(spans),
              by_type=obs.by_type(spans), stage_ms=_timings(timings), **extra)

# ---------- endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok", "ready_modes": sorted(state["ready"]), "versions": pipeline.versions(), "sync_limit_chars": settings.sync_limit_chars}

@app.post("/v1/detect")
async def detect(body: DetectIn, request: Request):
    if len(body.text) > settings.sync_limit_chars:
        raise HTTPException(413, f"documents over {settings.sync_limit_chars} chars must use POST /v1/jobs")
    with obs.span("detect", mode=body.mode, chars=len(body.text)) as put:
        spans, timings = await run_in_threadpool(_run, body)
        put(findings=len(spans), by_type=obs.by_type(spans))
    _account(request, "detect", body, spans, timings)
    return {"mode": body.mode, "raw": body.raw, "spans": spans_json(spans), "timings": _timings(timings), "versions": pipeline.versions()}

@app.post("/v1/redact")
async def redact(body: RedactIn, request: Request):
    if len(body.text) > settings.sync_limit_chars:
        raise HTTPException(413, f"documents over {settings.sync_limit_chars} chars must use POST /v1/jobs")
    with obs.span("redact", mode=body.mode, chars=len(body.text)) as put:
        spans, timings = await run_in_threadpool(_run, body)
        out, vault, leaks = _render(body.text, spans, body.style)
        put(findings=len(spans), leaks=len(leaks))
    _account(request, "redact", body, spans, timings, leaks=len(leaks))
    return {"output": out, "vault": vault, "leaks": len(leaks), "findings": len(spans), "by_type": obs.by_type(spans),
            "timings": _timings(timings), "versions": pipeline.versions()}

@app.post("/v1/jobs", status_code=202)
async def create_job(body: DetectIn, request: Request):
    jid = jobs.create(); client = request.state.client; rid = request.state.request_id
    def work():
        try:
            jobs.update(jid, status="running", stage="Waiting for a free worker", pct=1)
            last = [0.0]
            def progress(stage, pct):
                now = time.monotonic()
                if now - last[0] >= 0.2 or pct >= 99: last[0] = now; jobs.update(jid, stage=stage, pct=round(2 + pct * 0.97, 1))
            spans, timings = _run(body, progress)
            db.record(client, "job", body.mode, len(body.text), len(spans), timings["total_ms"])
            obs.event("job_done", request_id=rid, job_id=jid, mode=body.mode, chars=len(body.text), findings=len(spans), by_type=obs.by_type(spans), stage_ms=_timings(timings))
            jobs.update(jid, result={"mode": body.mode, "raw": body.raw, "spans": spans_json(spans), "timings": _timings(timings), "versions": pipeline.versions()},
                        stage="Done", pct=100, status="done")
        except Exception as e:  # noqa: BLE001
            obs.event("job_failed", logging.ERROR, request_id=rid, job_id=jid, error_type=type(e).__name__)
            jobs.update(jid, status="error", error="detection failed")
    asyncio.get_running_loop().run_in_executor(None, work)
    return {"job_id": jid, "status": "queued"}

@app.get("/v1/jobs/{jid}")
def get_job(jid: str):
    j = jobs.take(jid)
    if not j: raise HTTPException(404, "job not found or already collected")
    return j

@app.get("/v1/jobs/{jid}/events")
async def job_events(jid: str):
    """Server-sent events: `progress` {stage, pct} while the job runs, then `done` or `failed`. The stream never
    carries the result; collect it once with GET /v1/jobs/{id}, after which it is deleted."""
    if jobs.peek(jid) is None: raise HTTPException(404, "job not found or already collected")
    async def stream():
        last = None; deadline = time.monotonic() + settings.job_ttl_s
        while time.monotonic() < deadline:
            j = await run_in_threadpool(jobs.peek, jid)
            if j is None: yield "event: failed\ndata: {}\n\n"; return
            cur = (j.get("stage"), j.get("pct"))
            if cur != last:
                last = cur; yield f"event: progress\ndata: {json.dumps({'stage': j.get('stage', ''), 'pct': j.get('pct', 0)})}\n\n"
            if j["status"] == "done": yield "event: done\ndata: {}\n\n"; return
            if j["status"] == "error": yield "event: failed\ndata: {}\n\n"; return
            await asyncio.sleep(0.25)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Connection": "keep-alive"})

# ---------- model files for on-device mode (task D7) ----------
# The image already contains the int8 model files, so the API serves them to browsers that choose on-device mode
# (no separate model CDN needed). Only the files listed in the web app's integrity manifest exist here; the browser
# verifies every file's SHA-256 before use. Cross-origin headers are required because the web app is
# cross-origin isolated (COEP: require-corp).
MODEL_FILES = {"redactd-small": settings.distilled_dir, "gliner": settings.gliner_dir}
MODEL_EXT = (".json", ".onnx")

@app.get("/models/{model}/{path:path}")
def model_file(model: str, path: str, request: Request):
    from fastapi.responses import FileResponse
    base = MODEL_FILES.get(model)
    if not base or not path.endswith(MODEL_EXT) or ".." in path.split("/"): raise HTTPException(404, "not found")
    full = os.path.realpath(os.path.join(base, path))
    if not full.startswith(os.path.realpath(base) + os.sep) or not os.path.isfile(full): raise HTTPException(404, "not found")
    origin = request.headers.get("origin", "")
    headers = {"Cache-Control": "public, max-age=31536000, immutable", "Cross-Origin-Resource-Policy": "cross-origin"}
    import re
    if origin in settings.allowed_origins or (settings.allowed_origin_regex and re.fullmatch(settings.allowed_origin_regex, origin)):
        headers["Access-Control-Allow-Origin"] = origin; headers["Vary"] = "Origin"
    return FileResponse(full, media_type="application/octet-stream", headers=headers)

@app.post("/v1/extract")
async def extract_file(request: Request, file: UploadFile = File(...), include_attachments: bool = Form(False)):
    """Convert .docx / .eml / .msg / .pdf / .csv / .json / text to plain text, in memory. Returns the text to the
    caller and stores nothing. Email attachments are listed by name; their content is read only when the caller
    sets include_attachments=true (the UI asks the user first)."""
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes: raise HTTPException(413, "file too large")
    try:
        text, meta = await run_in_threadpool(extract, file.filename or "", data, include_attachments)
    except Unsupported as e:
        raise HTTPException(415, str(e))
    if len(text) > settings.max_chars: raise HTTPException(413, f"extracted text is {len(text)} characters; the limit is {settings.max_chars}")
    obs.event("extract", request_id=request.state.request_id, format=meta["format"], bytes=len(data), chars=len(text), attachments=meta["attachments"])
    return {"text": text, **meta}
