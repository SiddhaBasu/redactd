"""Observability without content (task C5).

One JSON log line per request and per job, carrying ONLY metadata: request id, method, path, status, duration,
sizes, mode, finding counts per type, salted client hash. Nothing derived from document text ever reaches a log
record, an exception message or a trace attribute. tests/test_privacy.py greps captured logs for fixture values.

Traces: if OTEL_EXPORTER_OTLP_ENDPOINT is set and opentelemetry is installed, each detection is a span with the same
metadata attributes. Without it, span() is a no-op.
"""
from __future__ import annotations
import contextlib, json, logging, sys, time, uuid
from .config import settings

ALLOWED = {"event", "request_id", "method", "path", "status", "ms", "client", "mode", "chars", "bytes", "findings", "by_type", "endpoint",
           "format", "stage_ms", "error_type", "job_id", "leaks", "attachments", "auth"}

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        d = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z", "level": record.levelname.lower(), "logger": record.name}
        meta = getattr(record, "meta", None)
        if meta is not None: d.update(meta)
        else: d["message"] = record.getMessage()
        return json.dumps(d, separators=(",", ":"))

log = logging.getLogger("redactd.api")

def setup_logging():
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter() if settings.log_format == "json" else logging.Formatter("%(asctime)s %(levelname)s %(message)s %(meta)s", defaults={"meta": ""}))
    log.handlers[:] = [h]; log.setLevel(logging.INFO); log.propagate = False
    logging.getLogger("uvicorn.access").disabled = True   # default access log is replaced by our metadata-only line

def event(name: str, level: int = logging.INFO, **meta):
    """Log a metadata-only event. Unknown keys are rejected so content cannot be added by accident."""
    bad = set(meta) - ALLOWED
    if bad: raise ValueError(f"log field(s) not on the metadata allow-list: {sorted(bad)}")
    log.log(level, name, extra={"meta": {"event": name, **meta}})

def new_request_id() -> str:
    return uuid.uuid4().hex[:16]

def by_type(spans) -> dict:
    out: dict = {}
    for s in spans: out[s.type] = out.get(s.type, 0) + 1
    return out

_tracer = None
def _get_tracer():
    global _tracer
    if _tracer is None:
        _tracer = False
        if settings.otel_endpoint:
            try:
                from opentelemetry import trace
                from opentelemetry.sdk.resources import Resource
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                p = TracerProvider(resource=Resource.create({"service.name": "redactd-api"}))
                p.add_span_processor(BatchSpanProcessor(OTLPSpanExporter())); trace.set_tracer_provider(p)
                _tracer = trace.get_tracer("redactd.api")
            except Exception as e:  # noqa: BLE001
                event("otel_disabled", logging.WARNING, error_type=type(e).__name__)
    return _tracer

@contextlib.contextmanager
def span(name: str, **attrs):
    """Trace span with metadata-only attributes (same allow-list as logs). The yielded setter adds more."""
    t = _get_tracer()
    def check(d):
        bad = set(d) - ALLOWED
        if bad: raise ValueError(f"trace attribute(s) not on the metadata allow-list: {sorted(bad)}")
    check(attrs)
    if not t:
        yield lambda **kw: check(kw); return
    with t.start_as_current_span(name) as sp:
        def put(**kw):
            check(kw)
            for k, v in kw.items(): sp.set_attribute(f"redactd.{k}", json.dumps(v) if isinstance(v, dict) else v)
        put(**attrs); yield put
