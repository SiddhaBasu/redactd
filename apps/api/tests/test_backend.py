"""C2/C4/C5: SSE progress, Redis-backed stores, API keys and quotas, input formats, content-free logs."""
import io, json, logging, os, sys, time
os.environ.setdefault("PRELOAD_MODES", "")
import tempfile; os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import db, jobs as jobs_mod, limits, obs, main as main_mod

DOC = open(os.path.join(os.path.dirname(__file__), "../../../tests/fixtures/wire_recall.txt")).read()
SECRETS = ["Priya", "Raman", "northgate", "0049821774471", "021000021", "GB82WEST", "4111", "555-0199", "123-45-6789", "Okafor", "Boise", "Royal Bank"]

@pytest.fixture()
def c():
    with TestClient(app) as cl: yield cl

@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(main_mod, "limiter", limits.MemoryRateLimiter())

@pytest.fixture()
def setting():
    """Temporarily change a (frozen) setting."""
    old = {}
    def set_(name, value):
        old.setdefault(name, getattr(main_mod.settings, name)); object.__setattr__(main_mod.settings, name, value)
    yield set_
    for k, v in old.items(): object.__setattr__(main_mod.settings, k, v)

@pytest.fixture()
def logs():
    class H(logging.Handler):
        def __init__(self): super().__init__(); self.lines = []
        def emit(self, r): self.lines.append(obs.JsonFormatter().format(r))
    h = H(); obs.log.addHandler(h); yield h.lines; obs.log.removeHandler(h)

# ---------------------------------------------------------------- C2: SSE
def test_job_progress_stream_then_single_delivery(c):
    jid = c.post("/v1/jobs", json={"text": DOC * 40, "mode": "rules"}).json()["job_id"]
    with c.stream("GET", f"/v1/jobs/{jid}/events") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())
    events = [l.split(": ", 1)[1] for l in body.splitlines() if l.startswith("event: ")]
    assert "progress" in events and events[-1] == "done"
    assert not any(s in body for s in SECRETS), "the progress stream must not carry content"
    pcts = [json.loads(l[6:])["pct"] for l in body.splitlines() if l.startswith("data: {") and "pct" in l]
    assert pcts == sorted(pcts) and pcts[-1] == 100
    assert c.get(f"/v1/jobs/{jid}").json()["result"]["spans"]
    assert c.get(f"/v1/jobs/{jid}").status_code == 404           # delivered once, then deleted
    assert c.get(f"/v1/jobs/{jid}/events").status_code == 404

# ---------------------------------------------------------------- C4: Redis stores behind the same interfaces
def test_redis_job_store_matches_memory_contract():
    import fakeredis
    for store in (jobs_mod.MemoryJobStore(), jobs_mod.RedisJobStore(fakeredis.FakeRedis())):
        jid = store.create()
        assert store.peek(jid)["status"] == "queued"
        store.update(jid, status="running", stage="Scanning", pct=40.0)
        assert store.take(jid)["status"] == "running"             # not finished: still there
        store.update(jid, status="done", pct=100, result={"spans": [{"start": 1, "end": 2}]})
        p = store.peek(jid); assert p["status"] == "done" and "result" not in p
        assert store.take(jid)["result"] == {"spans": [{"start": 1, "end": 2}]}
        assert store.take(jid) is None and store.peek(jid) is None
        store.update(jid, status="done")                           # update after delivery must not resurrect the job
        assert store.peek(jid) is None

def test_redis_job_ttl():
    import fakeredis
    r = fakeredis.FakeRedis(); s = jobs_mod.RedisJobStore(r, ttl=600); jid = s.create()
    assert 0 < r.ttl(s._k(jid)) <= 600

def test_rate_limiters():
    import fakeredis
    for lim in (limits.MemoryRateLimiter(), limits.RedisRateLimiter(fakeredis.FakeRedis())):
        assert [lim.allow("a", 3) for _ in range(5)] == [True, True, True, False, False]
        assert lim.allow("b", 3)

def test_anonymous_rate_limit_is_enforced(c, setting):
    setting("anon_rate_per_minute", 2)
    codes = [c.post("/v1/detect", json={"text": "hello", "mode": "rules"}).status_code for _ in range(4)]
    assert codes == [200, 200, 429, 429]

