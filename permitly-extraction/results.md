# Extraction results

| State | Role | Accuracy | Notes |
|---|---|---|---|
| TX | Development (rules built on it) | 9/10 = 90% | Misses 2 exemptions in 152.101 (lettered subsections) |
| KY | Unseen test, before fixes | 6/10 = 60% | Failed: license_required, bond_structure, decision_days, exemptions |
| KY | After fixes | 10/10 = 100% | Not an unseen test anymore |
| FL | Unseen test, regex only | 1/10 = 10% | Not found: license, bond x3, deadline. Exemptions thrown out (no quote). Fees wrong: picked $20,000 cap instead of $375 |

## Quote check
Every saved quote appears in the law. Answers with no real quote were thrown out instead of saved: KY exemptions (before fixes) and FL exemptions.

## Key finding
The quote check stops made-up quotes, but it does not stop the script from picking the wrong real number. In Florida, $20,000 is really in the law (a branch-fee cap), so the quote passed. Only the answer key caught that it was the wrong fee.

## Fields that fail most on unseen states
1. Exemptions (KY, FL)
2. Wording-based fields: license_required, bond_structure, decision_days (KY, FL)
3. Fees, when a section lists several dollar amounts (FL)

Regex rules do not carry over to new states. Next step: an LLM stage, with the same quote check, tested on unseen states.