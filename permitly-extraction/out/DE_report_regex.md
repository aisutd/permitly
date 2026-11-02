# DE extraction report

## A. Quote check

| Field | Answer key | Script |
|---|---|---|
| license_required | ok | ok |
| bond_structure | ok | no answer |
| bond_min_usd | ok | no answer |
| bond_max_usd | ok | no answer |
| net_worth_structure | ok | ok |
| net_worth_min_usd | ok | ok |
| application_fee_usd | ok | no answer |
| renewal_fee_usd | ok | ok |
| decision_days | ok | no answer |
| exemptions | ok | NOT FOUND, answer thrown out |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | WRONG | None | set_by_regulator |
| bond_min_usd | WRONG | None | 100000 |
| bond_max_usd | WRONG | None | 500000 |
| net_worth_structure | WRONG | formula | tiered |
| net_worth_min_usd | correct | 100000 | 100000 |
| application_fee_usd | WRONG | None | 172.5 |
| renewal_fee_usd | correct | 230 | 230 |
| decision_days | correct | None | None |
| exemptions | WRONG | 0 | 15 |

**Field-level accuracy: 4/10 = 40%. Answers thrown out for fake quotes: 1.**

## Fields that failed

- **bond_structure**: None (sec None) vs set_by_regulator (sec 2309)
- **bond_min_usd**: None (sec None) vs 100000 (sec 2309)
- **bond_max_usd**: None (sec None) vs 500000 (sec 2309)
- **net_worth_structure**: formula (sec 2308) vs tiered (sec 2308)
- **application_fee_usd**: None (sec None) vs 172.5 (sec 2306)
- **exemptions**: 0 of 15 found; missed ['agent_of_payee:2305(a)(2)', 'authorized_delegate:2304(b)(1)', 'bank:2305(a)(7)', 'board_of_trade:2305(a)(9)', 'broker_dealer:2305(a)(11)', 'ebt_contractor:2305(a)(8)', 'employee:2305(a)(12)', 'futures_merchant:2305(a)(10)', 'government:2305(a)(4)', 'government:2305(a)(6)', 'payment_intermediary:2305(a)(3)', 'payment_system:2305(a)(1)', 'postal_service:2305(a)(5)', 'regulator_exempts:2305(a)(14)', 'service_provider_to_bank:2305(a)(13)']
