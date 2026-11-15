# redactd benchmark report

Generated 2026-11-14 23:26 UTC · mode **standard** · shipped `redactd.pipeline.Pipeline` · 3 worker processes × 1 thread · total wall time 1.3 min

Recall = share of gold identifiers with ≥50% / ≥90% of their characters redacted. Precision = share of redacted characters that fall inside a gold span (Gretel leaves real PII unlabelled, so its precision understates reality). *Raw* uses dataset labels as-is; *policy* removes gold spans that are template placeholders and, for organisation labels only, generic phrases and public bodies (`bench/gold_policy.py`).

**Held-out** sets are never used to tune rules, thresholds or prompts. **Dev** sets are. The **regression** set (hand-built hard cases) was written by us and rules were fixed against it, so it shows that known hard cases pass, not how unseen text behaves.

## Summary

| Set | Role | Docs | Direct ≥50 raw | Direct ≥90 raw | Indirect ≥50 raw | Indirect ≥90 raw | Prec raw | Direct ≥50 pol | Direct ≥90 pol | Indirect ≥50 pol | Indirect ≥90 pol | Prec pol |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| eval_gretel_fin_holdout | held-out | 300 | 99.0 | 97.3 | 93.8 | 91.3 | 37.3 | 99.7 | 98.9 | 96.2 | 94.8 | 36.1 |
| eval_fin_holdout2 | held-out | 300 | 98.9 | 97.5 | 89.4 | 86.8 | 38.9 | 99.5 | 98.3 | 92.5 | 89.8 | 38.4 |
| eval_nemotron_fin_structured | held-out | 300 | 99.9 | 99.6 | 90.8 | 89.6 | 81.8 | 99.9 | 99.6 | 94.3 | 93.1 | 81.8 |
| eval_gretel_en | held-out | 300 | 99.9 | 99.2 | 100.0 | 98.4 | 78.9 | 99.9 | 99.2 | 100.0 | 98.4 | 78.9 |
| eval_adversarial | regression | 160 | 99.7 | 99.5 | 100.0 | 100.0 | 75.3 | 99.8 | 99.7 | 100.0 | 100.0 | 75.2 |
| eval_gretel_fin | dev | 200 | 99.1 | 97.7 | 95.6 | 94.0 | 41.6 | 99.4 | 98.5 | 99.1 | 97.6 | 39.7 |
| eval_nemotron_fin | dev | 300 | 99.9 | 99.9 | 97.1 | 95.3 | 78.2 | 99.9 | 99.9 | 98.2 | 96.3 | 78.2 |
| dev_nemotron_fin_structured | dev | 200 | 99.7 | 99.5 | 92.4 | 89.6 | 76.5 | 99.7 | 99.5 | 96.3 | 94.7 | 76.4 |

## Leak regression (A3)

`leak_check` must be empty for every rendered document. *Gold direct values in output* is a raw string search of the redacted output for every gold DIRECT value; it counts every miss and also short values that survive as substrings of unrelated words.

| Set | leak_check failures | Gold direct values still in output | of | Docs affected |
|---|---:|---:|---:|---:|
| eval_gretel_fin_holdout | 0 | 5 | 773 | 5 / 300 |
| eval_fin_holdout2 | 0 | 5 | 720 | 5 / 300 |
| eval_nemotron_fin_structured | 0 | 2 | 1287 | 2 / 300 |
| eval_gretel_en | 0 | 0 | 1130 | 0 / 300 |
| eval_adversarial | 0 | 2 | 592 | 2 / 160 |
| eval_gretel_fin | 0 | 4 | 513 | 4 / 200 |
| eval_nemotron_fin | 0 | 2 | 1270 | 2 / 300 |
| dev_nemotron_fin_structured | 0 | 1 | 824 | 1 / 200 |

## Latency (per document, measured inside the worker; all workers busy)

| Set | mean chars | p50 ms | p95 ms | p99 ms | ms / 1k chars | stage share |
|---|---:|---:|---:|---:|---:|---|
| eval_gretel_fin_holdout | 1399 | 139 | 528 | 574 | 114 | rules 1%, distilled 98%, finalize 1% |
| eval_fin_holdout2 | 1427 | 159 | 532 | 606 | 118 | rules 1%, distilled 98%, finalize 1% |
| eval_nemotron_fin_structured | 1087 | 96 | 572 | 628 | 136 | rules 1%, distilled 99%, finalize 0% |
| eval_gretel_en | 221 | 19 | 54 | 110 | 106 | rules 1%, distilled 98%, finalize 1% |
| eval_adversarial | 147 | 14 | 42 | 50 | 125 | rules 1%, distilled 97%, finalize 2% |
| eval_gretel_fin | 1481 | 152 | 549 | 640 | 113 | rules 1%, distilled 99%, finalize 1% |
| eval_nemotron_fin | 615 | 36 | 98 | 145 | 73 | rules 1%, distilled 98%, finalize 1% |
| dev_nemotron_fin_structured | 1031 | 86 | 563 | 650 | 132 | rules 1%, distilled 99%, finalize 1% |

