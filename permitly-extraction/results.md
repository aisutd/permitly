# Extraction results

| State | Role | Accuracy | Notes |
|---|---|---|---|
| TX | Development (rules built on it) | 9/10 = 90% | Misses 2 exemptions in 152.101 (lettered subsections) |
| KY | Unseen test, before fixes | 6/10 = 60% | Failed: license_required, bond_structure, decision_days, exemptions |
| KY | After fixes | 10/10 = 100% | Not an unseen test anymore |

Quote check: every quote verified in both states. The one KY answer with no real quote (exemptions, before fixes) was thrown out, not saved.

Fields that fail most on a new state: exemptions, then wording-based fields (license_required, bond_structure, decision_days). Dollar amounts were right every time.