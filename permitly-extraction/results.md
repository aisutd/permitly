# Extraction results: progress log

Each row is one stage of the project in order. Scores are field-level accuracy against hand-filled answer keys (10 fields per state). "Unseen" means the method had not been adjusted using that state.

## Progress over time

| Stage | What changed | TX | KY | FL | DE | Answers thrown out (bad quotes) |
|---|---|---|---|---|---|---|
| 1. Regex v1 | Rules written while reading Texas law | 9/10 | — | — | — | 0 |
| 2. First new state | Ran regex v1 on Kentucky, no changes | 9/10 | **6/10 (unseen)** | — | — | 1 |
| 3. Regex fixed | Added rules for Kentucky wording | 9/10 | 10/10 (no longer unseen) | — | — | 0 |
| 4. Second new state | Ran fixed regex on Florida, no changes | 9/10 | 10/10 | **1/10 (unseen)** | — | 1 |
| 5. LLM v1 | Replaced regex with an LLM (gpt-oss-120b on Groq), same quote check | 5/10 | **7/10 (unseen)** | **9/10 (unseen)** | — | 7 |
| 6. LLM v2 | Stricter quote rules, one retry for missing or inexact quotes, tag definitions | 7/10 | 9/10 | 8/10 | — | 0 |
| 7. Third new state | Ran regex and LLM v2 on Delaware, no changes (law replaced July 2026, SB 18) | — | — | — | **Regex 4/10, LLM 7/10 (unseen)** | Regex 1, LLM 0 |
| 8. LLM v3 | Approve-or-deny-only deadline rule, full citation paths, clearer tiered/formula definition, keeps cents, smaller retry | 9/10 | 9/10 | 10/10 | 9/10 | 0 (4 fixed on retry in DE) |
| 9. Fourth new state | Ran regex and LLM v3 on California, no changes | — | — | — | CA: Regex 4/10, LLM v3 8/10 (unseen) | Regex 1, LLM 0 (3 fixed on retry) |
STAGE 10: LLM v4 (exemption fixes)
* Changes: agents of licensees are often exempted in the license section; one tag per paragraph; exemptions-only request if exemptions are still missing; stricter exemption format check.
* Result: TX 9, KY 9, FL 10, DE 10, CA 8 = 46/50 (v3: 45/50). 0 fake quotes.
* The exemptions-only request fired once (CA) and fixed exemptions to 13 of 14.
* Remaining misses: citation depth (TX, KY), tag choice (CA), KY agent exemption, CA bond tiered vs formula (key under review).
* Not an unseen test: these states shaped v4.
STAGE 11: Washington blind test (v4, no code changes)
* Regex 2/10. LLM v4 7/10. 0 fake quotes.
* LLM misses: bond tiered/formula vs set_by_regulator (defensible), renewal null vs 1000 (defensible: WA has no renewal, only an annual assessment), exemptions 12 of 19.
* Exemption misses repeat known patterns: citation depth ((9) not split into (a)-(c); 030(b) not 030(1)(b)) and tag choice ((8), (11), (16)).
* v4 agent rule worked: the 030 authorized delegate exemption was found.
* Unseen totals: regex 17/50 = 34%; LLM 38/50 = 76%.
* For key review: WA bond structure, WA renewal fee, CA bond structure.

**Headline (unseen states only, first run on each):**
- Regex: **11/30 = 37%** (KY 6, FL 1, DE 4)
- LLM: **23/30 = 77%** (KY 7 and FL 9 with v1, DE 7 with v2)
- LLM v3 on all four development states: **37/40 = 92.5%**, zero rejected quotes (not an unseen score)

## What each stage taught us
1. **Regex v1 → Kentucky:** rules built on one state's wording miss other states' phrasing ("no person shall engage" vs "may not engage").
2. **Regex fixed → Florida:** fixing rules for one state does not carry over; Florida dropped to 10%. Regex also picked a real but wrong number ($20,000 branch-fee cap instead of the $375 application fee), and only the answer key caught it.
3. **LLM v1:** handled new wording far better, but shortened 7 quotes (dropped (A)/(B) markers, skipped words, used "..."). None were invented. The strict quote check rejected all 7, so no unverifiable answer entered the database.
4. **LLM v2:** zero inexact quotes across all three states (v1: 7), without loosening the check.
5. **Delaware (unseen):** LLM v2 scored 7/10. It answered "30 days" by citing a real sentence about a denial-notice deadline, not an approval deadline: a real quote backing the wrong answer, caught only by the answer key. It tagged all 14 exemption paragraphs correctly but wrote 2305(1) instead of 2305(a)(1), which strict scoring counts as wrong.
6. **LLM v3:** fixed decision days, citation format, and the tiered vs formula labels. The retry was also made smaller after Texas exceeded Groq's free-tier request size.
7. **Remaining misses are all exemptions:** long lists (Texas, 18 items, left out entirely) or exemptions split across the license and exemptions sections (Kentucky and Delaware delegate exemptions).
8. **California (unseen, v3):** 8/10, zero rejected quotes. The v3 fixes held on new law (no invented deadline, correct tiered net worth, correct citations). Misses: bond structure "tiered" vs key "formula" (California sets different bond rules by activity, so the model's answer is defensible and flagged for key review), and the agent exemption in the license section, now missed in KY, DE, and CA.

## Fields that fail most
1. Exemptions: long lists and exemptions spread across sections (still failing in v3)
2. Structure fields (bond_structure, net_worth_structure): fixed in v3 with clearer definitions
3. Decision days: a real number with the wrong meaning (Delaware notice deadline); fixed in v3
4. Wording-based fields for regex: license_required, decision_days
5. Fees, when a section lists several dollar amounts (regex)

## Known judgment calls
- Florida net worth ($100,000 plus $10,000 per location, capped at $2 million) is "formula": one rule for everyone.
- Texas and Delaware net worth (greater of $100,000 or 3% / 2% / 0.5% by asset bracket) are "tiered": different rules by bracket.
- Delaware application fee is the $172.50 investigation fee paid at application, not the $230 license fee paid on approval.
- Delaware decision days is null: the law sets no approve-or-deny deadline.
- Answer keys were never changed to match any model.

## Reliability notes
- The same script can give different answers on repeat runs (seen on Delaware). Final scores should average 3 runs per state.
- Groq's free tier allows 8,000 tokens per minute; the script waits and retries automatically.

## Next
1. California: unseen test of v3, no changes.
2. v4: a separate, smaller request for exemptions only, sending just the license and exemption sections.
3. New York, Illinois, Washington as further unseen tests.
4. Teammate review of all answer keys.
5. Cornerstone vendor comparison (Delaware should show the vendor summary is out of date).
6. Combined database file for the team.