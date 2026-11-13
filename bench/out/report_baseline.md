# redactd benchmark report

Generated 2026-11-13 04:49 UTC · mode **thorough** · shipped `redactd.pipeline.Pipeline` · 4 worker processes × 1 thread · total wall time 17.3 min

Recall = share of gold identifiers with ≥50% / ≥90% of their characters redacted. Precision = share of redacted characters that fall inside a gold span (Gretel leaves real PII unlabelled, so its precision understates reality). *Raw* uses dataset labels as-is; *policy* removes gold spans that are template placeholders and, for organisation labels only, generic phrases and public bodies (`bench/gold_policy.py`).

**Held-out** sets are never used to tune rules, thresholds or prompts. **Dev** sets are.

## Summary

| Set | Role | Docs | Direct ≥50 raw | Direct ≥90 raw | Indirect ≥50 raw | Indirect ≥90 raw | Prec raw | Direct ≥50 pol | Direct ≥90 pol | Indirect ≥50 pol | Indirect ≥90 pol | Prec pol |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| eval_gretel_fin_holdout | held-out | 300 | 99.8 | 92.0 | 95.8 | 91.3 | 25.8 | 100.0 | 93.2 | 96.8 | 93.0 | 24.7 |
| eval_fin_holdout2 | held-out | 300 | 99.8 | 90.4 | 94.4 | 92.2 | 25.3 | 99.8 | 91.1 | 95.2 | 93.3 | 24.9 |
| eval_nemotron_fin_structured | held-out | 300 | 99.6 | 99.2 | 95.4 | 94.7 | 64.2 | 99.6 | 99.2 | 96.4 | 96.0 | 63.8 |
| eval_gretel_en | held-out | 300 | 100.0 | 98.8 | 100.0 | 99.0 | 70.8 | 100.0 | 98.8 | 100.0 | 99.0 | 70.8 |
| eval_adversarial | held-out | 160 | 98.0 | 97.2 | 100.0 | 100.0 | 69.1 | 98.0 | 97.2 | 100.0 | 100.0 | 69.1 |
| eval_gretel_fin | dev | 200 | 99.0 | 90.3 | 99.5 | 97.8 | 26.0 | 99.1 | 90.9 | 99.4 | 98.0 | 24.7 |
| eval_nemotron_fin | dev | 300 | 99.9 | 99.7 | 98.5 | 97.9 | 63.3 | 99.9 | 99.7 | 98.5 | 98.2 | 63.3 |
| dev_nemotron_fin_structured | dev | 200 | 100.0 | 99.5 | 96.5 | 95.2 | 61.9 | 100.0 | 99.5 | 96.4 | 95.9 | 61.2 |

## Leak regression (A3)

`leak_check` must be empty for every rendered document. *Gold direct values in output* is a raw string search of the redacted output for every gold DIRECT value; it counts every miss and also short values that survive as substrings of unrelated words.

| Set | leak_check failures | Gold direct values still in output | of | Docs affected |
|---|---:|---:|---:|---:|
| eval_gretel_fin_holdout | 3 | 0 | 773 | 0 / 300 |
| eval_fin_holdout2 | 2 | 1 | 720 | 1 / 300 |
| eval_nemotron_fin_structured | 1 | 4 | 1287 | 4 / 300 |
| eval_gretel_en | 0 | 0 | 1214 | 0 / 300 |
| eval_adversarial | 5 | 0 | 592 | 0 / 160 |
| eval_gretel_fin | 2 | 2 | 513 | 2 / 200 |
| eval_nemotron_fin | 0 | 1 | 1270 | 1 / 300 |
| dev_nemotron_fin_structured | 1 | 0 | 824 | 0 / 200 |

## Latency (per document, measured inside the worker; all workers busy)

| Set | mean chars | p50 ms | p95 ms | p99 ms | ms / 1k chars | stage share |
|---|---:|---:|---:|---:|---:|---|
| eval_gretel_fin_holdout | 1399 | 2749 | 4454 | 6524 | 1960 | rules 0%, openmed 20%, gliner 79% |
| eval_fin_holdout2 | 1427 | 2966 | 4113 | 6702 | 1960 | rules 0%, openmed 21%, gliner 79% |
| eval_nemotron_fin_structured | 1087 | 2012 | 4695 | 6350 | 2119 | rules 0%, openmed 21%, gliner 79% |
| eval_gretel_en | 214 | 689 | 1383 | 1908 | 3656 | rules 0%, openmed 16%, gliner 84% |
| eval_adversarial | 147 | 626 | 1066 | 1400 | 4530 | rules 0%, openmed 15%, gliner 84% |
| eval_gretel_fin | 1481 | 2886 | 4588 | 6728 | 1894 | rules 0%, openmed 20%, gliner 79% |
| eval_nemotron_fin | 615 | 1152 | 2468 | 3018 | 2062 | rules 0%, openmed 17%, gliner 83% |
| dev_nemotron_fin_structured | 1031 | 1876 | 4348 | 8142 | 2125 | rules 0%, openmed 20%, gliner 79% |

