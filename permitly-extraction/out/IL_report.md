# IL extraction report

## A. Quote check

| Field | Answer key | Script |
|---|---|---|
| license_required | ok | ok |
| bond_structure | ok | no answer |
| bond_min_usd | ok | no answer |
| bond_max_usd | ok | no answer |
| net_worth_structure | ok | ok |
| net_worth_min_usd | ok | ok |
| application_fee_usd | ok | ok |
| renewal_fee_usd | ok | ok |
| decision_days | ok | ok |
| exemptions | ok | NOT FOUND, answer thrown out |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | WRONG | None | formula |
| bond_min_usd | WRONG | None | 100000 |
| bond_max_usd | WRONG | None | 2000000 |
| net_worth_structure | WRONG | formula | tiered |
| net_worth_min_usd | correct | 100000 | 100000 |
| application_fee_usd | correct | 2500 | 2500 |
| renewal_fee_usd | WRONG | 1000000 | 1000 |
| decision_days | correct | 120 | 120 |
| exemptions | WRONG | 0 | 17 |

**Field-level accuracy: 4/10 = 40%. Answers thrown out for fake quotes: 1.**

## Fields that failed

- **bond_structure**: None (sec None) vs formula (sec 10-2)
- **bond_min_usd**: None (sec None) vs 100000 (sec 10-2)
- **bond_max_usd**: None (sec None) vs 2000000 (sec 10-2)
- **net_worth_structure**: formula (sec 10-1) vs tiered (sec 10-1)
- **renewal_fee_usd**: 1000000 (sec 38IAC205.35) vs 1000 (sec 38IAC205.35)
- **exemptions**: 0 of 17 found; missed ['agent_of_payee:3-1(2)', 'authorized_delegate:5-1(b)(1)', 'bank:3-1(16)', 'bank:3-1(7)', 'board_of_trade:3-1(9)', 'broker_dealer:3-1(11)', 'ebt_contractor:3-1(8)', 'employee:3-1(12)', 'futures_merchant:3-1(10)', 'government:3-1(4)', 'government:3-1(6)', 'other:3-1(15)', 'payment_intermediary:3-1(3)', 'payment_system:3-1(1)', 'postal_service:3-1(5)', 'regulator_exempts:3-1(14)', 'service_provider_to_bank:3-1(13)']
