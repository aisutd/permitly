"""LLM extractor, v4 (current). Older versions: llm_latek_v1.py, llm_latek_v2.py, llm_latek_v3.py.

Asks an LLM on Groq to fill the same 10 fields as latek.py (regex).

v2 (from v1): stricter quote rules; self-check with one retry; tag definitions; rate-limit waits.
v3 (from v2, Delaware): approve-or-deny-only deadline rule; full citation paths; clearer
    tiered vs formula; keeps cents; smaller retry; retries when Groq returns an empty answer.
v4 (from v3, exemption misses in TX, KY, FL, DE, CA):
- Agents of licensees are often exempted in the license section, not the exemptions list.
- One tag per paragraph (the main type of entity it exempts).
- If exemptions are still missing after the retry, ask for exemptions alone, sending only
  the exemption and license sections (keeps the request small).

Run:   python llm_latek.py FL
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

VERSION = "v4"
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

EX_RULES = f"""exemptions: value is a list of strings "tag:SECTION(PATH)", for example "bank:100.10(4)" or "authorized_delegate:100.20(c)(1)", one for every paragraph that exempts a type of person or business, in any section. Write PATH as the full chain of subsection markers exactly as printed: if paragraph (1) sits under subsection (a), write 100.10(a)(1), not 100.10(1). Use exactly ONE tag per paragraph: the main type of person or business it exempts, even if the paragraph names several. Check the license-required section too: wording such as "or is an agent of a licensee", "an authorized delegate of a licensee", or "unless ... an agent of a person licensed" exempts agents, so add "authorized_delegate" with that section's path. Return it in the same {{"value": [...], "section": ..., "quote": ...}} form; the quote is the sentence that introduces the main list of exemptions. Never leave this field out.

Exemption tags (use only these):
{TAG_LINES}"""

PROMPT = f"""Fill these 10 fields for this state's money transmitter license.
For each field return {{"value": ..., "section": "<id from the === SECTION === header>", "quote": "<exact continuous words from that section>"}}.

license_required: true if the law requires a license to engage in money transmission.
bond_structure: one of "flat" (one fixed amount for everyone), "formula" (one rule for everyone that computes the amount, such as the greater of X or Y percent, or a base plus an amount per location), "tiered" (the law sorts licensees into categories or brackets, such as by assets or net worth, and gives each its own amount or rule, even if each rule is a formula), "set_by_regulator" (the regulator or a rule sets the amount, possibly within limits).
bond_min_usd: the lowest bond amount stated, as a number.
bond_max_usd: the highest bond amount or cap stated, as a number, or null.
net_worth_structure: same choices as bond_structure. Use "tiered" when the law sets different amounts or percentages for different brackets or categories of licensee (for example 3% of the first $100 million of assets and 2% above that). Use "formula" when one rule applies to everyone (for example $100,000 plus $10,000 per location).
net_worth_min_usd: the minimum net worth, as a number.
application_fee_usd: the application fee for the main money transmitter license, as a number. If several fees are listed, choose the one for the main license, not branches, locations, or caps.
renewal_fee_usd: the renewal fee for the main money transmitter license, as a number, or null.
decision_days: the number of days the regulator has to approve or deny a complete application, or null. Count only a deadline for the approve-or-deny decision itself. Do not use deadlines for sending notices, completeness reviews, hearings, appeals, or payments. If the law sets no approve-or-deny deadline, return null.
{EX_RULES}

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
    """Ask Groq. Waits on rate limits. If the model returns an empty or invalid answer,
    tries again with less reasoning, then without Groq's JSON mode (we read the JSON ourselves)."""
    settings = [
        {"response_format": {"type": "json_object"}},
        {"response_format": {"type": "json_object"}, "reasoning_effort": "low"},
        {"reasoning_effort": "low"},
    ]
    for extra in settings:
        body = json.dumps({"model": MODEL, "temperature": 0, "messages": messages, **extra}).encode()
        for attempt in range(5):
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                         "User-Agent": "permitly-extraction/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.loads(r.read())
                text = data["choices"][0]["message"]["content"] or ""
                start, end = text.find("{"), text.rfind("}")
                if start != -1 and end > start:
                    return json.loads(text[start:end + 1])
                print("  Empty answer from the model, trying again with different settings...")
                break
            except json.JSONDecodeError:
                print("  Answer was not valid JSON, trying again with different settings...")
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode()[:500]
                if e.code == 429 and attempt < 4:
                    print("  Groq rate limit reached, waiting 30 seconds...")
                    time.sleep(30)
                    continue
                if e.code == 400 and "json_validate_failed" in msg:
                    print("  Model returned an empty or invalid answer, trying again with different settings...")
                    break
                sys.exit(f"Groq error {e.code}: {msg}")
    sys.exit("The model did not return a usable answer after 3 tries.")