## eval_gretel_fin_holdout (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 439 | 99.8 | 98.4 |
| ORG | 437 | 92.9 | 89.9 |
| ADDRESS | 244 | 97.5 | 96.3 |
| DATE | 130 | 97.7 | 95.4 |
| CONTACT | 125 | 97.6 | 93.6 |
| FIN_ID | 94 | 100.0 | 100.0 |
| NETWORK | 19 | 100.0 | 100.0 |
| GOV_ID | 15 | 100.0 | 100.0 |
| SECRET | 10 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 437 | 92.9 | 89.9 |
| direct:name | 406 | 99.8 | 98.3 |
| direct:street_address | 240 | 97.5 | 96.2 |
| indirect:date | 85 | 98.8 | 97.6 |
| direct:phone_number | 81 | 97.5 | 93.8 |
| direct:email | 44 | 97.7 | 93.2 |
| indirect:time | 25 | 92.0 | 92.0 |
| direct:swift_bic_code | 18 | 100.0 | 100.0 |
| direct:last_name | 16 | 100.0 | 100.0 |
| direct:date_of_birth | 16 | 100.0 | 87.5 |
| direct:bban | 14 | 100.0 | 100.0 |
| direct:first_name | 14 | 100.0 | 100.0 |
| direct:iban | 14 | 100.0 | 100.0 |
| direct:ipv6 | 12 | 100.0 | 100.0 |
| direct:bank_routing_number | 11 | 100.0 | 100.0 |
| direct:credit_card_number | 9 | 100.0 | 100.0 |
| direct:customer_id | 8 | 100.0 | 100.0 |
| direct:ssn | 8 | 100.0 | 100.0 |
| direct:employee_id | 8 | 100.0 | 100.0 |
| direct:ipv4 | 7 | 100.0 | 100.0 |
| direct:account_pin | 7 | 100.0 | 100.0 |
| direct:password | 6 | 100.0 | 100.0 |
| direct:passport_number | 5 | 100.0 | 100.0 |
| direct:credit_card_security_code | 5 | 100.0 | 100.0 |
| direct:local_latlng | 4 | 100.0 | 100.0 |
| direct:api_key | 4 | 100.0 | 100.0 |
| indirect:date_time | 4 | 100.0 | 100.0 |
| direct:user_name | 3 | 100.0 | 100.0 |
| direct:driver_license_number | 2 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Bill of Lading | 98 | 91.8 | 91.8 |
| CSV | 89 | 100.0 | 100.0 |
| IT support ticket | 74 | 98.6 | 97.3 |
| Loan Application | 73 | 98.6 | 97.3 |
| Health Insurance Claim Form | 65 | 96.9 | 95.4 |
| Business Plan | 61 | 93.4 | 93.4 |
| ISDA Definition | 61 | 95.1 | 86.9 |
| Insurance Claim Form | 48 | 97.9 | 95.8 |
| Policyholder's Report | 43 | 93.0 | 93.0 |
| Payment Confirmation | 42 | 100.0 | 97.6 |
| FpML | 38 | 100.0 | 100.0 |
| Financial Aid Application | 38 | 100.0 | 94.7 |
| SWIFT Message | 38 | 94.7 | 89.5 |
| Trade Confirmation | 37 | 100.0 | 97.3 |
| Safety Data Sheet | 36 | 100.0 | 100.0 |
| Customer support conversational log | 36 | 100.0 | 97.2 |
| Email | 34 | 100.0 | 100.0 |
| Regulatory Filing | 33 | 93.9 | 90.9 |
| Financial Statement | 33 | 97.0 | 97.0 |
| EDI | 31 | 100.0 | 100.0 |
| Insurance Policy | 30 | 100.0 | 100.0 |
| Tax Return | 24 | 95.8 | 91.7 |
| Financial Risk Assessment | 22 | 100.0 | 100.0 |
| Compliance Certificate | 22 | 100.0 | 100.0 |
| Corporate Governance Guidelines | 21 | 100.0 | 90.5 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 37735 | 45.0 |
| tier:indirect | 32058 | 25.7 |
| ADDRESS | 13437 | 51.4 |
| DEMOGRAPHIC | 12588 | 3.4 |
| ORG | 11497 | 54.0 |
| DATE | 7973 | 20.1 |
| SECRET | 7520 | 6.7 |
| NAME | 7237 | 80.8 |
| CONTACT | 6549 | 30.5 |
| FIN_ID | 2288 | 44.5 |
| NETWORK | 564 | 99.6 |
| GOV_ID | 140 | 92.9 |

## eval_fin_holdout2 (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| ORG | 413 | 86.7 | 83.8 |
| NAME | 396 | 98.7 | 98.0 |
| ADDRESS | 271 | 98.9 | 95.9 |
| DATE | 156 | 96.8 | 95.5 |
| FIN_ID | 96 | 99.0 | 99.0 |
| CONTACT | 81 | 100.0 | 97.5 |
| GOV_ID | 21 | 100.0 | 100.0 |
| NETWORK | 15 | 100.0 | 100.0 |
| SECRET | 7 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 413 | 86.7 | 83.8 |
| direct:name | 376 | 98.7 | 97.9 |
| direct:street_address | 267 | 98.9 | 95.9 |
| indirect:date | 110 | 99.1 | 99.1 |
| direct:phone_number | 49 | 100.0 | 98.0 |
| direct:email | 32 | 100.0 | 96.9 |
| indirect:time | 24 | 87.5 | 79.2 |
| direct:employee_id | 21 | 100.0 | 100.0 |
| direct:bban | 16 | 100.0 | 100.0 |
| direct:date_of_birth | 15 | 93.3 | 93.3 |
| direct:swift_bic_code | 15 | 100.0 | 100.0 |
| direct:credit_card_number | 10 | 100.0 | 100.0 |
| direct:bank_routing_number | 10 | 100.0 | 100.0 |
| direct:last_name | 10 | 100.0 | 100.0 |
| direct:customer_id | 8 | 100.0 | 100.0 |
| direct:ipv6 | 8 | 100.0 | 100.0 |
| direct:passport_number | 7 | 100.0 | 100.0 |
| indirect:date_time | 7 | 100.0 | 100.0 |
| direct:ipv4 | 7 | 100.0 | 100.0 |
| direct:ssn | 7 | 100.0 | 100.0 |
| direct:account_pin | 7 | 100.0 | 100.0 |
| direct:driver_license_number | 7 | 100.0 | 100.0 |
| direct:first_name | 5 | 100.0 | 100.0 |
| direct:credit_card_security_code | 5 | 80.0 | 80.0 |
| direct:user_name | 5 | 100.0 | 100.0 |
| direct:password | 4 | 100.0 | 100.0 |
| direct:local_latlng | 4 | 100.0 | 100.0 |
| direct:iban | 4 | 100.0 | 100.0 |
| direct:api_key | 3 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Insurance Policy | 91 | 98.9 | 98.9 |
| Bill of Lading | 86 | 96.5 | 95.3 |
| CSV | 66 | 100.0 | 98.5 |
| Payment Confirmation | 64 | 96.9 | 92.2 |
| IT support ticket | 54 | 100.0 | 100.0 |
| Customer support conversational log | 49 | 100.0 | 100.0 |
| Health Insurance Claim Form | 45 | 100.0 | 100.0 |
| Loan Application | 44 | 100.0 | 97.7 |
| Credit Card Statement | 36 | 91.7 | 86.1 |
| Shareholder Agreement | 35 | 71.4 | 71.4 |
| Investment Prospectus | 34 | 94.1 | 94.1 |
| Audit Report | 32 | 100.0 | 100.0 |
| BAI Format | 32 | 100.0 | 96.9 |
| FIX Protocol | 31 | 93.5 | 90.3 |
| SWIFT Message | 31 | 93.5 | 71.0 |
| Safety Data Sheet | 30 | 83.3 | 73.3 |
| Tax Return | 30 | 96.7 | 96.7 |
| Real Estate Loan Agreement | 29 | 96.6 | 96.6 |
| Policyholder's Report | 29 | 86.2 | 82.8 |
| Transaction Confirmation | 28 | 96.4 | 92.9 |
| Compliance Certificate | 27 | 100.0 | 100.0 |
| ISDA Definition | 26 | 88.5 | 88.5 |
| Insurance Claim Form | 25 | 96.0 | 96.0 |
| MT940 | 25 | 96.0 | 96.0 |
| Annual Report | 24 | 95.8 | 91.7 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 37816 | 44.7 |
| tier:indirect | 29111 | 30.2 |
| ADDRESS | 14738 | 54.9 |
| ORG | 11229 | 57.4 |
| DEMOGRAPHIC | 10651 | 3.9 |
| DATE | 7231 | 26.7 |
| SECRET | 6871 | 4.6 |
| NAME | 6798 | 80.9 |
| CONTACT | 6467 | 20.8 |
| FIN_ID | 2310 | 47.2 |
| NETWORK | 448 | 90.6 |
| GOV_ID | 184 | 85.3 |

