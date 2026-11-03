# CA extraction report

## A. Quote check

| Field | Answer key | Script |
|---|---|---|
| license_required | ok | ok |
| bond_structure | ok | ok |
| bond_min_usd | ok | ok |
| bond_max_usd | ok | no answer |
| net_worth_structure | ok | ok |
| net_worth_min_usd | ok | ok |
| application_fee_usd | ok | no answer |
| renewal_fee_usd | ok | no answer |
| decision_days | ok | no answer |
| exemptions | ok | NOT FOUND, answer thrown out |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | WRONG | flat | formula |
| bond_min_usd | correct | 250000 | 250000 |
| bond_max_usd | WRONG | None | 7000000 |
| net_worth_structure | WRONG | formula | tiered |
| net_worth_min_usd | correct | 100000 | 100000 |
| application_fee_usd | WRONG | None | 5000 |
| renewal_fee_usd | WRONG | None | 2500 |
| decision_days | correct | None | None |
| exemptions | WRONG | 0 | 14 |

**Field-level accuracy: 4/10 = 40%. Answers thrown out for fake quotes: 1.**

## Fields that failed

- **bond_structure**: flat (sec 2037) vs formula (sec 2037)
- **bond_max_usd**: None (sec 2037) vs 7000000 (sec 2037)
- **net_worth_structure**: formula (sec 2040) vs tiered (sec 2040)
- **application_fee_usd**: None (sec None) vs 5000 (sec 2032)
- **renewal_fee_usd**: None (sec None) vs 2500 (sec 2038)
- **exemptions**: 0 of 14 found; missed ['agent_of_payee:2010(l)', 'authorized_delegate:2030(a)', 'bank:2010(d)', 'board_of_trade:2010(f)', 'broker_dealer:2010(i)', 'ebt_contractor:2010(e)', 'futures_merchant:2010(n)', 'government:2010(a)', 'government:2010(c)', 'payment_intermediary:2010(m)', 'payment_system:2010(g)', 'payment_system:2010(h)', 'payroll_processor:2010(j)', 'postal_service:2010(b)']