# ---------------------------------------------------------------- C4: API keys
def test_api_keys_are_hashed_and_have_their_own_quota(c):
    key = db.create_api_key("test integration", rate_per_minute=3, monthly_chars=40)
    with db.Session() as s:
        dump = " ".join(str(vars(k)) for k in s.query(db.ApiKey).all())
    assert key not in dump and key[3:20] not in dump and db.hash_key(key) in dump
    h = {"Authorization": f"Bearer {key}"}
    assert c.post("/v1/detect", json={"text": "x" * 30, "mode": "rules"}, headers=h).status_code == 200
    assert c.post("/v1/detect", json={"text": "x" * 30, "mode": "rules"}, headers=h).status_code == 200   # 30 < 40 at check time
    assert c.post("/v1/detect", json={"text": "x", "mode": "rules"}, headers=h).status_code == 429        # monthly quota used up
    assert c.post("/v1/detect", json={"text": "x", "mode": "rules"}, headers={"Authorization": "Bearer rk_nope"}).status_code == 401

def test_require_api_key_mode(c, setting):
    setting("require_api_key", True)
    assert c.post("/v1/detect", json={"text": "x", "mode": "rules"}).status_code == 401
    assert c.get("/health").status_code == 200

# ---------------------------------------------------------------- C4: formats
def _docx_bytes():
    import docx
    d = docx.Document(); d.add_paragraph("Wire recall for Priya Raman"); t = d.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text = "IBAN"; t.rows[0].cells[1].text = "GB82WEST12345698765432"; d.add_paragraph("SSN 123-45-6789")
    b = io.BytesIO(); d.save(b); return b.getvalue()

def _eml_bytes():
    from email.message import EmailMessage
    m = EmailMessage(); m["From"] = "Priya Raman <priya.raman@northgate-mail.com>"; m["To"] = "ops@example.com"; m["Subject"] = "Wire recall"
    m.set_content("Please recall the wire from account 0049821774471.")
    m.add_attachment(b"name,ssn\nDaniel Okafor,123-45-6789\n", maintype="text", subtype="csv", filename="statement_okafor.csv")
    return m.as_bytes()

def _pdf_bytes():
    from reportlab.pdfgen import canvas
    b = io.BytesIO(); cv = canvas.Canvas(b); cv.drawString(72, 720, "Beneficiary Daniel Okafor, card 4111 1111 1111 1111"); cv.save(); return b.getvalue()

def _msg_bytes():
    """Minimal Outlook .msg (OLE compound file) with a subject, a body and one attachment name."""
    import olefile  # noqa: F401
    pytest.importorskip("win32com", reason="writing .msg fixtures needs Outlook; the parser is covered by test_msg_parser_on_ole_layout")

def test_extract_docx_keeps_paragraphs_and_tables(c):
    r = c.post("/v1/extract", files={"file": ("recall.docx", _docx_bytes())}).json()
    assert r["format"] == "docx" and "Priya Raman" in r["text"] and "IBAN\tGB82WEST12345698765432" in r["text"] and "123-45-6789" in r["text"]

def test_extract_eml_lists_attachment_names_but_not_content_without_consent(c):
    r = c.post("/v1/extract", files={"file": ("m.eml", _eml_bytes())}).json()
    assert "0049821774471" in r["text"] and "statement_okafor.csv" in r["text"] and r["attachments"] == 1
    assert "Daniel Okafor" not in r["text"] and r["attachments_included"] is False
    r2 = c.post("/v1/extract", files={"file": ("m.eml", _eml_bytes())}, data={"include_attachments": "true"}).json()
    assert "Daniel Okafor" in r2["text"] and r2["attachments_included"] is True

def test_extract_pdf_text_layer(c):
    r = c.post("/v1/extract", files={"file": ("s.pdf", _pdf_bytes())}).json()
    assert r["format"] == "pdf" and "Daniel Okafor" in r["text"] and "4111 1111 1111 1111" in r["text"]

def test_extract_csv_and_json_keep_structure(c):
    csv = "name,iban\nPriya Raman,GB82WEST12345698765432\n"; js = '{"name": "Priya Raman",\n  "ssn": "123-45-6789"}'
    assert c.post("/v1/extract", files={"file": ("a.csv", csv.encode())}).json()["text"] == csv
    assert c.post("/v1/extract", files={"file": ("a.json", js.encode())}).json()["text"] == js
    d = c.post("/v1/redact", json={"text": js, "mode": "rules"}).json()["output"]
    assert "123-45-6789" not in d and d.startswith('{"name": ') and d.endswith('"}')