## eval_nemotron_fin_structured (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 586 | 100.0 | 99.8 |
| NAME | 498 | 100.0 | 100.0 |
| DATE | 414 | 94.2 | 93.7 |
| CONTACT | 348 | 99.7 | 99.7 |
| ADDRESS | 322 | 94.4 | 93.2 |
| ORG | 225 | 100.0 | 99.1 |
| DEMOGRAPHIC | 176 | 70.5 | 68.2 |
| GOV_ID | 130 | 100.0 | 96.9 |
| SECRET | 47 | 100.0 | 100.0 |
| NETWORK | 28 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:date | 312 | 93.3 | 93.3 |
| direct:first_name | 248 | 100.0 | 100.0 |
| indirect:company_name | 225 | 100.0 | 99.1 |
| direct:last_name | 218 | 100.0 | 100.0 |
| direct:account_number | 189 | 100.0 | 100.0 |
| direct:email | 174 | 99.4 | 99.4 |
| direct:customer_id | 110 | 100.0 | 99.1 |
| direct:credit_debit_card | 102 | 100.0 | 100.0 |
| direct:street_address | 95 | 98.9 | 98.9 |
| indirect:occupation | 94 | 58.5 | 57.4 |
| direct:url | 83 | 100.0 | 100.0 |
| direct:bank_routing_number | 75 | 100.0 | 100.0 |
| direct:phone_number | 71 | 100.0 | 100.0 |
| indirect:state | 61 | 91.8 | 85.2 |
| indirect:country | 52 | 100.0 | 100.0 |
| indirect:city | 50 | 100.0 | 100.0 |
| direct:ssn | 44 | 100.0 | 100.0 |
| direct:swift_bic | 41 | 100.0 | 100.0 |
| indirect:time | 40 | 95.0 | 90.0 |
| direct:date_of_birth | 36 | 100.0 | 100.0 |
| indirect:county | 35 | 65.7 | 65.7 |
| direct:cvv | 33 | 100.0 | 100.0 |
| direct:user_name | 32 | 100.0 | 100.0 |
| direct:biometric_identifier | 31 | 100.0 | 100.0 |
| direct:password | 29 | 100.0 | 100.0 |
| indirect:postcode | 29 | 100.0 | 100.0 |
| indirect:date_time | 26 | 96.2 | 96.2 |
| indirect:employment_status | 21 | 71.4 | 71.4 |
| direct:fax_number | 20 | 100.0 | 100.0 |
| direct:pin | 20 | 100.0 | 100.0 |
| direct:health_plan_beneficiary_number | 19 | 100.0 | 78.9 |
| direct:tax_id | 14 | 100.0 | 100.0 |
| indirect:education_level | 13 | 92.3 | 69.2 |
| direct:ipv4 | 11 | 100.0 | 100.0 |
| indirect:language | 10 | 70.0 | 70.0 |
| indirect:race_ethnicity | 10 | 100.0 | 100.0 |
| direct:medical_record_number | 10 | 100.0 | 100.0 |
| direct:api_key | 10 | 100.0 | 100.0 |
| indirect:age | 9 | 88.9 | 88.9 |
| direct:employee_id | 9 | 100.0 | 100.0 |
| direct:http_cookie | 8 | 100.0 | 100.0 |
| direct:mac_address | 8 | 100.0 | 100.0 |
| indirect:political_view | 7 | 85.7 | 85.7 |
| direct:unique_id | 7 | 100.0 | 100.0 |
| direct:ipv6 | 6 | 100.0 | 100.0 |
| direct:national_id | 5 | 100.0 | 100.0 |
| direct:certificate_license_number | 5 | 100.0 | 100.0 |
| indirect:religious_belief | 4 | 100.0 | 100.0 |
| indirect:gender | 4 | 100.0 | 100.0 |
| direct:device_identifier | 3 | 100.0 | 100.0 |
| indirect:blood_type | 2 | 100.0 | 100.0 |
| indirect:sexuality | 2 | 50.0 | 50.0 |
| direct:license_plate | 1 | 100.0 | 100.0 |
| direct:vehicle_identifier | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Investment Agreement | 58 | 98.3 | 98.3 |
| Mortgage Loan | 54 | 92.6 | 92.6 |
| Premium Payment Schedule | 48 | 100.0 | 91.7 |
| Emergency Planning | 44 | 95.5 | 93.2 |
| Corporate Solutions | 41 | 97.6 | 97.6 |
| Affidavit of No Contingencies | 40 | 90.0 | 90.0 |
| Privacy Policy Document | 39 | 100.0 | 100.0 |
| Investment Statement | 38 | 97.4 | 97.4 |
| Bank Services | 35 | 100.0 | 100.0 |
| Audit Report | 34 | 100.0 | 97.1 |
| Affidavit of No Unpaid Insurance Premiums | 34 | 70.6 | 70.6 |
| Debt Consolidation Agreement | 33 | 100.0 | 100.0 |
| Investment Proposal | 33 | 100.0 | 100.0 |
| Investment Strategy | 32 | 100.0 | 100.0 |
| Affidavit of Title | 31 | 96.8 | 96.8 |
| Due Diligence Report | 30 | 100.0 | 100.0 |
| Affidavit of No Unpaid Maintenance Fees | 30 | 96.7 | 96.7 |
| Credit Card Replacement Form | 29 | 89.7 | 89.7 |
| Application Setup Guide | 29 | 100.0 | 100.0 |
| Investment Evaluation | 29 | 96.6 | 96.6 |
| Risk Management Plan | 27 | 100.0 | 100.0 |
| Authorization Form | 27 | 70.4 | 70.4 |
| Investment Portfolio | 26 | 100.0 | 96.2 |
| Personal Identification | 26 | 100.0 | 100.0 |
| Power of Attorney | 26 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 29396 | 94.1 |
| tier:indirect | 16488 | 59.9 |
| CONTACT | 11763 | 99.1 |
| ORG | 6878 | 63.4 |
| FIN_ID | 6384 | 95.8 |
| DEMOGRAPHIC | 4896 | 28.3 |
| DATE | 4714 | 87.5 |
| ADDRESS | 3764 | 90.8 |
| NAME | 3651 | 91.4 |
| SECRET | 2452 | 71.7 |
| GOV_ID | 871 | 98.7 |
| NETWORK | 511 | 99.6 |

