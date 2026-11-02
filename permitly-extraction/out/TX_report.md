# TX extraction report

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
| decision_days | ok | ok |
| exemptions | ok | no answer |

## B. Accuracy

| Field | Result | Script said | Answer key says |
|---|---|---|---|
| license_required | correct | True | True |
| bond_structure | correct | tiered | tiered |
| bond_min_usd | correct | 100000 | 100000 |
| bond_max_usd | correct | 500000 | 500000 |
| net_worth_structure | correct | tiered | tiered |
| net_worth_min_usd | correct | 100000 | 100000 |
| application_fee_usd | correct | 10000 | 10000 |
| renewal_fee_usd | correct | None | None |
| decision_days | correct | 120 | 120 |
| exemptions | WRONG | 0 | 18 |

**Field-level accuracy: 9/10 = 90%. Answers thrown out for fake quotes: 0.**

## Fields that failed

- **exemptions**: 0 of 18 found; missed ['agent_of_payee:152.004(2)', 'attorney_or_title:152.004(9)', 'authorized_delegate:152.101(c)(1)', 'bank:152.004(7)', 'board_of_trade:152.004(11)', 'broker_dealer:152.004(13)', 'ebt_contractor:152.004(10)', 'employee:152.004(14)', 'futures_merchant:152.004(12)', 'government:152.004(4)', 'government:152.004(6)', 'incidental_business:152.101(e)', 'payment_intermediary:152.004(3)', 'payment_system:152.004(1)', 'postal_service:152.004(5)', 'regulator_exempts:152.004(16)', 'service_provider_to_bank:152.004(15)', 'trust_company:152.004(8)']
