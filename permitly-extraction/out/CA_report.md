# CA extraction report

## A. Quote check

| Field | Answer key | Script |
|---|---|---|
| license_required | ok | ok |
| bond_structure | ok | ok |
| bond_min_usd | ok | ok |
| bond_max_usd | ok | ok |
| net_worth_structure | ok | ok |
| net_worth_min_usd | ok | ok |
| application_fee_usd | ok | ok |
| renewal_fee_usd | ok | ok |
| decision_days | ok | no answer |
| exemptions | ok | ok |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | WRONG | tiered | formula |
| bond_min_usd | correct | 250000 | 250000 |
| bond_max_usd | correct | 7000000 | 7000000 |
| net_worth_structure | correct | tiered | tiered |
| net_worth_min_usd | correct | 100000 | 100000 |
| application_fee_usd | correct | 5000 | 5000 |
| renewal_fee_usd | correct | 2500 | 2500 |
| decision_days | correct | None | None |
| exemptions | WRONG | 15 | 14 |

**Field-level accuracy: 8/10 = 80%. Answers thrown out for fake quotes: 0.**

## Fields that failed

- **bond_structure**: tiered (sec 2037) vs formula (sec 2037)
- **exemptions**: 13 of 14 found; missed ['payment_system:2010(g)']; wrong ['bank:2010(k)', 'payment_intermediary:2010(g)']
