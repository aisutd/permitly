# FL extraction report

## A. Quote check

| Field | Answer key | Script |
|---|---|---|
| license_required | ok | no answer |
| bond_structure | ok | no answer |
| bond_min_usd | ok | no answer |
| bond_max_usd | ok | no answer |
| net_worth_structure | ok | ok |
| net_worth_min_usd | ok | ok |
| application_fee_usd | ok | ok |
| renewal_fee_usd | ok | ok |
| decision_days | ok | no answer |
| exemptions | ok | NOT FOUND, answer thrown out |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | WRONG | None | True |
| bond_structure | WRONG | None | set_by_regulator |
| bond_min_usd | WRONG | None | 50000 |
| bond_max_usd | WRONG | None | 2000000 |
| net_worth_structure | WRONG | flat | formula |
| net_worth_min_usd | correct | 100000 | 100000 |
| application_fee_usd | WRONG | 20000 | 375 |
| renewal_fee_usd | WRONG | 20000 | 750 |
| decision_days | WRONG | None | 90 |
| exemptions | WRONG | 0 | 3 |

**Field-level accuracy: 1/10 = 10%. Answers thrown out for fake quotes: 1.**

## Fields that failed

- **license_required**: None (sec None) vs True (sec 560.125)
- **bond_structure**: None (sec None) vs set_by_regulator (sec 560.209)
- **bond_min_usd**: None (sec None) vs 50000 (sec 560.209)
- **bond_max_usd**: None (sec None) vs 2000000 (sec 560.209)
- **net_worth_structure**: flat (sec 560.209) vs formula (sec 560.209)
- **application_fee_usd**: 20000 (sec 560.143) vs 375 (sec 560.143)
- **renewal_fee_usd**: 20000 (sec 560.143) vs 750 (sec 560.143)
- **decision_days**: None (sec None) vs 90 (sec 120.60)
- **exemptions**: 0 of 3 found; missed ['bank:560.104(1)', 'government:560.104(2)', 'government:560.104(3)']
