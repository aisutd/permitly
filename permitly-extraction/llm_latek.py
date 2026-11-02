"""Step 1b (v2): ask an LLM on Groq to fill the same 10 fields as extract.py.

v2 changes:
- Stricter quote rules: one continuous stretch, no "...", keep markers like (A).
- Checks its own quotes (and missing fields); asks the model once to fix them.
- Short definitions for each exemption tag.
- Waits and retries automatically on Groq's free-tier rate limit.

Run:   python llm_extract.py FL
Needs: export GROQ_API_KEY="your key"  and  export GROQ_MODEL="openai/gpt-oss-120b"
Writes out/FL.json (graded by check.py) and out/FL_llm_log.json (quote stats).
"""
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

STATE = sys.argv[1]
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
KEY = os.environ.get("GROQ_API_KEY")
if not KEY:
    sys.exit('No key found. First run:  export GROQ_API_KEY="your key"')

FIELDS = ["license_required", "bond_structure", "bond_min_usd", "bond_max_usd",
          "net_worth_structure", "net_worth_min_usd", "application_fee_usd",
          "renewal_fee_usd", "decision_days", "exemptions"]
NUMBER_FIELDS = {"bond_min_usd", "bond_max_usd", "net_worth_min_usd",
                 "application_fee_usd", "renewal_fee_usd", "decision_days"}

TAG_HELP = {
    "bank": "banks, credit unions, savings associations, other depository financial institutions",
    "trust_company": "trust companies",
    "government": "the United States, a state, or their agencies and political subdivisions",
    "postal_service": "the US Postal Service or its contractors",
    "agent_of_payee": "a person collecting money on behalf of a payee or a seller of goods or services",
    "payment_system": "operators of payment, clearing, or settlement systems",
    "payment_intermediary": "intermediaries in payments between businesses",
    "authorized_delegate": "agents or authorized delegates of a licensee",
    "employee": "employees of a licensee or of an exempt person",
    "service_provider_to_bank": "a service provider acting on behalf of an exempt bank or financial institution",
    "broker_dealer": "registered securities broker-dealers",
    "futures_merchant": "futures commission merchants",
    "board_of_trade": "boards of trade or exchanges and their clearing organizations",
    "attorney_or_title": "attorneys, title companies, or escrow agents",
    "ebt_contractor": "contractors delivering government benefits electronically",
    "payroll_processor": "payroll processors",
    "regulator_exempts": "persons the regulator exempts by rule or order",
    "incidental_business": "money transmission that is only incidental to another business",
    "blockchain_software": "software developers or node operators on a blockchain",
    "other": "fits none of the other tags",
}

tax = json.loads(Path("taxonomy.json").read_text(encoding="utf-8"))
TAGS = list(tax["exemptions"])
TAG_LINES = "\n".join(f"- {t}: {TAG_HELP.get(t, '')}" for t in TAGS)

SECTIONS = {f.stem: f.read_text(encoding="utf-8") for f in sorted(Path("raw", STATE).glob("*.txt"))}
law = "\n\n".join(f"=== SECTION {sid} ===\n{text}" for sid, text in SECTIONS.items())

SYSTEM = (
    "You extract money transmitter licensing requirements from US state law. "
    "Use ONLY the law text provided. Never use outside knowledge. "
    "QUOTE RULES: each quote must be ONE continuous stretch copied character for character "
    "from the cited section, 5 to 40 words. Never use '...'. Never skip, add, reorder, or "
    "change words. Keep markers like (A), (1), or (a) exactly if they fall inside the stretch. "
    "A short exact quote is better than a long edited one. "
    "If the text does not state a value, set value and quote to null. Respond with JSON only."
)

PROMPT = f"""Fill these 10 fields for this state's money transmitter license.
For each field return {{"value": ..., "section": "<id from the === SECTION === header>", "quote": "<exact continuous words from that section>"}}.

license_required: true if the law requires a license to engage in money transmission.
bond_structure: one of "flat" (one fixed amount for everyone), "formula" (one rule for everyone that computes the amount, such as the greater of X or Y percent, or a base plus an amount per location), "tiered" (the law sorts licensees into categories, such as by assets or net worth, and gives each category its own amount or rule, even if each rule is a formula), "set_by_regulator" (the regulator or a rule sets the amount, possibly within limits).bond_min_usd: the lowest bond amount stated, as a number.
bond_max_usd: the highest bond amount or cap stated, as a number, or null.
net_worth_structure: same choices as bond_structure.
net_worth_min_usd: the minimum net worth, as a number.
application_fee_usd: the application fee for the main money transmitter license, as a number. If several fees are listed, choose the one for the main license, not branches, locations, or caps.
renewal_fee_usd: the renewal fee for the main money transmitter license, as a number, or null.
decision_days: the number of days the regulator has to approve or deny a complete application, or null.
exemptions: value is a list of strings "tag:SECTION(PARAGRAPH)", for example "bank:100.10(4)" or "authorized_delegate:100.20(c)(1)", one for every paragraph that exempts a type of person or business, in any section. Return it in the same {{"value": [...], "section": ..., "quote": ...}} form; the quote is the sentence that introduces the main list of exemptions. Never leave this field out.

Exemption tags (use only these):
{TAG_LINES}

Return: {{"fields": {{"license_required": {{...}}, "bond_structure": {{...}}, ...all 10...}}}}

LAW TEXT:
{law}"""