## eval_gretel_en (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| GOV_ID | 341 | 100.0 | 99.1 |
| DATE | 225 | 100.0 | 100.0 |
| NAME | 224 | 100.0 | 100.0 |
| FIN_ID | 189 | 100.0 | 99.5 |
| ADDRESS | 101 | 99.0 | 95.0 |
| CONTACT | 100 | 100.0 | 100.0 |
| NETWORK | 50 | 100.0 | 100.0 |
| ORG | 16 | 100.0 | 87.5 |
| SECRET | 8 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:medical_record_number | 161 | 100.0 | 100.0 |
| direct:date_of_birth | 130 | 100.0 | 100.0 |
| direct:ssn | 103 | 100.0 | 97.1 |
| direct:street_address | 87 | 98.9 | 94.3 |
| direct:first_name | 78 | 100.0 | 100.0 |
| indirect:date | 77 | 100.0 | 100.0 |
| direct:last_name | 71 | 100.0 | 100.0 |
| direct:employee_id | 61 | 100.0 | 100.0 |
| direct:customer_id | 56 | 100.0 | 98.2 |
| direct:name | 55 | 100.0 | 100.0 |
| direct:phone_number | 50 | 100.0 | 100.0 |
| direct:email | 49 | 100.0 | 100.0 |
| direct:license_plate | 44 | 100.0 | 100.0 |
| direct:ipv4 | 36 | 100.0 | 100.0 |
| direct:credit_card_number | 35 | 100.0 | 100.0 |
| direct:user_name | 20 | 100.0 | 100.0 |
| indirect:company_name | 16 | 100.0 | 87.5 |
| direct:bank_routing_number | 14 | 100.0 | 100.0 |
| direct:account_number | 13 | 100.0 | 100.0 |
| direct:device_identifier | 12 | 100.0 | 100.0 |
| direct:certificate_license_number | 11 | 100.0 | 100.0 |
| indirect:date_time | 11 | 100.0 | 100.0 |
| direct:unique_id | 10 | 100.0 | 100.0 |
| direct:biometric_identifier | 7 | 100.0 | 100.0 |
| direct:vehicle_identifier | 7 | 100.0 | 100.0 |
| indirect:time | 7 | 100.0 | 100.0 |
| indirect:city | 6 | 100.0 | 100.0 |
| direct:password | 5 | 100.0 | 100.0 |
| indirect:postcode | 4 | 100.0 | 100.0 |
| direct:api_key | 3 | 100.0 | 100.0 |
| direct:health_plan_beneficiary_number | 3 | 100.0 | 100.0 |
| indirect:country | 3 | 100.0 | 100.0 |
| direct:national_id | 3 | 100.0 | 100.0 |
| direct:ipv6 | 2 | 100.0 | 100.0 |
| direct:tax_id | 2 | 100.0 | 100.0 |
| direct:coordinate | 1 | 100.0 | 100.0 |
| direct:url | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| ClaimForm | 23 | 100.0 | 100.0 |
| Marriage Certificate | 17 | 100.0 | 100.0 |
| Invoice | 15 | 100.0 | 93.3 |
| Bill of Lading | 14 | 100.0 | 100.0 |
| Packing List | 14 | 100.0 | 100.0 |
| Incident Report | 13 | 100.0 | 100.0 |
| Vaccination Record | 13 | 100.0 | 100.0 |
| BillOfLading | 13 | 100.0 | 100.0 |
| PackageInsert | 12 | 100.0 | 100.0 |
| UserManual | 12 | 100.0 | 100.0 |
| IncidentReport | 12 | 100.0 | 100.0 |
| InsurancePolicy | 11 | 100.0 | 100.0 |
| Audit Report | 11 | 100.0 | 90.9 |
| Shipment Notice | 10 | 100.0 | 100.0 |
| Contract | 10 | 100.0 | 100.0 |
| CaseReportForm | 10 | 100.0 | 100.0 |
| PromotionDetails | 10 | 100.0 | 90.0 |
| DisciplinaryActionForm | 10 | 100.0 | 100.0 |
| QualityControlReport | 10 | 100.0 | 100.0 |
| Distribution Agreement | 10 | 100.0 | 100.0 |
| AccountClosureForm | 10 | 100.0 | 100.0 |
| Data Privacy Notice | 10 | 100.0 | 100.0 |
| Title Report | 10 | 100.0 | 100.0 |
| Bill | 10 | 100.0 | 100.0 |
| DrugMasterFile | 10 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 14620 | 92.0 |
| tier:indirect | 5802 | 46.1 |
| FIN_ID | 3804 | 97.7 |
| DATE | 3507 | 70.7 |
| ADDRESS | 3112 | 91.8 |
| NAME | 2436 | 90.5 |
| CONTACT | 1949 | 97.4 |
| DEMOGRAPHIC | 1937 | 2.2 |
| GOV_ID | 1886 | 99.3 |
| SECRET | 800 | 37.1 |
| NETWORK | 633 | 95.9 |
| ORG | 358 | 42.2 |