def to_number(v):
    """Turn "$172.50" or "172.5" into a number. Keeps cents; whole amounts stay whole."""
    if v is None or isinstance(v, (int, float)):
        return v
    try:
        n = float(str(v).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None
    return int(n) if n.is_integer() else n


def exemptions_ok(f):
    """Exemptions must be a list of "tag:SECTION(PATH)" strings, with a real quote."""
    v = f.get("value") if f else None
    return (isinstance(v, list) and len(v) > 0
            and all(isinstance(x, str) and ":" in x and "(" in x for x in v)
            and quote_ok(f))


# Keep the regex results before overwriting out/STATE.json
out = Path(f"out/{STATE}.json")
if out.exists() and json.loads(out.read_text())["record_info"].get("made_by") in ("extract.py", "latek.py"):
    shutil.copy(out, f"out/{STATE}_regex.json")
    rep = Path(f"out/{STATE}_report.md")
    if rep.exists():
        shutil.copy(rep, f"out/{STATE}_report_regex.md")

# 1. Ask for all 10 fields
messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": PROMPT}]
first = call_llm(messages)
got = {k: as_field(v) for k, v in first.get("fields", first).items()}

# 2. One retry for missing fields or inexact quotes
first_bad = [n for n in FIELDS if n not in got or not quote_ok(got[n])]
fixed = []
if first_bad:
    print(f"{len(first_bad)} field(s) missing or not quoted word for word: {', '.join(first_bad)}")
    print("Asking the model to fix them once...")
    lines = "\n".join(
        f"- {n}: MISSING from your answer" if n not in got
        else f"- {n}: {got[n].get('quote')!r} (section {got[n].get('section')})"
        for n in first_bad)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": PROMPT +
            "\n\nIMPORTANT: in an earlier attempt, these fields were missing or their quotes did not "
            "appear word for word in the cited section:\n" + lines +
            "\nAnswer ONLY these fields, with a quote copied as ONE continuous stretch of the section "
            "text: no '...', no skipped or changed words, keep markers like (A). "
            "If no such stretch supports the value, set value and quote to null. "
            'Return {"fields": {...only these fields...}}'}]
    second = call_llm(messages)
    redo = {k: as_field(v) for k, v in second.get("fields", second).items()}
    for n in first_bad:
        if n in redo:
            got[n] = redo[n]
            if quote_ok(got[n]):
                fixed.append(n)

# 3. v4: if exemptions are still missing, ask for them alone with only the relevant sections
exemptions_alone = False
if not exemptions_ok(got.get("exemptions")):
    keep = {sid: t for sid, t in SECTIONS.items()
            if re.search(r"exempt|does not apply|engage in the business of money transmission", t, re.I)}
    small_law = "\n\n".join(f"=== SECTION {sid} ===\n{t}" for sid, t in keep.items())
    print(f"Exemptions still missing: asking for them alone ({len(keep)} of {len(SECTIONS)} sections)...")
    ex_prompt = ("Fill only the exemptions field for this state's money transmitter license.\n"
                 + EX_RULES +
                 '\n\nReturn: {"fields": {"exemptions": {"value": [...], "section": "...", "quote": "..."}}}'
                 "\n\nLAW TEXT:\n" + small_law)
    ex = call_llm([{"role": "system", "content": SYSTEM}, {"role": "user", "content": ex_prompt}])
    exf = as_field(ex.get("fields", ex).get("exemptions"))
    if exemptions_ok(exf):
        got["exemptions"] = exf
        exemptions_alone = True
        if "exemptions" not in fixed:
            fixed.append("exemptions")

still_bad = [n for n in FIELDS if n not in got or not quote_ok(got[n])]

fields = {}
for name in FIELDS:
    f = got.get(name) or {}
    value = f.get("value")
    if name in NUMBER_FIELDS:
        value = to_number(value)
    if name == "exemptions" and isinstance(value, list):
        value = [x if isinstance(x, str) else f"{x.get('tag')}:{x.get('section')}" for x in value]
    note = "llm"
    if name == "exemptions" and exemptions_alone:
        note = "llm (fixed by exemptions-only request)"
    elif name in fixed:
        note = "llm (fixed on retry)"
    elif name in still_bad:
        note = "llm (missing or quote not exact)"
    elif value is None:
        note = "llm: not found"
    fields[name] = {"value": value, "section": f.get("section"), "quote": f.get("quote"), "note": note}

record = {"record_info": {"state": STATE, "license_type": "money_transmission",
                          "made_by": f"llm_latek.py {VERSION} ({MODEL})", "date": str(date.today())},
          "fields": fields}
Path("out").mkdir(exist_ok=True)
out.write_text(json.dumps(record, indent=2), encoding="utf-8")
Path(f"out/{STATE}_llm_raw.json").write_text(json.dumps(got, indent=2), encoding="utf-8")
Path(f"out/{STATE}_llm_log.json").write_text(json.dumps(
    {"model": MODEL, "version": VERSION, "first_pass_bad_or_missing": first_bad,
     "fixed_on_retry": fixed, "exemptions_alone": exemptions_alone, "still_bad": still_bad},
    indent=2), encoding="utf-8")

print(f"\nSaved out/{STATE}.json (LLM {VERSION}: {MODEL})")
print(f"Fields: {len(first_bad)} missing or inexact on first try, {len(fixed)} fixed, {len(still_bad)} still bad\n")
for name, f in fields.items():
    shown = f"{len(f['value'])} items" if isinstance(f["value"], list) else f["value"]
    print(f"  {name:21} {str(shown):16} section {f['section']}   {f['note']}")