## eval_gretel_fin_holdout (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 439 | 99.8 | 98.4 |
| ORG | 437 | 97.3 | 92.2 |
| ADDRESS | 244 | 100.0 | 74.2 |
| DATE | 130 | 91.5 | 89.2 |
| CONTACT | 125 | 99.2 | 95.2 |
| FIN_ID | 94 | 100.0 | 100.0 |
| NETWORK | 19 | 100.0 | 100.0 |
| GOV_ID | 15 | 100.0 | 100.0 |
| SECRET | 10 | 100.0 | 90.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 437 | 97.3 | 92.2 |
| direct:name | 406 | 99.8 | 98.3 |
| direct:street_address | 240 | 100.0 | 74.6 |
| indirect:date | 85 | 100.0 | 97.6 |
| direct:phone_number | 81 | 98.8 | 96.3 |
| direct:email | 44 | 100.0 | 93.2 |
| indirect:time | 25 | 56.0 | 52.0 |
| direct:swift_bic_code | 18 | 100.0 | 100.0 |
| direct:last_name | 16 | 100.0 | 100.0 |
| direct:date_of_birth | 16 | 100.0 | 100.0 |
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
| direct:password | 6 | 100.0 | 83.3 |
| direct:passport_number | 5 | 100.0 | 100.0 |
| direct:credit_card_security_code | 5 | 100.0 | 100.0 |
| direct:local_latlng | 4 | 100.0 | 50.0 |
| direct:api_key | 4 | 100.0 | 100.0 |
| indirect:date_time | 4 | 100.0 | 100.0 |
| direct:user_name | 3 | 100.0 | 100.0 |
| direct:driver_license_number | 2 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Bill of Lading | 98 | 100.0 | 92.9 |
| CSV | 89 | 100.0 | 98.9 |
| IT support ticket | 74 | 98.6 | 94.6 |
| Loan Application | 73 | 100.0 | 87.7 |
| Health Insurance Claim Form | 65 | 98.5 | 80.0 |
| Business Plan | 61 | 100.0 | 100.0 |
| ISDA Definition | 61 | 98.4 | 88.5 |
| Insurance Claim Form | 48 | 95.8 | 85.4 |
| Policyholder's Report | 43 | 100.0 | 90.7 |
| Payment Confirmation | 42 | 100.0 | 97.6 |
| FpML | 38 | 100.0 | 100.0 |
| Financial Aid Application | 38 | 92.1 | 92.1 |
| SWIFT Message | 38 | 100.0 | 89.5 |
| Trade Confirmation | 37 | 100.0 | 86.5 |
| Safety Data Sheet | 36 | 75.0 | 66.7 |
| Customer support conversational log | 36 | 100.0 | 97.2 |
| Email | 34 | 100.0 | 97.1 |
| Regulatory Filing | 33 | 100.0 | 87.9 |
| Financial Statement | 33 | 100.0 | 97.0 |
| EDI | 31 | 100.0 | 93.5 |
| Insurance Policy | 30 | 100.0 | 90.0 |
| Tax Return | 24 | 100.0 | 91.7 |
| Financial Risk Assessment | 22 | 100.0 | 100.0 |
| Compliance Certificate | 22 | 100.0 | 100.0 |
| Corporate Governance Guidelines | 21 | 90.5 | 90.5 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 52407 | 31.2 |
| tier:indirect | 48897 | 17.7 |
| DEMOGRAPHIC | 26576 | 2.3 |
| CONTACT | 15431 | 13.9 |
| ADDRESS | 14411 | 45.0 |
| ORG | 14011 | 46.8 |
| NAME | 9127 | 58.9 |
| DATE | 8310 | 18.0 |
| SECRET | 6198 | 4.6 |
| FIN_ID | 4841 | 27.9 |
| GOV_ID | 1512 | 8.6 |
| NETWORK | 887 | 65.1 |

