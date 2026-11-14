"""Step 2: check the script's answers.

Run:  python check.py KY
  A. Is every quote really in the law, and is the number really in the quote?
     (catches made-up answers; rejected answers are kept in out/KY_rejected.json)
  B. Does each answer match the answer key?  (gives accuracy)
  C. Lists every rejected answer and whether it would have been right
Writes a report to out/KY_report.md
"""
import json
import sys
from pathlib import Path

from quote_utils import clean, number_in_quote

STATE = sys.argv[1]
NUMBER_FIELDS = {"bond_min_usd", "bond_max_usd", "net_worth_min_usd",
                 "application_fee_usd", "renewal_fee_usd", "decision_days"}


law = {f.stem: clean(f.read_text(encoding="utf-8")) for f in Path("raw", STATE).glob("*.txt")}
key = json.loads(Path(f"answer_key/{STATE}.json").read_text(encoding="utf-8"))["fields"]
pred = json.loads(Path(f"out/{STATE}.json").read_text(encoding="utf-8"))["fields"]
report = [f"# {STATE} extraction report", ""]


def quote_problem(name, f):
    """None if the answer is backed by the law, otherwise a short reason."""
    if not f.get("quote"):
        return "no quote"
    if f.get("section") not in law:
        return "section not in raw files"
    if clean(f["quote"]) not in law[f["section"]]:
        return "quote not found in section"
    if name in NUMBER_FIELDS and not number_in_quote(f.get("value"), f["quote"]):
        return "value not in quote"
    return None


def same(name, got, want):
    if name == "exemptions":
        return set(got or []) == set(want or [])
    return got == want


# A. Quote check, for the answer key and for the script.
# Rejected answers are not deleted: they go in `rejected` (saved to out/STATE_rejected.json)
# and the cleaned copy `clean_pred` (value set to None) is what gets scored.
print("A. Does every quote really appear in the law, and the number in the quote?\n")
report += ["## A. Quote check", "", "| Field | Answer key | Script |", "|---|---|---|"]
rejected, clean_pred = [], {}
for name in key:
    k_why = None if key[name].get("value") is None else quote_problem(name, key[name])
    k_status = "ok" if k_why is None else f"{k_why.upper()} (fix the answer key!)"
    p = dict(pred.get(name, {"value": None, "section": None}))
    why = None if p.get("value") is None else quote_problem(name, p)
    if p.get("value") is None:
        p_status = "no answer"
    elif why is None:
        p_status = "ok"
    else:
        p_status = f"REJECTED: {why}"
        rejected.append({"field": name, "reason": why, "value": p.get("value"),
                         "section": p.get("section"), "quote": p.get("quote"), "note": p.get("note"),
                         "would_match_answer_key": same(name, p.get("value"), key[name]["value"])})
        p["value"] = None
    clean_pred[name] = p
    print(f"  {name:21} key: {k_status:32} script: {p_status}")
    report.append(f"| {name} | {k_status} | {p_status} |")
thrown_out = len(rejected)
pred = clean_pred

# B. Score against the answer key
print("\nB. Does each answer match the answer key?\n")
report += ["", "## B. Accuracy", "", "| Field | Result | Script said | Answer key says |", "|---|---|---|---|"]
correct, fails = 0, []
ex_stats = None
for name, k in key.items():
    p = pred.get(name, {"value": None, "section": None})
    if name == "exemptions":
        got, want = set(p["value"] or []), set(k["value"] or [])
        ok = got == want
        ex_stats = (len(got & want), len(got - want), len(want - got))      # right, wrong, missed
        detail = f"{len(got & want)} of {len(want)} found"
        if want - got:
            detail += f"; missed {sorted(want - got)}"
        if got - want:
            detail += f"; wrong {sorted(got - want)}"
    elif k["value"] is None:
        ok = p["value"] is None                  # both agree there is no answer in the text
        detail = f"{p['value']} vs none"
    else:
        ok = p["value"] == k["value"] and p.get("section") == k["section"]
        detail = f"{p['value']} (sec {p.get('section')}) vs {k['value']} (sec {k['section']})"
    correct += ok
    print(f"  {name:21} {'correct' if ok else 'WRONG':8} {detail if not ok else ''}")
    report.append(f"| {name} | {'correct' if ok else 'WRONG'} | {p['value'] if name != 'exemptions' else len(p['value'] or [])} | {k['value'] if name != 'exemptions' else len(k['value'] or [])} |")
    if not ok:
        fails.append(f"- **{name}**: {detail}")

total = len(key)
summary = f"Field-level accuracy: {correct}/{total} = {correct / total:.0%}. Answers thrown out for fake quotes: {thrown_out}."
print(f"\n{summary}")
print("Fields that failed:")
print("\n".join(fails) if fails else "  none")
report += ["", f"**{summary}**", "", "## Fields that failed", ""] + (fails or ["none"])

# Exemptions are scored all-or-nothing above, so also report partial credit.
# A wrong tag is worse for a user than a missed one, so the two are counted separately.
if ex_stats:
    right, wrong, missed = ex_stats
    precision = right / (right + wrong) if right + wrong else 1.0
    recall = right / (right + missed) if right + missed else 1.0
    ex_line = (f"Exemptions: precision {precision:.0%} ({wrong} wrong tag(s)), "
               f"recall {recall:.0%} ({missed} missed).")
    print(ex_line)
    report += ["", f"**{ex_line}**"]

# C. Rejected answers: kept, not deleted, so a person can review them
print(f"\nC. Rejected answers kept for review: {len(rejected)}")
report += ["", "## C. Rejected answers (kept in out/" + STATE + "_rejected.json)", ""]
if rejected:
    report += ["| Field | Why rejected | Value | Would have matched key? |", "|---|---|---|---|"]
    for r in rejected:
        shown = f"{len(r['value'])} items" if isinstance(r["value"], list) else r["value"]
        print(f"  {r['field']:21} {r['reason']:28} would have matched key: {r['would_match_answer_key']}")
        report.append(f"| {r['field']} | {r['reason']} | {shown} | {'yes' if r['would_match_answer_key'] else 'no'} |")
else:
    report.append("none")
Path(f"out/{STATE}_rejected.json").write_text(json.dumps(rejected, indent=2), encoding="utf-8")
Path(f"out/{STATE}_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
print(f"\nReport saved to out/{STATE}_report.md")