def norm(s):
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def as_field(x):
    """The model sometimes returns a bare value or list instead of {"value": ...}."""
    if isinstance(x, dict):
        return x
    return {"value": x, "section": None, "quote": None}


def quote_ok(f):
    if f.get("value") is None:
        return True
    q, sec = f.get("quote"), f.get("section")
    return bool(q) and sec in SECTIONS and norm(q) in norm(SECTIONS[sec])


def call_llm(messages):
    body = json.dumps({"model": MODEL, "temperature": 0,
                       "response_format": {"type": "json_object"},
                       "messages": messages}).encode()
    for attempt in range(5):
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                     "User-Agent": "permitly-extraction/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            return json.loads(data["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:500]
            if e.code == 429 and attempt < 4:
                print("  Groq rate limit reached, waiting 30 seconds...")
                time.sleep(30)
                continue
            sys.exit(f"Groq error {e.code}: {msg}")


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

messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": PROMPT}]
first = call_llm(messages)
got = {k: as_field(v) for k, v in first.get("fields", first).items()}

first_bad = [n for n in FIELDS if n not in got or not quote_ok(got[n])]
fixed = []
if first_bad:
    print(f"{len(first_bad)} field(s) missing or not quoted word for word: {', '.join(first_bad)}")
    print("Asking the model to fix them once...")
    lines = "\n".join(
        f"- {n}: MISSING from your answer" if n not in got
        else f"- {n}: {got[n].get('quote')!r} (section {got[n].get('section')})"
        for n in first_bad)
    messages += [
        {"role": "assistant", "content": json.dumps(first)},
        {"role": "user", "content":
            "These fields are missing, or their quotes do not appear word for word in the cited section:\n"
            + lines +
            "\nFor these fields only, answer again with a quote copied as ONE continuous stretch "
            "of the section text: no '...', no skipped or changed words, keep markers like (A). "
            "If no such stretch supports the value, set value and quote to null. "
            'Return {"fields": {...only these fields...}}'}]
    second = call_llm(messages)
    redo = {k: as_field(v) for k, v in second.get("fields", second).items()}
    for n in first_bad:
        if n in redo:
            got[n] = redo[n]
            if quote_ok(got[n]):
                fixed.append(n)

still_bad = [n for n in FIELDS if n not in got or not quote_ok(got[n])]

fields = {}
for name in FIELDS:
    f = got.get(name) or {}
    value = f.get("value")
    if name in NUMBER_FIELDS:
        value = to_number(value)
    note = "llm"
    if name in fixed:
        note = "llm (fixed on retry)"
    elif name in still_bad:
        note = "llm (missing or quote not exact)"
    elif value is None:
        note = "llm: not found"
    fields[name] = {"value": value, "section": f.get("section"), "quote": f.get("quote"), "note": note}

record = {"record_info": {"state": STATE, "license_type": "money_transmission",
                          "made_by": f"llm_extract.py v2 ({MODEL})", "date": str(date.today())},
          "fields": fields}
Path("out").mkdir(exist_ok=True)
out.write_text(json.dumps(record, indent=2), encoding="utf-8")
Path(f"out/{STATE}_llm_raw.json").write_text(json.dumps(got, indent=2), encoding="utf-8")
Path(f"out/{STATE}_llm_log.json").write_text(json.dumps(
    {"model": MODEL, "version": "v2", "first_pass_bad_or_missing": first_bad,
     "fixed_on_retry": fixed, "still_bad": still_bad}, indent=2), encoding="utf-8")

print(f"\nSaved out/{STATE}.json (LLM v2: {MODEL})")
print(f"Fields: {len(first_bad)} missing or inexact on first try, {len(fixed)} fixed on retry, {len(still_bad)} still bad\n")
for name, f in fields.items():
    shown = f"{len(f['value'])} items" if isinstance(f["value"], list) else f["value"]
    print(f"  {name:21} {str(shown):16} section {f['section']}   {f['note']}")