## eval_adversarial (regression)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 224 | 99.1 | 98.7 |
| FIN_ID | 220 | 100.0 | 100.0 |
| ADDRESS | 112 | 100.0 | 100.0 |
| CONTACT | 80 | 100.0 | 100.0 |
| DATE | 28 | 100.0 | 100.0 |
| GOV_ID | 24 | 100.0 | 100.0 |
| ORG | 16 | 100.0 | 100.0 |
| SECRET | 4 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:name | 132 | 100.0 | 99.2 |
| direct:account_number | 76 | 100.0 | 100.0 |
| direct:iban | 60 | 100.0 | 100.0 |
| direct:first_name | 52 | 100.0 | 100.0 |
| direct:phone_number | 44 | 100.0 | 100.0 |
| direct:street_address | 40 | 100.0 | 100.0 |
| indirect:city | 40 | 100.0 | 100.0 |
| direct:last_name | 36 | 94.4 | 94.4 |
| direct:email | 36 | 100.0 | 100.0 |
| direct:credit_debit_card | 32 | 100.0 | 100.0 |
| indirect:postcode | 28 | 100.0 | 100.0 |
| indirect:date | 20 | 100.0 | 100.0 |
| direct:customer_id | 20 | 100.0 | 100.0 |
| direct:swift_bic | 20 | 100.0 | 100.0 |
| indirect:company | 16 | 100.0 | 100.0 |
| direct:ssn | 12 | 100.0 | 100.0 |
| direct:bank_routing_number | 12 | 100.0 | 100.0 |
| direct:date_of_birth | 8 | 100.0 | 100.0 |
| indirect:country | 4 | 100.0 | 100.0 |
| direct:password | 4 | 100.0 | 100.0 |
| direct:user_name | 4 | 100.0 | 100.0 |
| direct:passport_number | 4 | 100.0 | 100.0 |
| direct:driver_license_number | 4 | 100.0 | 100.0 |
| direct:tax_id | 4 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| international formats | 124 | 100.0 | 100.0 |
| structured keys | 92 | 100.0 | 100.0 |
| email threads | 76 | 98.7 | 97.4 |
| SWIFT / FIX | 64 | 98.4 | 98.4 |
| common-word names | 56 | 100.0 | 100.0 |
| masked partials | 56 | 100.0 | 100.0 |
| coreference | 48 | 100.0 | 100.0 |
| odd spacing / line breaks | 44 | 100.0 | 100.0 |
| glued text | 40 | 100.0 | 100.0 |
| prompt injection | 40 | 100.0 | 100.0 |
| keyword ids | 24 | 100.0 | 100.0 |
| public bodies / dates | 24 | 100.0 | 100.0 |
| chat log | 20 | 100.0 | 100.0 |

### Recall by template exposure

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| templates also rendered (other values) for training | 356 | 100.0 | 99.7 |
| templates never used in training | 352 | 99.4 | 99.4 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 10534 | 81.1 |
| FIN_ID | 3314 | 84.0 |
| NAME | 2345 | 91.5 |
| tier:indirect | 2001 | 44.0 |
| CONTACT | 1936 | 97.0 |
| ADDRESS | 1690 | 79.2 |
| SECRET | 1017 | 16.5 |
| DEMOGRAPHIC | 888 | 5.4 |
| DATE | 620 | 62.9 |
| ORG | 493 | 89.9 |
| GOV_ID | 232 | 100.0 |

