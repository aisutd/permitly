# Extraction results: progress log

Each row is one stage of the project in order. Scores are field-level accuracy against hand-filled answer keys (10 fields per state). "Unseen" means the method had not been adjusted using that state.

## Progress over time

| Stage | What changed | TX | KY | FL | Unseen-state accuracy | Answers thrown out (bad quotes) |
|---|---|---|---|---|---|---|
| 1. Regex v1 | Rules written while reading Texas law | 9/10 | — | — | — | 0 |
| 2. First new state | Ran regex v1 on Kentucky, no changes | 9/10 | **6/10 (unseen)** | — | 60% | 1 |
| 3. Regex fixed | Added rules for Kentucky wording | 9/10 | 10/10 (no longer unseen) | — | — | 0 |
| 4. Second new state | Ran fixed regex on Florida, no changes | 9/10 | 10/10 | **1/10 (unseen)** | 10% | 1 |
| 5. LLM v1 | Replaced regex with an LLM (gpt-oss-120b on Groq), same quote check | 5/10 | **7/10 (unseen)** | **9/10 (unseen)** | **80%** | 7 |
| 6. LLM v2 | Stricter quote rules, one retry for missing or inexact quotes, tag definitions | 7/10 | 9/10 (no longer unseen) | 8/10 (no longer unseen) | Test on CA, NY, IL, WA | 0 |

**Headline:** on states the method had not seen, accuracy rose from **35% with regex** (7/20, KY + FL first runs) to **80% with the LLM** (16/20).

## What each stage taught us
1. **Regex v1 → Kentucky:** rules built on one state's wording miss other states' phrasing ("no person shall engage" vs "may not engage").
2. **Regex fixed → Florida:** fixing rules for one state does not carry over; Florida dropped to 10%. Regex also picked a real but wrong number ($20,000 branch-fee cap instead of the $375 application fee), and only the answer key caught it.
3. **LLM v1:** handled new wording far better, but shortened 7 quotes (dropped (A)/(B) markers, skipped words, used "..."). None were invented. The strict quote check rejected all 7, so no unverifiable answer entered the database.
4. **LLM v2:** targets the quote-editing problem without loosening the check.

## Fields that fail most
1. Exemptions: labels and lists spread across sections
2. Structure fields (bond_structure, net_worth_structure): no single sentence states them, so quotes get edited
3. Wording-based fields for regex: license_required, decision_days
4. Fees, when a section lists several dollar amounts (regex)

## Known judgment calls
- Florida net worth ($100,000 plus $10,000 per location, capped at $2 million) is arguably "formula" or "tiered". The answer key says formula and was not changed to match any model.