# FL extraction report

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
| bond_min_usd | correct | 50000 | 50000 |
| bond_max_usd | correct | 2000000 | 2000000 |
| net_worth_structure | WRONG | tiered | formula |
| net_worth_min_usd | correct | 100000 | 100000 |
| application_fee_usd | correct | 375 | 375 |
| renewal_fee_usd | correct | 750 | 750 |
| decision_days | correct | 90 | 90 |
| exemptions | WRONG | 4 | 3 |

**Field-level accuracy: 8/10 = 80%. Answers thrown out for fake quotes: 0.**

## Fields that failed

- **net_worth_structure**: tiered (sec 560.209) vs formula (sec 560.209)
- **exemptions**: 2 of 3 found; missed ['government:560.104(3)']; wrong ['other:560.104(3)', 'trust_company:560.104(1)']
