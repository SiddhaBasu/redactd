#!/usr/bin/env python3
"""Budget guard for the Fly API (run hourly by .github/workflows/budget-guard.yml).

Fly.io has no spending cap and keeps metrics for ~15 days, so the guard enforces a DAILY allowance derived from the
monthly cap: the machine may run at most MONTHLY_CAP_USD / 31 worth of time in any rolling 24 hours. Then the month
can never exceed the cap (plus at most one hour of overshoot per day between checks).

  rolling-24h cost pace > MONTHLY_ALERT_USD  -> exit 1 (GitHub emails the repo owner about the failed run)
  rolling-24h cost pace > MONTHLY_CAP_USD    -> remove the machine (`fly scale count 0`): requests can no longer wake it
  app stopped by the guard and pace < alert  -> put one machine back (`fly scale count 1`)

Running time comes from Fly's Prometheus metric fly_instance_up (any machine of the app reporting "up"), sampled at
30-second steps. Prometheus keeps a series alive ~5 minutes after a machine stops, so this over-counts slightly:
it errs on the side of stopping early, never late.

Env: FLY_API_TOKEN (org token), APP (default redactd-api), ORG (default personal), HOURLY_USD (default 0.0904 =
performance-2x $66 / 730 h), MONTHLY_CAP_USD (15), MONTHLY_ALERT_USD (10), REGION (iad), DRY_RUN (1 = no changes).
"""
import json, os, subprocess, sys, urllib.parse, urllib.request

STEP = 30

def decide(up_seconds_24h: float, machines: int, hourly: float, cap: float, alert: float) -> tuple[str, float]:
    """-> (action, monthly pace in USD). action: 'stop' | 'resume' | 'alert' | 'ok'."""
    pace = up_seconds_24h / 3600 * hourly * 31
    if machines > 0 and pace > cap: return "stop", pace
    if machines == 0 and pace <= alert: return "resume", pace
    if pace > alert: return "alert", pace
    return "ok", pace

def auth_header(token: str) -> str:
    token = token.strip()
    return token if token.startswith("FlyV1 ") else f"Bearer {token}"

def prom(query: str, org: str, token: str) -> float:
    url = f"https://api.fly.io/prometheus/{org}/api/v1/query?" + urllib.parse.urlencode({"query": query})
    req = urllib.request.Request(url, headers={"Authorization": auth_header(token)})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    if data.get("status") != "success": raise RuntimeError(f"prometheus query failed: {data.get('error', data)}")
    res = data["data"]["result"]
    return float(res[0]["value"][1]) if res else 0.0

def fly(*args: str) -> str:
    return subprocess.run(["flyctl", *args], check=True, capture_output=True, text=True).stdout

def main() -> int:
    token = os.environ.get("FLY_API_TOKEN", "")
    if not token: print("::error::FLY_API_TOKEN is not set"); return 2
    app, org = os.environ.get("APP", "redactd-api"), os.environ.get("ORG", "personal")
    hourly = float(os.environ.get("HOURLY_USD", "0.0904"))
    cap, alert = float(os.environ.get("MONTHLY_CAP_USD", "15")), float(os.environ.get("MONTHLY_ALERT_USD", "10"))
    dry = os.environ.get("DRY_RUN") == "1"
    q = f'sum_over_time((sum(fly_instance_up{{app="{app}"}}) > bool 0)[24h:{STEP}s])'
    up = prom(q, org, token) * STEP
    machines = [m for m in json.loads(fly("machine", "list", "--app", app, "--json") or "[]") if m.get("config", {}).get("metadata", {}).get("fly_process_group", "app") == "app"]
    action, pace = decide(up, len(machines), hourly, cap, alert)
    print(f"app={app} machines={len(machines)} running last 24h={up / 3600:.2f} h  -> monthly pace ${pace:.2f} "
          f"(alert ${alert:.0f}, cap ${cap:.0f})  action={action}{' (dry run)' if dry else ''}")
    if action == "stop":
        if not dry: fly("scale", "count", "0", "--app", app, "--yes")
        print(f"::error::Budget cap reached: the {app} machine was removed. It comes back automatically once the last 24 hours "
              f"are under the ${alert:.0f}/month pace, or redeploy with the deploy-api workflow.")
        return 1
    if action == "resume":
        if not dry: fly("scale", "count", "1", "--app", app, "--region", os.environ.get("REGION", "iad"), "--yes")
        print(f"::notice::Usage is back under the ${alert:.0f}/month pace: one machine restored.")
        return 0
    if action == "alert":
        print(f"::error::The API ran {up / 3600:.1f} h in the last 24 hours: a ${pace:.2f}/month pace, above the ${alert:.0f} alert line. "
              f"It will be stopped above ${cap:.0f}.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