## eval_fin_holdout2 (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| ORG | 413 | 93.9 | 91.8 |
| NAME | 396 | 100.0 | 98.2 |
| ADDRESS | 271 | 100.0 | 72.0 |
| DATE | 156 | 95.5 | 93.6 |
| FIN_ID | 96 | 100.0 | 100.0 |
| CONTACT | 81 | 100.0 | 97.5 |
| GOV_ID | 21 | 95.2 | 95.2 |
| NETWORK | 15 | 100.0 | 100.0 |
| SECRET | 7 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 413 | 93.9 | 91.8 |
| direct:name | 376 | 100.0 | 98.1 |
| direct:street_address | 267 | 100.0 | 71.5 |
| indirect:date | 110 | 99.1 | 99.1 |
| direct:phone_number | 49 | 100.0 | 98.0 |
| direct:email | 32 | 100.0 | 96.9 |
| indirect:time | 24 | 79.2 | 66.7 |
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
| direct:ssn | 7 | 85.7 | 85.7 |
| direct:account_pin | 7 | 100.0 | 100.0 |
| direct:driver_license_number | 7 | 100.0 | 100.0 |
| direct:first_name | 5 | 100.0 | 100.0 |
| direct:credit_card_security_code | 5 | 100.0 | 100.0 |
| direct:user_name | 5 | 100.0 | 100.0 |
| direct:password | 4 | 100.0 | 100.0 |
| direct:local_latlng | 4 | 100.0 | 100.0 |
| direct:iban | 4 | 100.0 | 100.0 |
| direct:api_key | 3 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Insurance Policy | 91 | 100.0 | 95.6 |
| Bill of Lading | 86 | 97.7 | 93.0 |
| CSV | 66 | 100.0 | 100.0 |
| Payment Confirmation | 64 | 100.0 | 95.3 |
| IT support ticket | 54 | 100.0 | 100.0 |
| Customer support conversational log | 49 | 100.0 | 100.0 |
| Health Insurance Claim Form | 45 | 100.0 | 75.6 |
| Loan Application | 44 | 97.7 | 90.9 |
| Credit Card Statement | 36 | 100.0 | 100.0 |
| Shareholder Agreement | 35 | 97.1 | 88.6 |
| Investment Prospectus | 34 | 97.1 | 97.1 |
| Audit Report | 32 | 100.0 | 100.0 |
| BAI Format | 32 | 100.0 | 100.0 |
| FIX Protocol | 31 | 96.8 | 87.1 |
| SWIFT Message | 31 | 100.0 | 87.1 |
| Safety Data Sheet | 30 | 73.3 | 70.0 |
| Tax Return | 30 | 100.0 | 96.7 |
| Real Estate Loan Agreement | 29 | 100.0 | 72.4 |
| Policyholder's Report | 29 | 100.0 | 93.1 |
| Transaction Confirmation | 28 | 100.0 | 71.4 |
| Compliance Certificate | 27 | 100.0 | 96.3 |
| ISDA Definition | 26 | 96.2 | 80.8 |
| Insurance Claim Form | 25 | 100.0 | 92.0 |
| MT940 | 25 | 100.0 | 96.0 |
| Annual Report | 24 | 100.0 | 87.5 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 52814 | 30.5 |
| tier:indirect | 50018 | 19.0 |
| DEMOGRAPHIC | 26858 | 1.3 |
| ADDRESS | 15446 | 48.4 |
| ORG | 15406 | 47.0 |
| CONTACT | 15216 | 9.7 |
| NAME | 8430 | 60.7 |
| DATE | 7754 | 24.4 |
| SECRET | 6599 | 3.5 |
| FIN_ID | 5375 | 22.2 |
| GOV_ID | 1090 | 17.5 |
| NETWORK | 658 | 61.7 |

