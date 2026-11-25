# B10 — State requirements spot-check
Review date: 2026-11-25. Input: state_answer_keys JSON export from origin/arjun_backend. Five states selected: TX, CA, FL, IL, WA. This reviews seed records, not live database rows.

| State | Field(s) | Finding | Source |
|---|---|---|---|
| TX | license_required, bond structure/min/max, net worth structure/min | Match general requirements; net worth waiver possible | [Chapter 152](https://tcss.legis.texas.gov/resources/fi/htm/fi.152.htm) §§152.101, 152.351–352 |
| TX | application_fee, renewal_fee | $10,000 matches; null recurring fee appropriate for variable assessment, not zero | [7 TAC 33.27](https://www.law.cornell.edu/regulations/texas/7-Tex-Admin-Code-SS-33-27) |
| TX | decision_days, exemptions | Further section-by-section verification pending | Chapter 152 §§152.106, 152.004, 152.101 |
| CA | bond structure/min/max | Match for receiving money; separate cumulative security for payment instruments/stored value already noted | [§2037](https://law.justia.com/codes/california/code-fin/division-1-2/chapter-3/section-2037/) |
| CA | net worth structure/min | Match; discretionary waiver | [§2040](https://law.justia.com/codes/california/code-fin/division-1-2/chapter-3/section-2040/) |
| CA | application_fee, renewal_fee | Match base fees; additional branch fees apply | [DFPI fee schedule](https://dfpi.ca.gov/wp-content/uploads/2025/10/DFPI-ADM-510-Index-of-Fees_-Fines-and-Penalties-Rev.-10-25.pdf) |
| CA | decision_days | No numeric deadline in cited section; other laws not ruled out | [§2033](https://law.justia.com/codes/california/code-fin/division-1-2/chapter-3/section-2033/) |
| CA | license_required, exemptions | Pending; official code access returned 403 | §§2030, 2010 |
| FL | license_required, bond structure/min/max, net worth structure/min | Match; net worth increases with locations | [Chapter 560](https://www.flsenate.gov/Laws/Statutes/2026/Chapter560/All) §§560.125, 560.204, 560.209 |
| FL | application_fee, renewal_fee | Match base fees | [§560.143](https://m.flsenate.gov/Statutes/560.143) |
| FL | decision_days | 90 days supported by general licensing law, subject to exceptions and tolling; 2025 text reviewed | [§120.60](https://www.flsenate.gov/Laws/Statutes/2025/120.60) |
| FL | exemptions | Incomplete: authorized vendors exempt from licensure within scope under §560.203 | [Chapter 560](https://www.flsenate.gov/Laws/Statutes/2026/Chapter560/All) |
| IL | license_required, bond structure/min/max | Match; statutory cap may be exceeded in specified circumstances | [§5-1](https://www.ilga.gov/legislation/ILCS/details?ActID=4549&SeqEnd=2500000&SeqStart=1500000), [§10-2](https://ilga.gov/documents/legislation/ilcs/documents/020506580K10-2.htm) |
| IL | net worth structure/min | Match; discretionary waiver possible | [§10-1](https://www.ilga.gov/legislation/ILCS/details?ActID=4549&SeqEnd=4650000&SeqStart=4287500) |
| IL | application_fee, renewal_fee | $2,500 matches; $1,000 is minimum, not flat; existing note correctly explains | [38 IAC 205.35](https://ilga.gov/commission/jcar/admincode/038/038002050000350R.html) |
| IL | decision_days | 120 days from completion, subject to extension | [§5-5](https://ilga.gov/legislation/ILCS/details?ActID=4549&SeqEnd=2500000&SeqStart=1500000) |
| IL | exemptions | Pending individual tag verification | §3-1 |
| WA | bond structure/min/max | $10,000 floor; ordinary $550,000 cap; $1m discretionary cap. Existing note correct; rule supplies formula | [RCW 19.230](https://app.leg.wa.gov/rcw/default.aspx?cite=19.230&full=true), [WAC 208-690-040](https://app.leg.wa.gov/wAC/default.aspx?cite=208-690-040) |
| WA | net worth structure/min | Statutory floor and rule-based structure match; actual required amount may be higher | [RCW 19.230.060](https://app.leg.wa.gov/rcw/default.aspx?cite=19.230.060) |
| WA | application_fee, renewal_fee | $1,000 application matches; annual assessment $1,000 minimum, $100,000 maximum, not flat | [WAC 208-690-130](https://apps.leg.wa.gov/wAC/default.aspx?cite=208-690-130), [WAC 208-690-103](https://apps.leg.wa.gov/wAC/default.aspx?cite=208-690-103) |
| WA | decision_days | No numeric deadline in cited section; other laws not ruled out | [RCW 19.230.070](https://apps.leg.wa.gov/rcw/default.aspx?cite=19.230.070) |
| WA | license_required, exemptions | Pending individual verification | RCW 19.230.030, .020 |

## Proposed corrections
- FL: add authorized_delegate:560.203 (authorized vendor acting within scope); update exemption note to distinguish chapter-wide exclusions from Part II licensure exemptions.
- IL and WA: preserve minimum recurring fee values only if API/UI explicitly labels them as minimums and exposes the notes.
- WA: expose ordinary and discretionary bond caps separately; do not replace $1m with $550k without agreeing on field semantics.
- TX: retain null for variable assessment; never display as free.

## Status
Draft review; corrections not applied to backend branch or database. Pending checks listed above. The seed script ignores existing rows on conflict, so updating JSON alone does not update already-seeded records. Coordinate correction and database migration with backend owner. No claim of complete legal validation.
