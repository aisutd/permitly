# DE extraction report

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
| bond_min_usd | correct | 100000 | 100000 |
| bond_max_usd | correct | 500000 | 500000 |
| net_worth_structure | WRONG | formula | tiered |
| net_worth_min_usd | correct | 100000 | 100000 |
| application_fee_usd | correct | 172.5 | 172.5 |
| renewal_fee_usd | correct | 230 | 230 |
| decision_days | WRONG | 30 | None |
| exemptions | WRONG | 14 | 15 |

**Field-level accuracy: 7/10 = 70%. Answers thrown out for fake quotes: 0.**

## Fields that failed

- **net_worth_structure**: formula (sec 2308) vs tiered (sec 2308)
- **decision_days**: 30 vs none
- **exemptions**: 0 of 15 found; missed ['agent_of_payee:2305(a)(2)', 'authorized_delegate:2304(b)(1)', 'bank:2305(a)(7)', 'board_of_trade:2305(a)(9)', 'broker_dealer:2305(a)(11)', 'ebt_contractor:2305(a)(8)', 'employee:2305(a)(12)', 'futures_merchant:2305(a)(10)', 'government:2305(a)(4)', 'government:2305(a)(6)', 'payment_intermediary:2305(a)(3)', 'payment_system:2305(a)(1)', 'postal_service:2305(a)(5)', 'regulator_exempts:2305(a)(14)', 'service_provider_to_bank:2305(a)(13)']; wrong ['agent_of_payee:2305(2)', 'bank:2305(7)', 'board_of_trade:2305(9)', 'broker_dealer:2305(11)', 'ebt_contractor:2305(8)', 'employee:2305(12)', 'futures_merchant:2305(10)', 'government:2305(4)', 'government:2305(6)', 'payment_intermediary:2305(3)', 'payment_system:2305(1)', 'postal_service:2305(5)', 'regulator_exempts:2305(14)', 'service_provider_to_bank:2305(13)']
