# TX extraction report

## A. Quote check

| Field | Answer key | Script |
|---|---|---|
| license_required | ok | NOT FOUND, answer thrown out |
| bond_structure | ok | NOT FOUND, answer thrown out |
| bond_min_usd | ok | NOT FOUND, answer thrown out |
| bond_max_usd | ok | ok |
| net_worth_structure | ok | NOT FOUND, answer thrown out |
| net_worth_min_usd | ok | NOT FOUND, answer thrown out |
| application_fee_usd | ok | ok |
| renewal_fee_usd | ok | no answer |
| decision_days | ok | ok |
| exemptions | ok | ok |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | WRONG | None | True |
| bond_structure | WRONG | None | tiered |
| bond_min_usd | WRONG | None | 100000 |
| bond_max_usd | correct | 500000 | 500000 |
| net_worth_structure | WRONG | None | tiered |
| net_worth_min_usd | WRONG | None | 100000 |
| application_fee_usd | correct | 10000 | 10000 |
| renewal_fee_usd | correct | None | None |
| decision_days | correct | 120 | 120 |
| exemptions | correct | 18 | 18 |

**Field-level accuracy: 5/10 = 50%. Answers thrown out for fake quotes: 5.**

## Fields that failed

- **license_required**: None (sec 152.101) vs True (sec 152.101)
- **bond_structure**: None (sec 152.352) vs tiered (sec 152.352)
- **bond_min_usd**: None (sec 152.352) vs 100000 (sec 152.352)
- **net_worth_structure**: None (sec 152.351) vs tiered (sec 152.351)
- **net_worth_min_usd**: None (sec 152.351) vs 100000 (sec 152.351)