## eval_nemotron_fin_structured (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 586 | 99.1 | 99.0 |
| NAME | 498 | 100.0 | 100.0 |
| DATE | 414 | 94.9 | 94.4 |
| CONTACT | 348 | 99.7 | 99.7 |
| ADDRESS | 322 | 98.4 | 96.6 |
| ORG | 225 | 100.0 | 99.6 |
| DEMOGRAPHIC | 176 | 88.1 | 86.9 |
| GOV_ID | 130 | 100.0 | 100.0 |
| SECRET | 47 | 100.0 | 93.6 |
| NETWORK | 28 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:date | 312 | 93.9 | 93.3 |
| direct:first_name | 248 | 100.0 | 100.0 |
| indirect:company_name | 225 | 100.0 | 99.6 |
| direct:last_name | 218 | 100.0 | 100.0 |
| direct:account_number | 189 | 100.0 | 99.5 |
| direct:email | 174 | 99.4 | 99.4 |
| direct:customer_id | 110 | 100.0 | 100.0 |
| direct:credit_debit_card | 102 | 100.0 | 100.0 |
| direct:street_address | 95 | 98.9 | 94.7 |
| indirect:occupation | 94 | 79.8 | 77.7 |
| direct:url | 83 | 100.0 | 100.0 |
| direct:bank_routing_number | 75 | 100.0 | 100.0 |
| direct:phone_number | 71 | 100.0 | 100.0 |
| indirect:state | 61 | 96.7 | 95.1 |
| indirect:country | 52 | 98.1 | 98.1 |
| indirect:city | 50 | 100.0 | 100.0 |
| direct:ssn | 44 | 100.0 | 100.0 |
| direct:swift_bic | 41 | 100.0 | 100.0 |
| indirect:time | 40 | 97.5 | 97.5 |
| direct:date_of_birth | 36 | 100.0 | 100.0 |
| indirect:county | 35 | 97.1 | 94.3 |
| direct:cvv | 33 | 97.0 | 97.0 |
| direct:user_name | 32 | 100.0 | 100.0 |
| direct:biometric_identifier | 31 | 100.0 | 100.0 |
| direct:password | 29 | 100.0 | 96.6 |
| indirect:postcode | 29 | 100.0 | 100.0 |
| indirect:date_time | 26 | 96.2 | 96.2 |
| indirect:employment_status | 21 | 100.0 | 100.0 |
| direct:fax_number | 20 | 100.0 | 100.0 |
| direct:pin | 20 | 80.0 | 80.0 |
| direct:health_plan_beneficiary_number | 19 | 100.0 | 100.0 |
| direct:tax_id | 14 | 100.0 | 100.0 |
| indirect:education_level | 13 | 100.0 | 100.0 |
| direct:ipv4 | 11 | 100.0 | 100.0 |
| indirect:language | 10 | 90.0 | 90.0 |
| indirect:race_ethnicity | 10 | 100.0 | 100.0 |
| direct:medical_record_number | 10 | 100.0 | 100.0 |
| direct:api_key | 10 | 100.0 | 100.0 |
| indirect:age | 9 | 88.9 | 88.9 |
| direct:employee_id | 9 | 100.0 | 100.0 |
| direct:http_cookie | 8 | 100.0 | 75.0 |
| direct:mac_address | 8 | 100.0 | 100.0 |
| indirect:political_view | 7 | 100.0 | 100.0 |
| direct:unique_id | 7 | 100.0 | 100.0 |
| direct:ipv6 | 6 | 100.0 | 100.0 |
| direct:national_id | 5 | 100.0 | 100.0 |
| direct:certificate_license_number | 5 | 100.0 | 100.0 |
| indirect:religious_belief | 4 | 100.0 | 100.0 |
| indirect:gender | 4 | 100.0 | 100.0 |
| direct:device_identifier | 3 | 100.0 | 100.0 |
| indirect:blood_type | 2 | 100.0 | 100.0 |
| indirect:sexuality | 2 | 100.0 | 100.0 |
| direct:license_plate | 1 | 100.0 | 100.0 |
| direct:vehicle_identifier | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Investment Agreement | 58 | 100.0 | 100.0 |
| Mortgage Loan | 54 | 96.3 | 96.3 |
| Premium Payment Schedule | 48 | 91.7 | 91.7 |
| Emergency Planning | 44 | 100.0 | 100.0 |
| Corporate Solutions | 41 | 97.6 | 97.6 |
| Affidavit of No Contingencies | 40 | 100.0 | 100.0 |
| Privacy Policy Document | 39 | 100.0 | 100.0 |
| Investment Statement | 38 | 100.0 | 100.0 |
| Bank Services | 35 | 100.0 | 97.1 |
| Audit Report | 34 | 100.0 | 97.1 |
| Affidavit of No Unpaid Insurance Premiums | 34 | 100.0 | 100.0 |
| Debt Consolidation Agreement | 33 | 100.0 | 100.0 |
| Investment Proposal | 33 | 100.0 | 100.0 |
| Investment Strategy | 32 | 100.0 | 100.0 |
| Affidavit of Title | 31 | 100.0 | 100.0 |
| Due Diligence Report | 30 | 100.0 | 100.0 |
| Affidavit of No Unpaid Maintenance Fees | 30 | 100.0 | 93.3 |
| Credit Card Replacement Form | 29 | 89.7 | 89.7 |
| Application Setup Guide | 29 | 100.0 | 100.0 |
| Investment Evaluation | 29 | 96.6 | 96.6 |
| Risk Management Plan | 27 | 100.0 | 100.0 |
| Authorization Form | 27 | 70.4 | 70.4 |
| Investment Portfolio | 26 | 100.0 | 100.0 |
| Personal Identification | 26 | 100.0 | 100.0 |
| Power of Attorney | 26 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 36369 | 76.0 |
| tier:indirect | 22981 | 44.5 |
| CONTACT | 13832 | 84.5 |
| DEMOGRAPHIC | 10125 | 19.1 |
| ORG | 7491 | 55.0 |
| FIN_ID | 7333 | 86.9 |
| DATE | 5365 | 77.6 |
| SECRET | 4759 | 28.3 |
| ADDRESS | 4667 | 77.8 |
| NAME | 4372 | 73.9 |
| GOV_ID | 897 | 95.9 |
| NETWORK | 509 | 100.0 |

