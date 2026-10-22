# KY extraction report

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
| decision_days | ok | ok |
| exemptions | ok | ok |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | correct | set_by_regulator | set_by_regulator |
| bond_min_usd | correct | 500000 | 500000 |
| bond_max_usd | correct | 5000000 | 5000000 |
| net_worth_structure | correct | flat | flat |
| net_worth_min_usd | correct | 500000 | 500000 |
| application_fee_usd | correct | 500 | 500 |
| renewal_fee_usd | correct | 500 | 500 |
| decision_days | correct | 120 | 120 |
| exemptions | WRONG | 8 | 9 |

**Field-level accuracy: 9/10 = 90%. Answers thrown out for fake quotes: 0.**

## Fields that failed

- **exemptions**: 7 of 9 found; missed ['authorized_delegate:286.11-005(1)', 'service_provider_to_bank:286.11-007(5)']; wrong ['authorized_delegate:286.11-007(5)']
