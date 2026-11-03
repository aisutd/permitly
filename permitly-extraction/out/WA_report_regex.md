# WA extraction report

## A. Quote check

| Field | Answer key | Script |
|---|---|---|
| license_required | ok | ok |
| bond_structure | ok | no answer |
| bond_min_usd | ok | no answer |
| bond_max_usd | ok | no answer |
| net_worth_structure | ok | ok |
| net_worth_min_usd | ok | no answer |
| application_fee_usd | ok | no answer |
| renewal_fee_usd | ok | no answer |
| decision_days | NOT FOUND | no answer |
| exemptions | ok | no answer |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | WRONG | None | set_by_regulator |
| bond_min_usd | WRONG | None | 10000 |
| bond_max_usd | WRONG | None | 1000000 |
| net_worth_structure | WRONG | flat | set_by_regulator |
| net_worth_min_usd | WRONG | None | 10000 |
| application_fee_usd | WRONG | None | 1000 |
| renewal_fee_usd | WRONG | None | 1000 |
| decision_days | correct | None | None |
| exemptions | WRONG | 0 | 19 |

**Field-level accuracy: 2/10 = 20%. Answers thrown out for fake quotes: 0.**

## Fields that failed

- **bond_structure**: None (sec None) vs set_by_regulator (sec 19.230.050)
- **bond_min_usd**: None (sec None) vs 10000 (sec 19.230.050)
- **bond_max_usd**: None (sec None) vs 1000000 (sec 19.230.050)
- **net_worth_structure**: flat (sec 19.230.060) vs set_by_regulator (sec 19.230.060)
- **net_worth_min_usd**: None (sec 19.230.060) vs 10000 (sec 19.230.060)
- **application_fee_usd**: None (sec None) vs 1000 (sec WAC208-690-130)
- **renewal_fee_usd**: None (sec None) vs 1000 (sec 19.230.110)
- **exemptions**: 0 of 19 found; missed ['agent_of_payee:19.230.020(9)(c)', 'attorney_or_title:19.230.020(11)', 'attorney_or_title:19.230.020(13)', 'authorized_delegate:19.230.030(1)(b)', 'bank:19.230.020(4)', 'board_of_trade:19.230.020(6)', 'broker_dealer:19.230.020(10)', 'ebt_contractor:19.230.020(5)', 'futures_merchant:19.230.020(7)', 'government:19.230.020(1)', 'government:19.230.020(3)', 'incidental_business:19.230.020(16)', 'other:19.230.020(12)', 'other:19.230.020(14)', 'payment_system:19.230.020(8)', 'payment_system:19.230.020(9)(a)', 'payroll_processor:19.230.020(15)', 'postal_service:19.230.020(2)', 'service_provider_to_bank:19.230.020(9)(b)']