## eval_gretel_en (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| GOV_ID | 314 | 100.0 | 100.0 |
| NAME | 258 | 100.0 | 99.6 |
| DATE | 221 | 100.0 | 100.0 |
| FIN_ID | 194 | 100.0 | 100.0 |
| CONTACT | 128 | 100.0 | 100.0 |
| ADDRESS | 107 | 100.0 | 87.9 |
| NETWORK | 73 | 100.0 | 100.0 |
| ORG | 10 | 100.0 | 90.0 |
| SECRET | 8 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:medical_record_number | 155 | 100.0 | 100.0 |
| direct:date_of_birth | 144 | 100.0 | 100.0 |
| direct:ssn | 107 | 100.0 | 100.0 |
| direct:first_name | 97 | 100.0 | 100.0 |
| direct:last_name | 92 | 100.0 | 100.0 |
| direct:street_address | 90 | 100.0 | 85.6 |
| direct:employee_id | 70 | 100.0 | 100.0 |
| direct:email | 70 | 100.0 | 100.0 |
| indirect:date | 62 | 100.0 | 100.0 |
| direct:name | 57 | 100.0 | 98.2 |
| direct:customer_id | 57 | 100.0 | 100.0 |
| direct:phone_number | 56 | 100.0 | 100.0 |
| direct:ipv4 | 50 | 100.0 | 100.0 |
| direct:license_plate | 33 | 100.0 | 100.0 |
| direct:credit_card_number | 31 | 100.0 | 100.0 |
| direct:device_identifier | 20 | 100.0 | 100.0 |
| direct:bank_routing_number | 18 | 100.0 | 100.0 |
| direct:user_name | 12 | 100.0 | 100.0 |
| indirect:company_name | 10 | 100.0 | 90.0 |
| direct:account_number | 9 | 100.0 | 100.0 |
| direct:unique_id | 9 | 100.0 | 100.0 |
| indirect:date_time | 8 | 100.0 | 100.0 |
| indirect:time | 7 | 100.0 | 100.0 |
| direct:api_key | 6 | 100.0 | 100.0 |
| direct:vehicle_identifier | 6 | 100.0 | 100.0 |
| direct:coordinate | 5 | 100.0 | 100.0 |
| direct:biometric_identifier | 4 | 100.0 | 100.0 |
| indirect:postcode | 4 | 100.0 | 100.0 |
| indirect:city | 4 | 100.0 | 100.0 |
| direct:certificate_license_number | 4 | 100.0 | 100.0 |
| indirect:country | 3 | 100.0 | 100.0 |
| direct:ipv6 | 3 | 100.0 | 100.0 |
| direct:password | 2 | 100.0 | 100.0 |
| direct:national_id | 2 | 100.0 | 100.0 |
| direct:health_plan_beneficiary_number | 2 | 100.0 | 100.0 |
| direct:url | 2 | 100.0 | 100.0 |
| indirect:state | 1 | 100.0 | 100.0 |
| direct:tax_id | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Invoice | 18 | 100.0 | 94.4 |
| Vulnerability Assessment Report | 17 | 100.0 | 100.0 |
| Router Configuration | 15 | 100.0 | 100.0 |
| TransportationContract | 14 | 100.0 | 92.9 |
| InvestmentAccountStatement | 13 | 100.0 | 100.0 |
| Service Level Description | 13 | 100.0 | 92.3 |
| PatientIntakeForm | 12 | 100.0 | 100.0 |
| MedicalHistoryForm | 12 | 100.0 | 100.0 |
| E-Ticket | 11 | 100.0 | 100.0 |
| Certificate Practice Statement | 11 | 100.0 | 100.0 |
| ClaimForm | 11 | 100.0 | 100.0 |
| InstallationReport | 10 | 100.0 | 90.0 |
| UserManual | 10 | 100.0 | 100.0 |
| Voter Registration Form | 10 | 100.0 | 100.0 |
| LoanAgreement | 10 | 100.0 | 100.0 |
| BillOfLading | 9 | 100.0 | 88.9 |
| Termination Agreement | 9 | 100.0 | 100.0 |
| Vaccination Record | 9 | 100.0 | 100.0 |
| Classified Document | 9 | 100.0 | 100.0 |
| AvionicsManual | 9 | 100.0 | 100.0 |
| TroubleshootingReport | 9 | 100.0 | 100.0 |
| PackingSlip | 9 | 100.0 | 88.9 |
| TaxReturnForm | 9 | 100.0 | 100.0 |
| QualityControlReport | 9 | 100.0 | 100.0 |
| ProductionSchedule | 8 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 17571 | 82.2 |
| tier:indirect | 6596 | 40.3 |
| FIN_ID | 4201 | 90.9 |
| CONTACT | 3315 | 72.2 |
| DATE | 3197 | 76.5 |
| ADDRESS | 3171 | 92.6 |
| NAME | 3119 | 80.3 |
| DEMOGRAPHIC | 2850 | 0.0 |
| GOV_ID | 1647 | 97.3 |
| SECRET | 1271 | 31.5 |
| NETWORK | 847 | 93.5 |
| ORG | 549 | 38.4 |

