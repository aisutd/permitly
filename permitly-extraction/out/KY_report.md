# KY extraction report

## A. Quote check

| Field | Answer key | Script |
|---|---|---|
| license_required | ok | ok |
| bond_structure | ok | NOT FOUND, answer thrown out |
| bond_min_usd | ok | ok |
| bond_max_usd | ok | ok |
| net_worth_structure | ok | NOT FOUND, answer thrown out |
| net_worth_min_usd | ok | ok |
| application_fee_usd | ok | ok |
| renewal_fee_usd | ok | ok |
| decision_days | ok | ok |
| exemptions | ok | ok |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | WRONG | None | set_by_regulator |
| bond_min_usd | correct | 500000 | 500000 |
| bond_max_usd | correct | 5000000 | 5000000 |
| net_worth_structure | WRONG | None | flat |
| net_worth_min_usd | correct | 500000 | 500000 |
| application_fee_usd | correct | 500 | 500 |
| renewal_fee_usd | correct | 500 | 500 |
| decision_days | correct | 120 | 120 |
| exemptions | WRONG | 8 | 9 |

**Field-level accuracy: 7/10 = 70%. Answers thrown out for fake quotes: 2.**

## Fields that failed

- **bond_structure**: None (sec 286.11-013) vs set_by_regulator (sec 286.11-013)
- **net_worth_structure**: None (sec 286.11-011) vs flat (sec 286.11-011)
- **exemptions**: 5 of 9 found; missed ['agent_of_payee:286.11-007(6)', 'authorized_delegate:286.11-005(1)', 'ebt_contractor:286.11-007(7)', 'service_provider_to_bank:286.11-007(5)']; wrong ['government:286.11-007(7)', 'other:286.11-007(5)', 'other:286.11-007(6)']