## eval_gretel_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 304 | 99.7 | 98.0 |
| ORG | 284 | 94.4 | 93.3 |
| ADDRESS | 200 | 99.5 | 98.0 |
| DATE | 94 | 98.9 | 95.7 |
| CONTACT | 69 | 98.6 | 95.7 |
| FIN_ID | 65 | 96.9 | 96.9 |
| GOV_ID | 19 | 100.0 | 100.0 |
| NETWORK | 11 | 100.0 | 100.0 |
| SECRET | 11 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 284 | 94.4 | 93.3 |
| direct:name | 271 | 99.6 | 97.8 |
| direct:street_address | 191 | 99.5 | 97.9 |
| indirect:date | 68 | 100.0 | 100.0 |
| direct:email | 36 | 100.0 | 100.0 |
| direct:phone_number | 33 | 97.0 | 90.9 |
| direct:first_name | 31 | 100.0 | 100.0 |
| indirect:time | 13 | 100.0 | 76.9 |
| direct:account_pin | 12 | 100.0 | 100.0 |
| direct:date_of_birth | 11 | 90.9 | 90.9 |
| direct:credit_card_security_code | 10 | 80.0 | 80.0 |
| direct:employee_id | 10 | 100.0 | 100.0 |
| direct:local_latlng | 9 | 100.0 | 100.0 |
| direct:customer_id | 9 | 100.0 | 100.0 |
| direct:ssn | 8 | 100.0 | 100.0 |
| direct:passport_number | 8 | 100.0 | 100.0 |
| direct:credit_card_number | 7 | 100.0 | 100.0 |
| direct:ipv4 | 7 | 100.0 | 100.0 |
| direct:password | 7 | 100.0 | 100.0 |
| direct:swift_bic_code | 6 | 100.0 | 100.0 |
| direct:iban | 6 | 100.0 | 100.0 |
| direct:ipv6 | 4 | 100.0 | 100.0 |
| direct:api_key | 4 | 100.0 | 100.0 |
| direct:bank_routing_number | 3 | 100.0 | 100.0 |
| direct:driver_license_number | 3 | 100.0 | 100.0 |
| indirect:date_time | 2 | 100.0 | 100.0 |
| direct:bban | 2 | 100.0 | 100.0 |
| direct:last_name | 1 | 100.0 | 100.0 |
| direct:user_name | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Loan Application | 101 | 99.0 | 99.0 |
| BAI Format | 50 | 96.0 | 96.0 |
| SWIFT Message | 47 | 100.0 | 97.9 |
| Policyholder's Report | 43 | 100.0 | 95.3 |
| IT support ticket | 39 | 100.0 | 100.0 |
| Customer support conversational log | 37 | 100.0 | 100.0 |
| Customer Agreement | 35 | 100.0 | 100.0 |
| Payment Confirmation | 31 | 96.8 | 96.8 |
| Audit Report | 31 | 100.0 | 100.0 |
| EDI | 31 | 100.0 | 96.8 |
| Supply Chain Management Agreement | 29 | 100.0 | 100.0 |
| FIX Protocol | 29 | 100.0 | 100.0 |
| Bill of Lading | 29 | 100.0 | 100.0 |
| Financial Risk Assessment | 25 | 100.0 | 96.0 |
| Regulatory Compliance Guide | 25 | 84.0 | 84.0 |
| Insurance Policy | 24 | 100.0 | 100.0 |
| Trade Confirmation | 23 | 100.0 | 95.7 |
| CSV | 21 | 100.0 | 100.0 |
| Financial Disclosure Statement | 21 | 100.0 | 100.0 |
| Compliance Certificate | 21 | 100.0 | 95.2 |
| MT940 | 17 | 100.0 | 100.0 |
| Employment Contract | 17 | 100.0 | 100.0 |
| Credit Card Statement | 16 | 87.5 | 87.5 |
| Email | 16 | 100.0 | 87.5 |
| Health Insurance Claim Form | 16 | 100.0 | 87.5 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 24168 | 48.1 |
| tier:indirect | 19759 | 29.4 |
| ADDRESS | 9137 | 61.7 |
| DEMOGRAPHIC | 7725 | 2.7 |
| ORG | 7544 | 58.3 |
| SECRET | 5660 | 6.8 |
| DATE | 4490 | 27.0 |
| NAME | 4164 | 85.8 |
| CONTACT | 3205 | 34.4 |
| FIN_ID | 1517 | 35.5 |
| NETWORK | 307 | 75.2 |
| GOV_ID | 178 | 93.3 |

## eval_nemotron_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 480 | 100.0 | 100.0 |
| NAME | 370 | 99.7 | 99.7 |
| ADDRESS | 265 | 99.6 | 99.6 |
| CONTACT | 262 | 99.6 | 99.6 |
| DATE | 221 | 99.1 | 97.7 |
| DEMOGRAPHIC | 158 | 89.9 | 84.2 |
| ORG | 127 | 100.0 | 100.0 |
| GOV_ID | 103 | 100.0 | 100.0 |
| NETWORK | 49 | 100.0 | 100.0 |
| SECRET | 34 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:first_name | 194 | 99.5 | 99.5 |
| direct:account_number | 167 | 100.0 | 100.0 |
| direct:last_name | 144 | 100.0 | 100.0 |
| indirect:date | 137 | 98.5 | 97.8 |
| indirect:company_name | 127 | 100.0 | 100.0 |
| direct:email | 121 | 99.2 | 99.2 |
| direct:customer_id | 106 | 100.0 | 100.0 |
| direct:url | 81 | 100.0 | 100.0 |
| direct:street_address | 71 | 100.0 | 100.0 |
| indirect:country | 67 | 100.0 | 100.0 |
| direct:credit_debit_card | 64 | 100.0 | 100.0 |
| direct:bank_routing_number | 61 | 100.0 | 100.0 |
| indirect:state | 45 | 97.8 | 97.8 |
| direct:phone_number | 43 | 100.0 | 100.0 |
| indirect:city | 35 | 100.0 | 100.0 |
| direct:date_of_birth | 35 | 100.0 | 100.0 |
| indirect:occupation | 33 | 90.9 | 84.8 |
| direct:user_name | 32 | 100.0 | 100.0 |
| indirect:time | 31 | 100.0 | 93.5 |
| indirect:employment_status | 31 | 83.9 | 71.0 |
| direct:swift_bic | 29 | 100.0 | 100.0 |
| indirect:postcode | 28 | 100.0 | 100.0 |
| direct:ipv4 | 26 | 100.0 | 100.0 |
| direct:biometric_identifier | 26 | 100.0 | 100.0 |
| direct:ssn | 25 | 100.0 | 100.0 |
| direct:cvv | 23 | 100.0 | 100.0 |
| indirect:race_ethnicity | 20 | 100.0 | 100.0 |
| direct:health_plan_beneficiary_number | 19 | 100.0 | 100.0 |
| indirect:date_time | 18 | 100.0 | 100.0 |
| direct:http_cookie | 17 | 100.0 | 100.0 |
| direct:pin | 17 | 100.0 | 100.0 |
| indirect:blood_type | 17 | 52.9 | 52.9 |
| direct:fax_number | 17 | 100.0 | 100.0 |
| indirect:education_level | 14 | 100.0 | 85.7 |
| direct:tax_id | 14 | 100.0 | 100.0 |
| direct:password | 12 | 100.0 | 100.0 |
| indirect:county | 11 | 100.0 | 100.0 |
| direct:mac_address | 10 | 100.0 | 100.0 |
| direct:ipv6 | 10 | 100.0 | 100.0 |
| indirect:religious_belief | 10 | 100.0 | 100.0 |
| direct:employee_id | 9 | 100.0 | 100.0 |
| indirect:age | 8 | 100.0 | 100.0 |
| indirect:language | 8 | 100.0 | 100.0 |
| direct:coordinate | 8 | 100.0 | 100.0 |
| direct:medical_record_number | 8 | 100.0 | 100.0 |
| indirect:sexuality | 8 | 100.0 | 100.0 |
| indirect:political_view | 7 | 100.0 | 85.7 |
| direct:certificate_license_number | 7 | 100.0 | 100.0 |
| direct:api_key | 5 | 100.0 | 100.0 |
| direct:unique_id | 4 | 100.0 | 100.0 |
| direct:device_identifier | 3 | 100.0 | 100.0 |
| indirect:gender | 2 | 100.0 | 100.0 |
| direct:vehicle_identifier | 2 | 100.0 | 100.0 |
| direct:license_plate | 2 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Mortgage | 401 | 98.5 | 98.0 |
| Investment | 342 | 99.4 | 98.5 |
| Banking | 337 | 100.0 | 99.4 |
| User Account and Transaction Services | 282 | 99.6 | 99.3 |
| Brokerage | 279 | 100.0 | 99.6 |
| Insurance | 214 | 95.8 | 94.4 |
| Credit | 214 | 98.6 | 98.6 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 24953 | 91.9 |
| tier:indirect | 12759 | 51.3 |
| CONTACT | 9074 | 99.2 |
| DEMOGRAPHIC | 7087 | 24.1 |
| FIN_ID | 5293 | 97.1 |
| ADDRESS | 3201 | 87.2 |
| ORG | 3085 | 80.4 |
| NAME | 2824 | 87.2 |
| SECRET | 2706 | 64.6 |
| DATE | 2587 | 91.1 |
| NETWORK | 951 | 97.7 |
| GOV_ID | 904 | 95.0 |