## eval_adversarial (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 224 | 100.0 | 99.6 |
| FIN_ID | 220 | 96.4 | 95.0 |
| ADDRESS | 112 | 100.0 | 99.1 |
| CONTACT | 80 | 100.0 | 100.0 |
| DATE | 28 | 100.0 | 100.0 |
| GOV_ID | 24 | 83.3 | 83.3 |
| ORG | 16 | 100.0 | 100.0 |
| SECRET | 4 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:name | 132 | 100.0 | 99.2 |
| direct:account_number | 76 | 100.0 | 100.0 |
| direct:iban | 60 | 93.3 | 93.3 |
| direct:first_name | 52 | 100.0 | 100.0 |
| direct:phone_number | 44 | 100.0 | 100.0 |
| direct:street_address | 40 | 100.0 | 97.5 |
| indirect:city | 40 | 100.0 | 100.0 |
| direct:last_name | 36 | 100.0 | 100.0 |
| direct:email | 36 | 100.0 | 100.0 |
| direct:credit_debit_card | 32 | 87.5 | 78.1 |
| indirect:postcode | 28 | 100.0 | 100.0 |
| indirect:date | 20 | 100.0 | 100.0 |
| direct:customer_id | 20 | 100.0 | 100.0 |
| direct:swift_bic | 20 | 100.0 | 100.0 |
| indirect:company | 16 | 100.0 | 100.0 |
| direct:ssn | 12 | 66.7 | 66.7 |
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
| international formats | 124 | 100.0 | 99.2 |
| structured keys | 92 | 100.0 | 100.0 |
| email threads | 76 | 100.0 | 98.7 |
| SWIFT / FIX | 64 | 100.0 | 100.0 |
| common-word names | 56 | 100.0 | 100.0 |
| masked partials | 56 | 78.6 | 73.2 |
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
| templates also rendered (other values) for training | 356 | 98.9 | 98.6 |
| templates never used in training | 352 | 97.7 | 96.6 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 10747 | 75.7 |
| FIN_ID | 3605 | 73.0 |
| tier:indirect | 2652 | 42.6 |
| NAME | 2300 | 89.5 |
| CONTACT | 2235 | 86.0 |
| ADDRESS | 1532 | 78.8 |
| DEMOGRAPHIC | 966 | 1.6 |
| ORG | 958 | 66.6 |
| SECRET | 819 | 12.3 |
| DATE | 728 | 65.4 |
| GOV_ID | 215 | 98.1 |
| NETWORK | 41 | 0.0 |

## eval_gretel_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 304 | 100.0 | 98.0 |
| ORG | 284 | 99.6 | 97.9 |
| ADDRESS | 200 | 100.0 | 74.0 |
| DATE | 94 | 97.9 | 96.8 |
| CONTACT | 69 | 98.6 | 95.7 |
| FIN_ID | 65 | 92.3 | 92.3 |
| GOV_ID | 19 | 100.0 | 100.0 |
| NETWORK | 11 | 100.0 | 100.0 |
| SECRET | 11 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 284 | 99.6 | 97.9 |
| direct:name | 271 | 100.0 | 97.8 |
| direct:street_address | 191 | 100.0 | 74.3 |
| indirect:date | 68 | 100.0 | 100.0 |
| direct:email | 36 | 100.0 | 100.0 |
| direct:phone_number | 33 | 97.0 | 90.9 |
| direct:first_name | 31 | 100.0 | 100.0 |
| indirect:time | 13 | 92.3 | 84.6 |
| direct:account_pin | 12 | 58.3 | 58.3 |
| direct:date_of_birth | 11 | 90.9 | 90.9 |
| direct:credit_card_security_code | 10 | 100.0 | 100.0 |
| direct:employee_id | 10 | 100.0 | 100.0 |
| direct:local_latlng | 9 | 100.0 | 66.7 |
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
| Loan Application | 101 | 100.0 | 88.1 |
| BAI Format | 50 | 100.0 | 96.0 |
| SWIFT Message | 47 | 100.0 | 93.6 |
| Policyholder's Report | 43 | 100.0 | 90.7 |
| IT support ticket | 39 | 97.4 | 89.7 |
| Customer support conversational log | 37 | 100.0 | 100.0 |
| Customer Agreement | 35 | 100.0 | 91.4 |
| Payment Confirmation | 31 | 100.0 | 83.9 |
| Audit Report | 31 | 100.0 | 100.0 |
| EDI | 31 | 100.0 | 93.5 |
| Supply Chain Management Agreement | 29 | 100.0 | 100.0 |
| FIX Protocol | 29 | 100.0 | 93.1 |
| Bill of Lading | 29 | 100.0 | 96.6 |
| Financial Risk Assessment | 25 | 100.0 | 96.0 |
| Regulatory Compliance Guide | 25 | 100.0 | 100.0 |
| Insurance Policy | 24 | 100.0 | 87.5 |
| Trade Confirmation | 23 | 100.0 | 78.3 |
| CSV | 21 | 100.0 | 100.0 |
| Financial Disclosure Statement | 21 | 100.0 | 100.0 |
| Compliance Certificate | 21 | 100.0 | 95.2 |
| MT940 | 17 | 70.6 | 70.6 |
| Employment Contract | 17 | 100.0 | 82.4 |
| Credit Card Statement | 16 | 100.0 | 100.0 |
| Email | 16 | 100.0 | 87.5 |
| Health Insurance Claim Form | 16 | 100.0 | 93.8 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 35355 | 31.4 |
| tier:indirect | 34549 | 17.9 |
| DEMOGRAPHIC | 19957 | 1.4 |
| ORG | 9772 | 47.6 |
| ADDRESS | 9573 | 53.8 |
| CONTACT | 9073 | 12.9 |
| NAME | 6139 | 55.4 |
| SECRET | 5259 | 4.7 |
| DATE | 4820 | 25.5 |
| FIN_ID | 3501 | 20.9 |
| GOV_ID | 1380 | 11.7 |
| NETWORK | 430 | 56.3 |

