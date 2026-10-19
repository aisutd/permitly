"""Step 1: read a state's law files and pull out the answers with simple rules (regex).

Run:  python extract.py TX
Reads:  raw/TX/*.txt   (line 1 = section title, rest = law text)
Writes: out/TX.json    (same format as answer_key/TX.json)
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

STATE = sys.argv[1]

MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)(?:\s*(million|billion))?", re.I)
DAYS = re.compile(r"(\d+)(?:st|nd|rd|th)?\s+day", re.I)

# Words that identify each exemption. Checked top to bottom; the first match wins,
# so more specific phrases come before general ones.
EXEMPTION_WORDS = [
    ("governmental benefits", "ebt_contractor"),
    ("postal service", "postal_service"),
    ("united states", "government"),
    ("governmental agency", "government"),
    ("county, city", "government"),
    ("depository", "bank"),
    ("bank", "bank"),
    ("credit union", "bank"),
    ("trust company", "trust_company"),
    ("attorney", "attorney_or_title"),
    ("title company", "attorney_or_title"),
    ("board of trade", "board_of_trade"),
    ("futures commission", "futures_merchant"),
    ("broker-dealer", "broker_dealer"),
    ("employed by", "employee"),
    ("service provider", "service_provider_to_bank"),
    ("payroll", "payroll_processor"),
    ("agent of a payee", "agent_of_payee"),
    ("agent of the payee", "agent_of_payee"),
    ("intermediary", "payment_intermediary"),
    ("payment system", "payment_system"),
    ("regulation or order", "regulator_exempts"),
    ("rule or order", "regulator_exempts"),
]


def to_dollars(m):
    n = float(m.group(1).replace(",", ""))
    mult = {"million": 1e6, "billion": 1e9}.get((m.group(2) or "").lower(), 1)
    return int(n * mult)


def load_sections():
    sections = {}
    for f in Path("raw", STATE).glob("*.txt"):
        lines = f.read_text(encoding="utf-8").splitlines()
        sections[f.stem] = {"title": lines[0].strip(), "text": " ".join(lines[1:])}
    return sections


def pieces(text):
    """Split law text into short pieces at . ; : so each quote is a real stretch of the text."""
    return [p.strip() for p in re.split(r"(?<=[.;:])\s+", text) if p.strip()]


def find(sections, title_word):
    for sid, s in sections.items():
        if title_word in s["title"].lower():
            return sid, s
    return None, None


def answer(value, section, quote, note=""):
    return {"value": value, "section": section, "quote": quote, "note": note}


NOT_FOUND = answer(None, None, None, "not found")


def license_required(sections):
    sid, s = find(sections, "license required")
    if not s:
        return NOT_FOUND
    for p in pieces(s["text"]):
        if re.search(r"may not engage", p, re.I):
            return answer(True, sid, re.sub(r"^.*?\(a\)\s+", "", p))
    return answer(None, sid, None, "no 'may not engage' sentence")


def bond(sections):
    sid, s = find(sections, "security")
    if not s:
        return NOT_FOUND, NOT_FOUND, NOT_FOUND
    text = s["text"]
    tiers = len(re.findall(r"for a licensee with", text, re.I))
    if tiers >= 2:
        structure = "tiered"
    elif "greater of" in text.lower():
        structure = "formula"
    else:
        structure = "flat"
    structure_quote = next((p for p in pieces(text) if "greater of" in p.lower() or "for a licensee" in p.lower()), pieces(text)[0])

    amounts = [(p, to_dollars(m)) for p in pieces(text) for m in MONEY.finditer(p)]
    if not amounts:
        return answer(structure, sid, structure_quote), answer(None, sid, None, "no amount"), answer(None, sid, None, "no amount")
    low_piece, low = min(amounts, key=lambda a: a[1])
    m = re.search(r"(?:maximum|not to exceed|not more than)[^$]{0,40}\$\s?[\d,]+(?:\s*(?:million|billion))?", text, re.I)
    if m:
        high = answer(to_dollars(MONEY.search(m.group(0))), sid, m.group(0))
    else:
        high = answer(None, sid, None, "no cap found")
    return answer(structure, sid, structure_quote), answer(low, sid, low_piece), high


def net_worth(sections):
    sid, s = find(sections, "net worth")
    if not s:
        return NOT_FOUND, NOT_FOUND
    text = s["text"]
    tiers = len(re.findall(r"for a licensee with total assets", text, re.I))
    structure = "tiered" if tiers >= 2 else ("formula" if "greater of" in text.lower() else "flat")
    structure_quote = pieces(text)[0]
    structure_quote = re.sub(r"^.*?\(a\)\s+", "", structure_quote)
    for p in pieces(text):
        m = MONEY.search(p)
        if m and not m.group(2):          # first plain dollar figure, not "$100 million"
            return answer(structure, sid, structure_quote), answer(to_dollars(m), sid, p)
    return answer(structure, sid, structure_quote), answer(None, sid, None, "no amount")


def fee(sections, pattern):
    for sid, s in sections.items():
        for p in pieces(s["text"]):
            if re.search(pattern, p, re.I):
                m = MONEY.search(p)
                if m:
                    return answer(to_dollars(m), sid, p)
    return NOT_FOUND


def decision_days(sections):
    for sid, s in sections.items():
        for p in pieces(s["text"]):
            m = DAYS.search(p)
            if m and re.search(r"approve or deny", p, re.I):
                return answer(int(m.group(1)), sid, p)
    return NOT_FOUND


def exemptions(sections):
    sid, s = find(sections, "exempt")
    if not s:
        return NOT_FOUND
    found = []
    for num, body in re.findall(r"\((\d+)\)\s+(.+?)(?=\s\(\d+\)\s|$)", s["text"]):
        tag = next((t for w, t in EXEMPTION_WORDS if w in body.lower()), "UNTAGGED")
        found.append(f"{tag}:{sid}({num})")
    lead = re.search(r"this chapter does not apply to:", s["text"], re.I)
    return answer(found, sid, lead.group(0) if lead else None)


sections = load_sections()
b_structure, b_min, b_max = bond(sections)
nw_structure, nw_min = net_worth(sections)

record = {
    "record_info": {"state": STATE, "license_type": "money_transmission", "made_by": "extract.py", "date": str(date.today())},
    "fields": {
        "license_required": license_required(sections),
        "bond_structure": b_structure,
        "bond_min_usd": b_min,
        "bond_max_usd": b_max,
        "net_worth_structure": nw_structure,
        "net_worth_min_usd": nw_min,
        "application_fee_usd": fee(sections, r"application fee"),
        "renewal_fee_usd": fee(sections, r"renewal fee|annual license fee of"),
        "decision_days": decision_days(sections),
        "exemptions": exemptions(sections),
    },
}

Path("out").mkdir(exist_ok=True)
Path(f"out/{STATE}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(f"Saved out/{STATE}.json\n")
for name, f in record["fields"].items():
    shown = f"{len(f['value'])} items" if isinstance(f["value"], list) else f["value"]
    print(f"  {name:21} {str(shown):12} section {f['section']}   {f['note']}")