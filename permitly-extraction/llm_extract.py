"""Step 1b: ask an LLM (Groq) to fill the same 10 fields as extract.py.

Run:   python llm_extract.py FL
Needs: export GROQ_API_KEY="your key"   (in the terminal first)
Writes out/FL.json so check.py can grade it.
The regex version is kept as out/FL_regex.json and out/FL_report_regex.md.
"""
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

STATE = sys.argv[1]
MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
KEY = os.environ.get("GROQ_API_KEY")
if not KEY:
    sys.exit('No key found. First run:  export GROQ_API_KEY="your key"')

FIELDS = ["license_required", "bond_structure", "bond_min_usd", "bond_max_usd",
          "net_worth_structure", "net_worth_min_usd", "application_fee_usd",
          "renewal_fee_usd", "decision_days", "exemptions"]
NUMBER_FIELDS = {"bond_min_usd", "bond_max_usd", "net_worth_min_usd",
                 "application_fee_usd", "renewal_fee_usd", "decision_days"}

tax = json.loads(Path("taxonomy.json").read_text(encoding="utf-8"))
TAGS = list(tax["exemptions"])

# The law text, one block per section. The section id is the file name.
law = "\n\n".join(f"=== SECTION {f.stem} ===\n{f.read_text(encoding='utf-8')}"
                  for f in sorted(Path("raw", STATE).glob("*.txt")))

SYSTEM = (
    "You extract money transmitter licensing requirements from US state law. "
    "Use ONLY the law text provided. Never use outside knowledge. "
    "Every quote must be copied word for word from the text, 5 to 40 words long. "
    "If the text does not state a value, set value and quote to null. "
    "Respond with JSON only."
)

PROMPT = f"""Fill these 10 fields for this state's money transmitter license.
For each field return {{"value": ..., "section": "<id from the === SECTION === header>", "quote": "<exact words from that section>"}}.

license_required: true if the law requires a license to engage in money transmission.
bond_structure: one of "flat" (one fixed amount), "formula" (computed, such as the greater of X or Y percent), "tiered" (different amounts for different categories of licensee), "set_by_regulator" (the regulator or a rule sets the amount, possibly within limits).
bond_min_usd: the lowest bond amount stated, as a number.
bond_max_usd: the highest bond amount or cap stated, as a number, or null.
net_worth_structure: same choices as bond_structure.
net_worth_min_usd: the minimum net worth, as a number.
application_fee_usd: the application fee for the main money transmitter license, as a number. If several fees are listed, choose the one for the main license, not branches, locations, or caps.
renewal_fee_usd: the renewal fee for the main money transmitter license, as a number, or null.
decision_days: the number of days the regulator has to approve or deny a complete application, or null.
exemptions: a list of strings "tag:SECTION(PARAGRAPH)", for example "bank:152.004(7)" or "authorized_delegate:152.101(c)(1)", one for every paragraph that exempts a type of person or business, in any section. Use only these tags: {", ".join(TAGS)}. For this field, the quote is the sentence that introduces the main list of exemptions.

Return: {{"fields": {{"license_required": {{...}}, "bond_structure": {{...}}, ...all 10...}}}}

LAW TEXT:
{law}"""


def call_llm():
    body = json.dumps({
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": PROMPT}],
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "User-Agent": "permitly-extraction/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Groq error {e.code}: {e.read().decode()[:500]}")
    return json.loads(data["choices"][0]["message"]["content"])


def to_number(v):
    if v is None or isinstance(v, (int, float)):
        return v
    try:
        return int(float(str(v).replace("$", "").replace(",", "").strip()))
    except ValueError:
        return None


# Keep the regex results before overwriting out/STATE.json
out = Path(f"out/{STATE}.json")
if out.exists() and json.loads(out.read_text())["record_info"].get("made_by") == "extract.py":
    shutil.copy(out, f"out/{STATE}_regex.json")
    rep = Path(f"out/{STATE}_report.md")
    if rep.exists():
        shutil.copy(rep, f"out/{STATE}_report_regex.md")

result = call_llm()
Path("out").mkdir(exist_ok=True)
Path(f"out/{STATE}_llm_raw.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

got = result.get("fields", result)
fields = {}
for name in FIELDS:
    f = got.get(name) or {}
    value = f.get("value")
    if name in NUMBER_FIELDS:
        value = to_number(value)
    fields[name] = {"value": value, "section": f.get("section"), "quote": f.get("quote"),
                    "note": "llm" if value is not None else "llm: not found"}

record = {"record_info": {"state": STATE, "license_type": "money_transmission",
                          "made_by": f"llm_extract.py ({MODEL})", "date": str(date.today())},
          "fields": fields}
out.write_text(json.dumps(record, indent=2), encoding="utf-8")

print(f"Saved out/{STATE}.json (LLM: {MODEL})\n")
for name, f in fields.items():
    shown = f"{len(f['value'])} items" if isinstance(f["value"], list) else f["value"]
    print(f"  {name:21} {str(shown):16} section {f['section']}")