## eval_nemotron_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 480 | 100.0 | 100.0 |
| NAME | 370 | 100.0 | 100.0 |
| ADDRESS | 265 | 99.6 | 99.2 |
| CONTACT | 262 | 99.6 | 99.6 |
| DATE | 221 | 100.0 | 99.1 |
| DEMOGRAPHIC | 158 | 94.3 | 93.0 |
| ORG | 127 | 100.0 | 100.0 |
| GOV_ID | 103 | 100.0 | 100.0 |
| NETWORK | 49 | 100.0 | 100.0 |
| SECRET | 34 | 100.0 | 94.1 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:first_name | 194 | 100.0 | 100.0 |
| direct:account_number | 167 | 100.0 | 100.0 |
| direct:last_name | 144 | 100.0 | 100.0 |
| indirect:date | 137 | 100.0 | 98.5 |
| indirect:company_name | 127 | 100.0 | 100.0 |
| direct:email | 121 | 99.2 | 99.2 |
| direct:customer_id | 106 | 100.0 | 100.0 |
| direct:url | 81 | 100.0 | 100.0 |
| direct:street_address | 71 | 100.0 | 98.6 |
| indirect:country | 67 | 100.0 | 100.0 |
| direct:credit_debit_card | 64 | 100.0 | 100.0 |
| direct:bank_routing_number | 61 | 100.0 | 100.0 |
| indirect:state | 45 | 97.8 | 97.8 |
| direct:phone_number | 43 | 100.0 | 100.0 |
| indirect:city | 35 | 100.0 | 100.0 |
| direct:date_of_birth | 35 | 100.0 | 100.0 |
| indirect:occupation | 33 | 97.0 | 97.0 |
| direct:user_name | 32 | 100.0 | 100.0 |
| indirect:time | 31 | 100.0 | 100.0 |
| indirect:employment_status | 31 | 100.0 | 96.8 |
| direct:swift_bic | 29 | 100.0 | 100.0 |
| indirect:postcode | 28 | 100.0 | 100.0 |
| direct:ipv4 | 26 | 100.0 | 100.0 |
| direct:biometric_identifier | 26 | 100.0 | 100.0 |
| direct:ssn | 25 | 100.0 | 100.0 |
| direct:cvv | 23 | 100.0 | 100.0 |
| indirect:race_ethnicity | 20 | 100.0 | 100.0 |
| direct:health_plan_beneficiary_number | 19 | 100.0 | 100.0 |
| indirect:date_time | 18 | 100.0 | 100.0 |
| direct:http_cookie | 17 | 100.0 | 88.2 |
| direct:pin | 17 | 100.0 | 100.0 |
| indirect:blood_type | 17 | 58.8 | 58.8 |
| direct:fax_number | 17 | 100.0 | 100.0 |
| indirect:education_level | 14 | 100.0 | 92.9 |
| direct:tax_id | 14 | 100.0 | 100.0 |
| direct:password | 12 | 100.0 | 100.0 |
| indirect:county | 11 | 100.0 | 100.0 |
| direct:mac_address | 10 | 100.0 | 100.0 |
| direct:ipv6 | 10 | 100.0 | 100.0 |
| indirect:religious_belief | 10 | 90.0 | 90.0 |
| direct:employee_id | 9 | 100.0 | 100.0 |
| indirect:age | 8 | 100.0 | 100.0 |
| indirect:language | 8 | 100.0 | 100.0 |
| direct:coordinate | 8 | 100.0 | 100.0 |
| direct:medical_record_number | 8 | 100.0 | 100.0 |
| indirect:sexuality | 8 | 100.0 | 100.0 |
| indirect:political_view | 7 | 100.0 | 100.0 |
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
| Mortgage | 401 | 99.8 | 99.3 |
| Investment | 342 | 99.4 | 99.1 |
| Banking | 337 | 100.0 | 100.0 |
| User Account and Transaction Services | 282 | 100.0 | 99.6 |
| Brokerage | 279 | 100.0 | 99.6 |
| Insurance | 214 | 96.7 | 95.8 |
| Credit | 214 | 99.5 | 99.5 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 29635 | 77.1 |
| tier:indirect | 17044 | 39.1 |
| CONTACT | 10924 | 83.2 |
| DEMOGRAPHIC | 10125 | 16.9 |
| FIN_ID | 5853 | 89.1 |
| ORG | 4020 | 61.9 |
| NAME | 3941 | 64.7 |
| SECRET | 3758 | 40.4 |
| ADDRESS | 3407 | 86.3 |
| DATE | 2899 | 85.0 |
| NETWORK | 952 | 94.6 |
| GOV_ID | 800 | 81.4 |