## dev_nemotron_fin_structured (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 378 | 99.2 | 99.2 |
| NAME | 310 | 100.0 | 100.0 |
| DATE | 274 | 97.4 | 94.2 |
| ADDRESS | 189 | 92.6 | 91.5 |
| CONTACT | 171 | 100.0 | 100.0 |
| ORG | 135 | 98.5 | 98.5 |
| GOV_ID | 98 | 100.0 | 100.0 |
| DEMOGRAPHIC | 98 | 76.5 | 70.4 |
| SECRET | 25 | 100.0 | 88.0 |
| NETWORK | 19 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:date | 193 | 97.4 | 93.3 |
| direct:first_name | 164 | 100.0 | 100.0 |
| indirect:company_name | 135 | 98.5 | 98.5 |
| direct:last_name | 124 | 100.0 | 100.0 |
| direct:account_number | 121 | 100.0 | 100.0 |
| direct:customer_id | 86 | 100.0 | 100.0 |
| direct:email | 82 | 100.0 | 100.0 |
| direct:street_address | 59 | 100.0 | 100.0 |
| direct:credit_debit_card | 56 | 100.0 | 100.0 |
| direct:url | 50 | 100.0 | 100.0 |
| direct:bank_routing_number | 46 | 100.0 | 100.0 |
| indirect:country | 35 | 100.0 | 100.0 |
| direct:phone_number | 31 | 100.0 | 100.0 |
| direct:date_of_birth | 30 | 100.0 | 100.0 |
| indirect:occupation | 29 | 48.3 | 41.4 |
| indirect:time | 28 | 96.4 | 92.9 |
| indirect:state | 28 | 89.3 | 89.3 |
| direct:ssn | 27 | 100.0 | 100.0 |
| direct:cvv | 27 | 88.9 | 88.9 |
| direct:biometric_identifier | 25 | 100.0 | 100.0 |
| indirect:city | 23 | 100.0 | 95.7 |
| indirect:date_time | 23 | 95.7 | 95.7 |
| indirect:county | 22 | 50.0 | 50.0 |
| direct:user_name | 22 | 100.0 | 100.0 |
| indirect:postcode | 19 | 100.0 | 94.7 |
| direct:pin | 16 | 100.0 | 100.0 |
| indirect:employment_status | 15 | 80.0 | 80.0 |
| direct:medical_record_number | 15 | 100.0 | 100.0 |
| indirect:blood_type | 14 | 71.4 | 64.3 |
| direct:swift_bic | 13 | 100.0 | 100.0 |
| direct:password | 12 | 100.0 | 75.0 |
| indirect:race_ethnicity | 11 | 100.0 | 90.9 |
| direct:ipv4 | 10 | 100.0 | 100.0 |
| direct:http_cookie | 9 | 100.0 | 100.0 |
| direct:health_plan_beneficiary_number | 8 | 100.0 | 100.0 |
| direct:employee_id | 8 | 100.0 | 100.0 |
| direct:fax_number | 8 | 100.0 | 100.0 |
| indirect:language | 8 | 87.5 | 87.5 |
| direct:tax_id | 8 | 100.0 | 100.0 |
| indirect:religious_belief | 6 | 100.0 | 66.7 |
| direct:certificate_license_number | 6 | 100.0 | 100.0 |
| direct:national_id | 6 | 100.0 | 100.0 |
| direct:ipv6 | 5 | 100.0 | 100.0 |
| direct:unique_id | 5 | 100.0 | 100.0 |
| indirect:age | 5 | 100.0 | 100.0 |
| indirect:gender | 4 | 100.0 | 100.0 |
| direct:api_key | 4 | 100.0 | 100.0 |
| direct:coordinate | 3 | 100.0 | 100.0 |
| indirect:education_level | 3 | 100.0 | 100.0 |
| indirect:political_view | 3 | 100.0 | 100.0 |
| direct:device_identifier | 2 | 100.0 | 100.0 |
| direct:mac_address | 2 | 100.0 | 100.0 |
| direct:vehicle_identifier | 2 | 100.0 | 100.0 |
| direct:license_plate | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Risk Assessment | 33 | 100.0 | 100.0 |
| Affidavit of No Unpaid Assessments | 32 | 96.9 | 96.9 |
| Investment Strategy | 29 | 100.0 | 100.0 |
| Credit Policy Document | 27 | 100.0 | 100.0 |
| Trade Authorization | 26 | 88.5 | 80.8 |
| Medical Records Release Form | 25 | 100.0 | 96.0 |
| Investment Policy Statement | 24 | 100.0 | 100.0 |
| Investment Objectives | 22 | 100.0 | 100.0 |
| Market Analysis Report | 22 | 90.9 | 86.4 |
| Insurance Endorsement | 22 | 100.0 | 95.5 |
| Investment Forecast | 22 | 100.0 | 100.0 |
| Investment Review | 22 | 86.4 | 81.8 |
| System Diagnostic Log | 22 | 100.0 | 100.0 |
| blood bank inventory record | 21 | 71.4 | 71.4 |
| Account Closing Form | 21 | 100.0 | 100.0 |
| Quitclaim Deed | 20 | 90.0 | 90.0 |
| Incident Report | 20 | 100.0 | 100.0 |
| Investment Proposal | 20 | 100.0 | 100.0 |
| Insurance Compliance Report | 19 | 100.0 | 100.0 |
| Driver License | 19 | 100.0 | 100.0 |
| Debt Settlement Plan | 19 | 100.0 | 100.0 |
| Affidavit of No Unpaid Liabilities | 19 | 78.9 | 78.9 |
| Reinsurance Agreement | 19 | 100.0 | 100.0 |
| Affidavit of Title | 18 | 100.0 | 100.0 |
| clinical trial participant biometric file | 17 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 17843 | 91.1 |
| tier:indirect | 11938 | 54.4 |
| CONTACT | 6174 | 97.4 |
| ORG | 4781 | 60.2 |
| FIN_ID | 4351 | 95.4 |
| DEMOGRAPHIC | 4006 | 19.3 |
| DATE | 3151 | 90.3 |
| ADDRESS | 2404 | 83.7 |
| NAME | 2114 | 92.3 |
| SECRET | 1810 | 63.1 |
| GOV_ID | 638 | 99.4 |
| NETWORK | 352 | 99.4 |

