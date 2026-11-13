"""Regression tests for the two leak-check failures found on held-out data (diagnosed with bench/leak_diag.py,
which prints only lengths and character shapes, never text)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from redactd.post import Span, finalize
from redactd.vault import redact, leak_check

def run(text, raw):
    fin = finalize(text, raw)
    out, vault = redact(text, [(s.start, s.end, s.type) for s in fin])
    return out, leak_check(out, vault)

def sp(text, value, typ, nth=0, src="distilled"):
    i = -1
    for _ in range(nth + 1): i = text.index(value, i + 1)
    return Span(i, i + len(value), typ, src, 0.9, typ, [], [src])

def test_value_inside_our_own_placeholder_is_not_a_leak():
    # cause 1: a redacted value "ORG" matched inside the generated "[ORG_1]"
    t = "Header ORG: Northgate. Contact SEC desk."
    out, leaks = run(t, [sp(t, "ORG", "ORG")])
    assert "[ORG_1]" in out and leaks == []

def test_value_left_in_clear_is_still_a_leak():
    t = "Code ORG here and ORG there."
    out, vault = redact(t, [(5, 8, "ORG")])          # second occurrence deliberately not redacted
    assert leak_check(out, vault) == ["ORG"]

def test_partial_digit_findings_are_widened_so_halves_cannot_reappear():
    # cause 2: a model span covering half of a digit run ("4471" of "55664471"); another span covering the other half
    # of a different run ("7788" of "77884471"). Rendering then left "4471" standing alone in the output.
    t = "ref 55664471 and ref 77884471 end"
    out, leaks = run(t, [sp(t, "4471", "ADDRESS"), sp(t, "7788", "ADDRESS")])
    assert leaks == [] and "4471" not in out and "7788" not in out and "5566" not in out

def test_manual_selections_are_not_widened():
    t = "acct 0049821774471"
    fin = finalize(t, [Span(5, 9, "FIN_ID", "manual", None, "manual", [], ["manual"])])
    assert [(s.start, s.end) for s in fin] == [(5, 9)]

def test_partial_word_findings_are_widened_too():
    # same failure with letters: "TIC" found inside "SEMANTIC"; elsewhere "TIC" sat between two redacted runs
    t = "type SEMANTIC and 4471TIC9921 end"
    out, leaks = run(t, [sp(t, "TIC", "SECRET"), sp(t, "4471", "FIN_ID"), sp(t, "9921", "FIN_ID")])
    assert leaks == [] and "SEMANTIC" not in out and "4471" not in out   # the redacted value is now the whole word

def test_glued_letter_and_digit_runs_stay_separate():
    from redactd.post import snap_digits
    t = "amt 041316.75Corona Requena"
    assert snap_digits(t, 13, 19) == (13, 19)          # "Corona" is not widened into the digits
    assert snap_digits(t, 15, 18) == (13, 19)          # "ron" inside "Corona" is