def test_msg_parser_on_ole_layout():
    """extract._msg reads the standard MAPI streams. Build the same layout with a fake OLE reader."""
    from app import extract as ex
    streams = {("__substg1.0_0037001F",): "Wire recall".encode("utf-16-le"), ("__substg1.0_1000001F",): "Body for Priya Raman".encode("utf-16-le"),
               ("__substg1.0_0C1A001F",): "Priya Raman".encode("utf-16-le"),
               ("__attach_version1.0_#00000000", "__substg1.0_3707001F"): "statement.pdf".encode("utf-16-le"),
               ("__attach_version1.0_#00000000", "__substg1.0_37010102"): b"SECRET ATTACHMENT BYTES"}
    class Fake:
        def __init__(self, _): pass
        def exists(self, p): return tuple(p) in streams
        def openstream(self, p): return io.BytesIO(streams[tuple(p)])
        def listdir(self, streams=False, storages=True): return [["__attach_version1.0_#00000000"]]
    import olefile; real = olefile.OleFileIO; olefile.OleFileIO = Fake
    try: text, meta = ex.extract("m.msg", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    finally: olefile.OleFileIO = real
    assert "Subject: Wire recall" in text and "Body for Priya Raman" in text and "statement.pdf" in text and "SECRET" not in text and meta["attachments"] == 1

def test_extract_rejects_unknown_and_broken_files_without_echo(c, logs):
    assert c.post("/v1/extract", files={"file": ("x.exe", b"MZ Priya Raman")}).status_code == 415
    r = c.post("/v1/extract", files={"file": ("x.docx", b"PK\x03\x04 Priya Raman 4111 1111 1111 1111")})
    assert r.status_code == 415 and "Priya" not in r.text and "4111" not in r.text
    assert not any(s in " ".join(logs) for s in SECRETS)

# ---------------------------------------------------------------- C5: logs carry metadata only
def test_logs_are_json_metadata_without_content(c, logs):
    c.post("/v1/detect", json={"text": DOC, "mode": "rules", "custom_terms": ["Northgate"], "allow_terms": ["Boise"]})
    c.post("/v1/redact", json={"text": DOC, "mode": "rules"})
    c.post("/v1/extract", files={"file": ("recall_priya_raman.docx", _docx_bytes())})
    c.post("/v1/detect", json={"text": DOC, "mode": "bogus"})                     # validation error
    jid = c.post("/v1/jobs", json={"text": DOC, "mode": "rules"}).json()["job_id"]
    for _ in range(100):
        if c.get(f"/v1/jobs/{jid}").status_code == 200: break
        time.sleep(0.02)
    time.sleep(0.2)
    dump = "\n".join(logs)
    leaked = [s for s in SECRETS if s.lower() in dump.lower()]
    assert not leaked, leaked
    recs = [json.loads(l) for l in logs]
    det = next(r for r in recs if r.get("event") == "detect")
    assert det["chars"] == len(DOC) and det["findings"] > 5 and det["by_type"]["FIN_ID"] >= 3 and len(det["request_id"]) == 16
    assert any(r.get("event") == "request" and r["path"] == "/v1/detect" and r["status"] == 200 for r in recs)
    assert any(r.get("event") == "job_done" for r in recs) and any(r.get("event") == "extract" and r["format"] == "docx" for r in recs)

def test_log_helper_rejects_fields_that_are_not_metadata():
    with pytest.raises(ValueError): obs.event("detect", text="Priya Raman")
    with pytest.raises(ValueError):
        with obs.span("detect", value="4111"): pass

def test_validation_errors_do_not_echo_input(c):
    r = c.post("/v1/detect", json={"text": DOC, "mode": "bogus", "sensitivity": "Priya Raman"})
    assert r.status_code == 422 and not any(s in r.text for s in SECRETS)
    assert {e["field"] for e in r.json()["errors"]} == {"mode", "sensitivity"}

def test_no_content_in_database_after_everything(c):
    c.post("/v1/redact", json={"text": DOC, "mode": "rules", "custom_terms": ["Northgate"]})
    raw = open(db.engine.url.database, "rb").read()
    assert not any(s.encode() in raw for s in SECRETS)

def test_raw_mode_returns_unmerged_findings_for_local_post_processing(c):
    fin = c.post("/v1/detect", json={"text": DOC, "mode": "rules"}).json()
    raw = c.post("/v1/detect", json={"text": DOC, "mode": "rules", "raw": True}).json()
    assert raw["raw"] is True and len(raw["spans"]) >= len(fin["spans"]) and all(s["source"] == "rules" for s in raw["spans"])
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
    from redactd.post import Span, finalize
    again = finalize(DOC, [Span(**s) for s in raw["spans"]])
    assert [(s.start, s.end, s.type) for s in again] == [(s["start"], s["end"], s["type"]) for s in fin["spans"]]
