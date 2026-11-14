# TX extraction report

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
| renewal_fee_usd | ok | no answer |
| decision_days | ok | ok |
| exemptions | ok | ok |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | WRONG | formula | tiered |
| bond_min_usd | correct | 100000 | 100000 |
| bond_max_usd | correct | 500000 | 500000 |
| net_worth_structure | WRONG | formula | tiered |
| net_worth_min_usd | correct | 100000 | 100000 |
| application_fee_usd | correct | 10000 | 10000 |
| renewal_fee_usd | correct | None | None |
| decision_days | correct | 120 | 120 |
| exemptions | WRONG | 16 | 18 |

**Field-level accuracy: 7/10 = 70%. Answers thrown out for fake quotes: 0.**

## Fields that failed

- **bond_structure**: formula (sec 152.352) vs tiered (sec 152.352)
- **net_worth_structure**: formula (sec 152.351) vs tiered (sec 152.351)
- **exemptions**: 16 of 18 found; missed ['authorized_delegate:152.101(c)(1)', 'incidental_business:152.101(e)']