## dev_nemotron_fin_structured (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 378 | 100.0 | 99.5 |
| NAME | 310 | 100.0 | 100.0 |
| DATE | 274 | 97.4 | 96.7 |
| ADDRESS | 189 | 100.0 | 96.3 |
| CONTACT | 171 | 100.0 | 100.0 |
| ORG | 135 | 98.5 | 98.5 |
| GOV_ID | 98 | 100.0 | 100.0 |
| DEMOGRAPHIC | 98 | 87.8 | 87.8 |
| SECRET | 25 | 100.0 | 92.0 |
| NETWORK | 19 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:date | 193 | 97.9 | 96.9 |
| direct:first_name | 164 | 100.0 | 100.0 |
| indirect:company_name | 135 | 98.5 | 98.5 |
| direct:last_name | 124 | 100.0 | 100.0 |
| direct:account_number | 121 | 100.0 | 100.0 |
| direct:customer_id | 86 | 100.0 | 100.0 |
| direct:email | 82 | 100.0 | 100.0 |
| direct:street_address | 59 | 100.0 | 98.3 |
| direct:credit_debit_card | 56 | 100.0 | 96.4 |
| direct:url | 50 | 100.0 | 100.0 |
| direct:bank_routing_number | 46 | 100.0 | 100.0 |
| indirect:country | 35 | 100.0 | 100.0 |
| direct:phone_number | 31 | 100.0 | 100.0 |
| direct:date_of_birth | 30 | 100.0 | 100.0 |
| indirect:occupation | 29 | 69.0 | 69.0 |
| indirect:time | 28 | 92.9 | 92.9 |
| indirect:state | 28 | 100.0 | 89.3 |
| direct:ssn | 27 | 100.0 | 100.0 |
| direct:cvv | 27 | 100.0 | 100.0 |
| direct:biometric_identifier | 25 | 100.0 | 100.0 |
| indirect:city | 23 | 100.0 | 100.0 |
| indirect:date_time | 23 | 95.7 | 95.7 |
| indirect:county | 22 | 100.0 | 86.4 |
| direct:user_name | 22 | 100.0 | 100.0 |
| indirect:postcode | 19 | 100.0 | 100.0 |
| direct:pin | 16 | 100.0 | 100.0 |
| indirect:employment_status | 15 | 93.3 | 93.3 |
| direct:medical_record_number | 15 | 100.0 | 100.0 |
| indirect:blood_type | 14 | 85.7 | 85.7 |
| direct:swift_bic | 13 | 100.0 | 100.0 |
| direct:password | 12 | 100.0 | 91.7 |
| indirect:race_ethnicity | 11 | 100.0 | 100.0 |
| direct:ipv4 | 10 | 100.0 | 100.0 |
| direct:http_cookie | 9 | 100.0 | 88.9 |
| direct:health_plan_beneficiary_number | 8 | 100.0 | 100.0 |
| direct:employee_id | 8 | 100.0 | 100.0 |
| direct:fax_number | 8 | 100.0 | 100.0 |
| indirect:language | 8 | 100.0 | 100.0 |
| direct:tax_id | 8 | 100.0 | 100.0 |
| indirect:religious_belief | 6 | 100.0 | 100.0 |
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
| Risk Assessment | 33 | 93.9 | 93.9 |
| Affidavit of No Unpaid Assessments | 32 | 96.9 | 96.9 |
| Investment Strategy | 29 | 100.0 | 100.0 |
| Credit Policy Document | 27 | 100.0 | 100.0 |
| Trade Authorization | 26 | 84.6 | 84.6 |
| Medical Records Release Form | 25 | 100.0 | 100.0 |
| Investment Policy Statement | 24 | 100.0 | 100.0 |
| Investment Objectives | 22 | 100.0 | 100.0 |
| Market Analysis Report | 22 | 100.0 | 100.0 |
| Insurance Endorsement | 22 | 100.0 | 95.5 |
| Investment Forecast | 22 | 100.0 | 100.0 |
| Investment Review | 22 | 100.0 | 95.5 |
| System Diagnostic Log | 22 | 100.0 | 100.0 |
| blood bank inventory record | 21 | 81.0 | 81.0 |
| Account Closing Form | 21 | 100.0 | 100.0 |
| Quitclaim Deed | 20 | 100.0 | 90.0 |
| Incident Report | 20 | 100.0 | 100.0 |
| Investment Proposal | 20 | 100.0 | 100.0 |
| Insurance Compliance Report | 19 | 100.0 | 100.0 |
| Driver License | 19 | 100.0 | 100.0 |
| Debt Settlement Plan | 19 | 100.0 | 100.0 |
| Affidavit of No Unpaid Liabilities | 19 | 100.0 | 89.5 |
| Reinsurance Agreement | 19 | 100.0 | 100.0 |
| Affidavit of Title | 18 | 100.0 | 100.0 |
| clinical trial participant biometric file | 17 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 21839 | 74.7 |
| tier:indirect | 15631 | 42.5 |
| CONTACT | 6876 | 88.5 |
| DEMOGRAPHIC | 6831 | 12.6 |
| ORG | 5173 | 55.4 |
| FIN_ID | 4463 | 90.8 |
| SECRET | 4204 | 25.7 |
| DATE | 3627 | 80.5 |
| ADDRESS | 2683 | 81.1 |
| NAME | 2569 | 75.7 |
| GOV_ID | 694 | 88.3 |
| NETWORK | 350 | 100.0 |
