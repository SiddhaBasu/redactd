import os, sys, time
os.environ.setdefault("PRELOAD_MODES", "")
import tempfile; os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
from app.main import app

DOC = open(os.path.join(os.path.dirname(__file__), "../../../tests/fixtures/wire_recall.txt")).read()
MUST = ["Priya", "Raman", "priya.raman@northgate-mail.com", "0049821774471", "021000021", "GB82WEST12345698765432",
        "Royal Bank of Canada", "4111 1111 1111 1111", "555-0199", "123-45-6789", "Okafor", "Boise"]

def client():
    from app import main, limits
    main.limiter = limits.MemoryRateLimiter()     # each test starts with a clean rate-limit window
    return TestClient(app)

def test_health():
    with client() as c:
        assert c.get("/health").json()["status"] == "ok"

def test_redact_standard_removes_all_identifiers():
    with client() as c:
        r = c.post("/v1/redact", json={"text": DOC, "mode": "standard"}).json()
        leaked = [v for v in MUST if v in r["output"]]
        assert not leaked, (leaked, r["output"])
        assert r["leaks"] == 0 and r["vault"]
        # reversible: every placeholder maps back to an original value
        assert all(v in DOC for v in r["vault"].values())

def test_detect_rules_and_styles():
    with client() as c:
        d = c.post("/v1/detect", json={"text": DOC, "mode": "rules"}).json()
        assert any(DOC[s["start"]:s["end"]] == "GB82WEST12345698765432" for s in d["spans"])
        b = c.post("/v1/redact", json={"text": DOC, "mode": "rules", "style": "block"}).json()
        assert b["vault"] is None and "4111 1111" not in b["output"]

def test_validation_and_limits():
    with client() as c:
        assert c.post("/v1/detect", json={"text": DOC, "mode": "bogus"}).status_code == 422
        assert c.post("/v1/detect", json={"text": "x" * 200_001, "mode": "rules"}).status_code == 413

def test_async_job_roundtrip_and_single_delivery():
    with client() as c:
        jid = c.post("/v1/jobs", json={"text": DOC * 3, "mode": "rules"}).json()["job_id"]
        for _ in range(100):
            j = c.get(f"/v1/jobs/{jid}")
            if j.status_code == 200 and j.json()["status"] == "done": break
            time.sleep(0.05)
        assert j.json()["result"]["spans"]
        assert c.get(f"/v1/jobs/{jid}").status_code == 404   # result delivered once, then deleted

def test_no_text_in_database():
    from app import db
    with client() as c:
        c.post("/v1/detect", json={"text": DOC, "mode": "rules"})
    with db.Session() as s:
        rows = s.query(db.UsageEvent).all()
        dump = " ".join(str(vars(r)) for r in rows)
        assert rows and "Priya" not in dump and "4111" not in dump
