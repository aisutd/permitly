# WA extraction report

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
| decision_days | NOT FOUND | no answer |
| exemptions | ok | ok |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | WRONG | formula | set_by_regulator |
| bond_min_usd | correct | 10000 | 10000 |
| bond_max_usd | correct | 1000000 | 1000000 |
| net_worth_structure | correct | set_by_regulator | set_by_regulator |
| net_worth_min_usd | correct | 10000 | 10000 |
| application_fee_usd | correct | 1000 | 1000 |
| renewal_fee_usd | WRONG | None | 1000 |
| decision_days | correct | None | None |
| exemptions | WRONG | 17 | 19 |

**Field-level accuracy: 7/10 = 70%. Answers thrown out for fake quotes: 0.**

## Fields that failed

- **bond_structure**: formula (sec 19.230.050) vs set_by_regulator (sec 19.230.050)
- **renewal_fee_usd**: None (sec None) vs 1000 (sec 19.230.110)
- **exemptions**: 12 of 19 found; missed ['agent_of_payee:19.230.020(9)(c)', 'attorney_or_title:19.230.020(11)', 'authorized_delegate:19.230.030(1)(b)', 'incidental_business:19.230.020(16)', 'payment_system:19.230.020(8)', 'payment_system:19.230.020(9)(a)', 'service_provider_to_bank:19.230.020(9)(b)']; wrong ['authorized_delegate:19.230.030(b)', 'other:19.230.020(11)', 'other:19.230.020(16)', 'payment_intermediary:19.230.020(8)', 'payment_system:19.230.020(9)']