## Notes, caveats and negative results

**How to read the precision numbers.** Precision counts a redacted character as correct only if the dataset labels
it. Gretel labels no demographics at all and only some dates, places and organisations, so real quasi-identifiers
("Software Engineer", "New York", "December 31, 2021") count as errors there. On the dev split, DEMOGRAPHIC and
unlabelled DATE/ADDRESS findings are roughly half of all "false" characters. Nemotron labels these categories and
is the better guide to true precision.

**Manual audit of "false positives" (Gretel dev, 100 random findings that the labels do not cover, seed 7).**
Judged by hand: about 27 are real identifiers the dataset simply does not label (routing and policy numbers, IBAN
and BIC fragments, LEIs, e-mail addresses, transaction timestamps, ZIP codes, a person's occupation); about 8 are
debatable (governing-law jurisdictions, "Monday through Friday"); about 65 are genuine over-redaction. Of those 65,
roughly 30 are GLiNER `occupation`/demographic guesses on ordinary noun phrases ("Corporate Governance Guidelines",
"industry experts") and roughly 14 are GLiNER `password`/`api key` guesses ("transaction history", "prompts").
So about a third of the measured false positives are not errors, and two GLiNER labels cause most of the rest. This
is a small single-rater sample on a dev set: treat it as an indication, not a measurement.

**What did not work, or worked less than hoped**

* *Per-type confidence thresholds (B2).* Calibrated on the dev sets under the stated constraint (keep each type's
  recall at ≥ 99% of its value): about +1 point of precision. GLiNER's low-score findings are what carry recall for
  names and organisations on Gretel, so almost no threshold survives the recall constraint. Only two were kept.
* *"Unsupported finding" thresholds* (drop a GLiNER finding that no rule and no other model overlaps when its score
  is under a per-label threshold): about +3 points on every dev set with recall unchanged. The biggest offender,
  GLiNER's `occupation` label (9 true vs 550 false lone findings on the Nemotron dev sets), could NOT be thresholded
  without breaking the 99% constraint for DEMOGRAPHIC recall, so it stays.
* *Propagating only confident findings.* +1 point of precision, but it left other occurrences of a redacted value
  visible, i.e. it broke the zero-leak invariant (131 leak-check failures on the headline set). Reverted.
* *Precision targets (Gretel ≥ 55%, Nemotron ≥ 85%) are not met.* See the summary table. Reaching them with this
  ensemble would require giving up indirect recall (dropping demographics or unlabelled dates), which the ground
  rules forbid.
* *Raw-label direct recall ≥ 99% on Gretel is not met* (see table). On the dev split every remaining ≥50% miss was
  inspected: they are label noise ("Corporation" and "Complainant" labelled as names, "[Employee's Name]",
  "MM/DD/YYYY") plus one document with a bare 4-digit PIN in an MT940 line. Held-out misses were not inspected.

**Policy-adjusted labels.** `bench/gold_policy.py` now also excludes generic terms ("Borrower", "Company"), public
bodies and reporting periods ("Q3 2025"), reusing the lists the product ships, because the product deliberately does
not redact them. This makes the policy number a measure of "did we redact what we intend to redact". It cannot
validate the intent itself; the raw column next to it is there for that.

**Held-out hygiene.** Rules, word lists and thresholds were tuned only on the three dev sets and on the hand-built
regression set. `eval_gretel_fin_holdout` predates this work (the legacy part of the policy may have been informed
by it); `eval_fin_holdout2`, `eval_nemotron_fin_structured` and `eval_gretel_en` were built here and never opened.

**Latency columns** are measured inside 4 single-threaded worker processes running concurrently; the API uses
`MODEL_THREADS` intra-op threads per request instead, see `bench/out/load.md`.
