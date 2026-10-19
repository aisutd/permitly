"""Step 2: check the script's answers.

Run:  python check.py TX
  A. Is every quote really in the law?  (catches made-up answers)
  B. Does each answer match the answer key?  (gives accuracy)
Writes a report to out/TX_report.md
"""
import json
import re
import sys
from pathlib import Path

STATE = sys.argv[1]


def clean(text):
    """Ignore spacing, line breaks, curly quotes, and capitals when comparing text."""
    text = (text or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


law = {f.stem: clean(f.read_text(encoding="utf-8")) for f in Path("raw", STATE).glob("*.txt")}
key = json.loads(Path(f"answer_key/{STATE}.json").read_text(encoding="utf-8"))["fields"]
pred = json.loads(Path(f"out/{STATE}.json").read_text(encoding="utf-8"))["fields"]
report = [f"# {STATE} extraction report", ""]


def quote_is_real(f):
    return bool(f.get("quote")) and clean(f["quote"]) in law.get(f.get("section"), "")


# A. Quote check, for the answer key and for the script
print("A. Does every quote really appear in the law?\n")
report += ["## A. Quote check", "", "| Field | Answer key | Script |", "|---|---|---|"]
thrown_out = 0
for name in key:
    k_ok = quote_is_real(key[name])
    p = pred.get(name, {})
    if p.get("value") is None:
        p_status = "no answer"
    elif quote_is_real(p):
        p_status = "ok"
    else:
        p_status = "NOT FOUND, answer thrown out"
        p["value"] = None
        thrown_out += 1
    print(f"  {name:21} key: {'ok' if k_ok else 'NOT FOUND (fix the answer key!)':32} script: {p_status}")
    report.append(f"| {name} | {'ok' if k_ok else 'NOT FOUND'} | {p_status} |")

# B. Score against the answer key
print("\nB. Does each answer match the answer key?\n")
report += ["", "## B. Accuracy", "", "| Field | Result | Script said | Answer key says |", "|---|---|---|---|"]
correct, fails = 0, []
for name, k in key.items():
    p = pred.get(name, {"value": None, "section": None})
    if name == "exemptions":
        got, want = set(p["value"] or []), set(k["value"] or [])
        ok = got == want
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
Path(f"out/{STATE}_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
print(f"\nReport saved to out/{STATE}_report.md")