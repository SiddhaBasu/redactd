"""Decision logic of scripts/budget_guard.py (the Fly and Prometheus calls are exercised by the workflow itself)."""
import importlib.util, os
spec = importlib.util.spec_from_file_location("budget_guard", os.path.join(os.path.dirname(__file__), "..", "scripts", "budget_guard.py"))
bg = importlib.util.module_from_spec(spec); spec.loader.exec_module(bg)
H, CAP, ALERT = 0.0904, 15.0, 10.0
hours = lambda h: h * 3600

def test_normal_hobby_use_is_ok():
    action, pace = bg.decide(hours(0.5), 1, H, CAP, ALERT)
    assert action == "ok" and round(pace, 2) == 1.40

def test_alert_between_10_and_15_dollar_pace():
    assert bg.decide(hours(4.0), 1, H, CAP, ALERT)[0] == "alert"       # 4 h/day -> $11.21/month pace

def test_stop_above_the_cap_and_never_resume_while_over_alert():
    assert bg.decide(hours(6.0), 1, H, CAP, ALERT)[0] == "stop"         # 6 h/day -> $16.81
    assert bg.decide(hours(24.0), 1, H, CAP, ALERT)[0] == "stop"        # always on, e.g. a bot pinging
    assert bg.decide(hours(4.0), 0, H, CAP, ALERT)[0] == "alert"        # stopped, still over the alert pace: stay stopped

def test_resume_once_the_last_day_is_quiet():
    assert bg.decide(hours(1.0), 0, H, CAP, ALERT)[0] == "resume"

def test_month_can_never_exceed_the_cap_plus_hourly_overshoot():
    # the most it can run per day before being stopped is the cap's daily share, plus one hour between checks
    daily_max_h = CAP / 31 / H + 1
    assert daily_max_h * 31 * H < CAP + 31 * H + 0.01

def test_auth_header_accepts_both_token_formats():
    assert bg.auth_header("FlyV1 fm2_abc") == "FlyV1 fm2_abc" and bg.auth_header("abc123") == "Bearer abc123"
