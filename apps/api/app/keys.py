"""API key admin.  python -m app.keys create "Acme integration" [--rate 120] [--monthly-chars 50000000] | list | revoke <id>"""
import argparse
from . import db

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create"); c.add_argument("name"); c.add_argument("--rate", type=int); c.add_argument("--monthly-chars", type=int)
    sub.add_parser("list"); r = sub.add_parser("revoke"); r.add_argument("id", type=int)
    a = ap.parse_args(); db.init_db()
    if a.cmd == "create":
        print("API key (shown once, store it now):", db.create_api_key(a.name, a.rate, a.monthly_chars))
    elif a.cmd == "list":
        with db.Session() as s:
            for k in s.query(db.ApiKey).all(): print(k.id, k.prefix + "…", k.name, "revoked" if k.revoked else "active", k.rate_per_minute, k.monthly_chars)
    else:
        with db.Session() as s:
            k = s.get(db.ApiKey, a.id)
            if k: k.revoked = True; s.commit(); print("revoked", a.id)

if __name__ == "__main__":
    main()
