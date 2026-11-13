# redactd benchmark report

Generated 2026-11-13 07:01 UTC · mode **thorough** · shipped `redactd.pipeline.Pipeline` · 4 worker processes × 1 thread · total wall time 9.6 min

Recall = share of gold identifiers with ≥50% / ≥90% of their characters redacted. Precision = share of redacted characters that fall inside a gold span (Gretel leaves real PII unlabelled, so its precision understates reality). *Raw* uses dataset labels as-is; *policy* removes gold spans that are template placeholders and, for organisation labels only, generic phrases and public bodies (`bench/gold_policy.py`).

**Held-out** sets are never used to tune rules, thresholds or prompts. **Dev** sets are.

## Summary

| Set | Role | Docs | Direct ≥50 raw | Direct ≥90 raw | Indirect ≥50 raw | Indirect ≥90 raw | Prec raw | Direct ≥50 pol | Direct ≥90 pol | Indirect ≥50 pol | Indirect ≥90 pol | Prec pol |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| eval_gretel_fin_holdout | held-out | 300 | 98.9 | 95.6 | 92.2 | 87.8 | 33.4 | 99.7 | 97.2 | 95.4 | 92.0 | 32.5 |
| eval_fin_holdout2 | held-out | 300 | 98.6 | 96.3 | 89.7 | 88.6 | 35.0 | 99.2 | 97.4 | 92.8 | 91.7 | 34.6 |
| eval_nemotron_fin_structured | held-out | 300 | 99.6 | 99.2 | 92.6 | 92.2 | 76.1 | 99.6 | 99.2 | 96.2 | 95.9 | 76.0 |
| eval_gretel_en | held-out | 300 | 100.0 | 99.2 | 100.0 | 99.0 | 76.7 | 100.0 | 99.2 | 100.0 | 99.0 | 76.7 |
| eval_adversarial | held-out | 160 | 99.0 | 98.0 | 98.1 | 98.1 | 75.9 | 99.5 | 98.5 | 98.1 | 98.1 | 75.9 |
| eval_gretel_fin | dev | 200 | 98.6 | 96.7 | 95.9 | 93.7 | 36.0 | 99.0 | 97.5 | 99.4 | 97.6 | 34.5 |
| eval_nemotron_fin | dev | 300 | 99.9 | 99.8 | 97.6 | 97.3 | 74.3 | 99.9 | 99.8 | 98.6 | 98.3 | 74.2 |
| dev_nemotron_fin_structured | dev | 200 | 99.7 | 99.2 | 92.1 | 91.1 | 73.7 | 99.7 | 99.2 | 96.8 | 96.3 | 73.6 |

## Leak regression (A3)

`leak_check` must be empty for every rendered document. *Gold direct values in output* is a raw string search of the redacted output for every gold DIRECT value; it counts every miss and also short values that survive as substrings of unrelated words.

| Set | leak_check failures | Gold direct values still in output | of | Docs affected |
|---|---:|---:|---:|---:|
| eval_gretel_fin_holdout | 131 | 7 | 773 | 7 / 300 |
| eval_fin_holdout2 | 117 | 8 | 720 | 7 / 300 |
| eval_nemotron_fin_structured | 39 | 6 | 1287 | 6 / 300 |
| eval_gretel_en | 6 | 0 | 1214 | 0 / 300 |
| eval_adversarial | 4 | 5 | 592 | 4 / 160 |
| eval_gretel_fin | 92 | 4 | 513 | 4 / 200 |
| eval_nemotron_fin | 23 | 1 | 1270 | 1 / 300 |
| dev_nemotron_fin_structured | 25 | 0 | 824 | 0 / 200 |

## Latency (per document, measured inside the worker; all workers busy)

| Set | mean chars | p50 ms | p95 ms | p99 ms | ms / 1k chars | stage share |
|---|---:|---:|---:|---:|---:|---|
| eval_gretel_fin_holdout | 1399 | 1418 | 2993 | 5037 | 1137 | rules 0%, openmed 15%, gliner 85%, finalize 0% |
| eval_fin_holdout2 | 1427 | 1613 | 3385 | 5048 | 1148 | rules 0%, openmed 14%, gliner 86%, finalize 0% |
| eval_nemotron_fin_structured | 1087 | 911 | 3617 | 4354 | 1189 | rules 0%, openmed 17%, gliner 83%, finalize 0% |
| eval_gretel_en | 214 | 257 | 522 | 804 | 1373 | rules 0%, openmed 12%, gliner 88%, finalize 0% |
| eval_adversarial | 147 | 198 | 397 | 470 | 1536 | rules 0%, openmed 11%, gliner 89%, finalize 0% |
| eval_gretel_fin | 1481 | 1716 | 3353 | 5191 | 1123 | rules 0%, openmed 15%, gliner 85%, finalize 0% |
| eval_nemotron_fin | 615 | 436 | 945 | 2049 | 834 | rules 0%, openmed 12%, gliner 88%, finalize 0% |
| dev_nemotron_fin_structured | 1031 | 840 | 3304 | 6264 | 1170 | rules 0%, openmed 16%, gliner 84%, finalize 0% |

## eval_gretel_fin_holdout (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 439 | 100.0 | 97.7 |
| ORG | 437 | 92.7 | 87.2 |
| ADDRESS | 244 | 98.0 | 91.4 |
| DATE | 130 | 90.8 | 90.0 |
| CONTACT | 125 | 96.0 | 93.6 |
| FIN_ID | 94 | 100.0 | 100.0 |
| NETWORK | 19 | 100.0 | 100.0 |
| GOV_ID | 15 | 100.0 | 100.0 |
| SECRET | 10 | 100.0 | 90.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 437 | 92.7 | 87.2 |
| direct:name | 406 | 100.0 | 97.5 |
| direct:street_address | 240 | 97.9 | 91.7 |
| indirect:date | 85 | 98.8 | 98.8 |
| direct:phone_number | 81 | 95.1 | 93.8 |
| direct:email | 44 | 97.7 | 93.2 |
| indirect:time | 25 | 60.0 | 60.0 |
| direct:swift_bic_code | 18 | 100.0 | 100.0 |
| direct:last_name | 16 | 100.0 | 100.0 |
| direct:date_of_birth | 16 | 93.8 | 87.5 |
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
| direct:local_latlng | 4 | 100.0 | 75.0 |
| direct:api_key | 4 | 100.0 | 100.0 |
| indirect:date_time | 4 | 100.0 | 100.0 |
| direct:user_name | 3 | 100.0 | 100.0 |
| direct:driver_license_number | 2 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Bill of Lading | 98 | 98.0 | 96.9 |
| CSV | 89 | 100.0 | 100.0 |
| IT support ticket | 74 | 97.3 | 95.9 |
| Loan Application | 73 | 98.6 | 94.5 |
| Health Insurance Claim Form | 65 | 96.9 | 93.8 |
| Business Plan | 61 | 90.2 | 90.2 |
| ISDA Definition | 61 | 96.7 | 88.5 |
| Insurance Claim Form | 48 | 93.8 | 93.8 |
| Policyholder's Report | 43 | 93.0 | 86.0 |
| Payment Confirmation | 42 | 100.0 | 100.0 |
| FpML | 38 | 100.0 | 100.0 |
| Financial Aid Application | 38 | 89.5 | 78.9 |
| SWIFT Message | 38 | 97.4 | 84.2 |
| Trade Confirmation | 37 | 100.0 | 91.9 |
| Safety Data Sheet | 36 | 77.8 | 75.0 |
| Customer support conversational log | 36 | 100.0 | 97.2 |
| Email | 34 | 100.0 | 97.1 |
| Regulatory Filing | 33 | 97.0 | 87.9 |
| Financial Statement | 33 | 100.0 | 100.0 |
| EDI | 31 | 100.0 | 93.5 |
| Insurance Policy | 30 | 100.0 | 93.3 |
| Tax Return | 24 | 95.8 | 87.5 |
| Financial Risk Assessment | 22 | 100.0 | 100.0 |
| Compliance Certificate | 22 | 100.0 | 95.5 |
| Corporate Governance Guidelines | 21 | 90.5 | 90.5 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 39754 | 41.0 |
| tier:indirect | 37259 | 23.5 |
| DEMOGRAPHIC | 18267 | 2.6 |
| ADDRESS | 13917 | 48.6 |
| ORG | 11052 | 61.1 |
| NAME | 8026 | 65.2 |
| DATE | 7940 | 18.9 |
| SECRET | 7118 | 4.6 |
| CONTACT | 6401 | 31.5 |
| FIN_ID | 3093 | 40.1 |
| NETWORK | 978 | 59.0 |
| GOV_ID | 221 | 58.8 |

## eval_fin_holdout2 (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| ORG | 413 | 87.7 | 86.7 |
| NAME | 396 | 98.5 | 97.2 |
| ADDRESS | 271 | 98.2 | 93.7 |
| DATE | 156 | 95.5 | 94.2 |
| FIN_ID | 96 | 99.0 | 99.0 |
| CONTACT | 81 | 100.0 | 97.5 |
| GOV_ID | 21 | 100.0 | 95.2 |
| NETWORK | 15 | 100.0 | 100.0 |
| SECRET | 7 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 413 | 87.7 | 86.7 |
| direct:name | 376 | 98.4 | 97.1 |
| direct:street_address | 267 | 98.1 | 93.6 |
| indirect:date | 110 | 99.1 | 99.1 |
| direct:phone_number | 49 | 100.0 | 98.0 |
| direct:email | 32 | 100.0 | 96.9 |
| indirect:time | 24 | 79.2 | 70.8 |
| direct:employee_id | 21 | 100.0 | 100.0 |
| direct:bban | 16 | 100.0 | 100.0 |
| direct:date_of_birth | 15 | 93.3 | 93.3 |
| direct:swift_bic_code | 15 | 100.0 | 100.0 |
| direct:credit_card_number | 10 | 100.0 | 100.0 |
| direct:bank_routing_number | 10 | 100.0 | 100.0 |
| direct:last_name | 10 | 100.0 | 100.0 |
| direct:customer_id | 8 | 100.0 | 100.0 |
| direct:ipv6 | 8 | 100.0 | 100.0 |
| direct:passport_number | 7 | 100.0 | 85.7 |
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
| Bill of Lading | 86 | 95.3 | 93.0 |
| CSV | 66 | 100.0 | 100.0 |
| Payment Confirmation | 64 | 93.8 | 92.2 |
| IT support ticket | 54 | 98.1 | 98.1 |
| Customer support conversational log | 49 | 100.0 | 100.0 |
| Health Insurance Claim Form | 45 | 97.8 | 97.8 |
| Loan Application | 44 | 100.0 | 97.7 |
| Credit Card Statement | 36 | 94.4 | 94.4 |
| Shareholder Agreement | 35 | 71.4 | 71.4 |
| Investment Prospectus | 34 | 94.1 | 94.1 |
| Audit Report | 32 | 100.0 | 100.0 |
| BAI Format | 32 | 100.0 | 100.0 |
| FIX Protocol | 31 | 93.5 | 87.1 |
| SWIFT Message | 31 | 100.0 | 83.9 |
| Safety Data Sheet | 30 | 73.3 | 73.3 |
| Tax Return | 30 | 100.0 | 100.0 |
| Real Estate Loan Agreement | 29 | 96.6 | 96.6 |
| Policyholder's Report | 29 | 96.6 | 89.7 |
| Transaction Confirmation | 28 | 100.0 | 96.4 |
| Compliance Certificate | 27 | 100.0 | 96.3 |
| ISDA Definition | 26 | 88.5 | 80.8 |
| Insurance Claim Form | 25 | 100.0 | 100.0 |
| MT940 | 25 | 96.0 | 96.0 |
| Annual Report | 24 | 95.8 | 91.7 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 40230 | 40.2 |
| tier:indirect | 33847 | 27.8 |
| ADDRESS | 14746 | 53.1 |
| DEMOGRAPHIC | 13888 | 2.0 |
| ORG | 12576 | 57.6 |
| NAME | 8153 | 62.2 |
| DATE | 7383 | 25.8 |
| CONTACT | 6786 | 20.0 |
| SECRET | 6466 | 4.2 |
| FIN_ID | 3092 | 33.5 |
| NETWORK | 695 | 58.4 |
| GOV_ID | 292 | 71.6 |

## eval_nemotron_fin_structured (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 586 | 99.1 | 99.1 |
| NAME | 498 | 100.0 | 100.0 |
| DATE | 414 | 94.7 | 94.4 |
| CONTACT | 348 | 99.7 | 99.7 |
| ADDRESS | 322 | 94.4 | 93.2 |
| ORG | 225 | 100.0 | 99.6 |
| DEMOGRAPHIC | 176 | 80.1 | 79.0 |
| GOV_ID | 130 | 100.0 | 100.0 |
| SECRET | 47 | 100.0 | 93.6 |
| NETWORK | 28 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:date | 312 | 93.6 | 93.3 |
| direct:first_name | 248 | 100.0 | 100.0 |
| indirect:company_name | 225 | 100.0 | 99.6 |
| direct:last_name | 218 | 100.0 | 100.0 |
| direct:account_number | 189 | 99.5 | 99.5 |
| direct:email | 174 | 99.4 | 99.4 |
| direct:customer_id | 110 | 100.0 | 100.0 |
| direct:credit_debit_card | 102 | 100.0 | 100.0 |
| direct:street_address | 95 | 98.9 | 94.7 |
| indirect:occupation | 94 | 68.1 | 66.0 |
| direct:url | 83 | 100.0 | 100.0 |
| direct:bank_routing_number | 75 | 100.0 | 100.0 |
| direct:phone_number | 71 | 100.0 | 100.0 |
| indirect:state | 61 | 93.4 | 93.4 |
| indirect:country | 52 | 98.1 | 98.1 |
| indirect:city | 50 | 100.0 | 100.0 |
| direct:ssn | 44 | 100.0 | 100.0 |
| direct:swift_bic | 41 | 100.0 | 100.0 |
| indirect:time | 40 | 97.5 | 97.5 |
| direct:date_of_birth | 36 | 100.0 | 100.0 |
| indirect:county | 35 | 65.7 | 65.7 |
| direct:cvv | 33 | 87.9 | 87.9 |
| direct:user_name | 32 | 100.0 | 100.0 |
| direct:biometric_identifier | 31 | 100.0 | 100.0 |
| direct:password | 29 | 100.0 | 96.6 |
| indirect:postcode | 29 | 100.0 | 100.0 |
| indirect:date_time | 26 | 96.2 | 96.2 |
| indirect:employment_status | 21 | 90.5 | 90.5 |
| direct:fax_number | 20 | 100.0 | 100.0 |
| direct:pin | 20 | 100.0 | 100.0 |
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
| indirect:sexuality | 2 | 50.0 | 50.0 |
| direct:license_plate | 1 | 100.0 | 100.0 |
| direct:vehicle_identifier | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Investment Agreement | 58 | 98.3 | 98.3 |
| Mortgage Loan | 54 | 92.6 | 92.6 |
| Premium Payment Schedule | 48 | 100.0 | 100.0 |
| Emergency Planning | 44 | 100.0 | 100.0 |
| Corporate Solutions | 41 | 97.6 | 97.6 |
| Affidavit of No Contingencies | 40 | 92.5 | 92.5 |
| Privacy Policy Document | 39 | 100.0 | 100.0 |
| Investment Statement | 38 | 97.4 | 97.4 |
| Bank Services | 35 | 100.0 | 97.1 |
| Audit Report | 34 | 100.0 | 100.0 |
| Affidavit of No Unpaid Insurance Premiums | 34 | 73.5 | 73.5 |
| Debt Consolidation Agreement | 33 | 100.0 | 100.0 |
| Investment Proposal | 33 | 100.0 | 100.0 |
| Investment Strategy | 32 | 100.0 | 100.0 |
| Affidavit of Title | 31 | 96.8 | 96.8 |
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
| tier:direct | 30963 | 88.8 |
| tier:indirect | 18627 | 54.8 |
| CONTACT | 11782 | 99.0 |
| DEMOGRAPHIC | 7293 | 24.8 |
| ORG | 6555 | 64.5 |
| FIN_ID | 6533 | 95.4 |
| DATE | 4779 | 87.2 |
| NAME | 4192 | 81.0 |
| ADDRESS | 3989 | 82.1 |
| SECRET | 2942 | 48.4 |
| GOV_ID | 1016 | 97.8 |
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
| ADDRESS | 107 | 100.0 | 91.6 |
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
| direct:street_address | 90 | 100.0 | 90.0 |
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
| Service Level Description | 13 | 100.0 | 100.0 |
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
| tier:direct | 16607 | 88.3 |
| tier:indirect | 5791 | 43.6 |
| ADDRESS | 3299 | 93.1 |
| DATE | 3221 | 73.5 |
| NAME | 3085 | 82.0 |
| FIN_ID | 2818 | 93.5 |
| GOV_ID | 2617 | 99.8 |
| CONTACT | 2596 | 95.2 |
| DEMOGRAPHIC | 2117 | 0.0 |
| SECRET | 1194 | 33.5 |
| NETWORK | 998 | 94.5 |
| ORG | 453 | 34.4 |

## eval_adversarial (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 224 | 97.8 | 96.4 |
| FIN_ID | 220 | 100.0 | 99.1 |
| ADDRESS | 112 | 97.3 | 96.4 |
| CONTACT | 80 | 100.0 | 100.0 |
| DATE | 28 | 100.0 | 100.0 |
| GOV_ID | 24 | 100.0 | 100.0 |
| ORG | 16 | 100.0 | 100.0 |
| SECRET | 4 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:name | 132 | 98.5 | 96.2 |
| direct:account_number | 76 | 100.0 | 97.4 |
| direct:iban | 60 | 100.0 | 100.0 |
| direct:first_name | 52 | 100.0 | 100.0 |
| direct:phone_number | 44 | 100.0 | 100.0 |
| direct:street_address | 40 | 97.5 | 95.0 |
| indirect:city | 40 | 95.0 | 95.0 |
| direct:last_name | 36 | 91.7 | 91.7 |
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
| international formats | 124 | 100.0 | 99.2 |
| structured keys | 92 | 98.9 | 98.9 |
| email threads | 76 | 100.0 | 98.7 |
| SWIFT / FIX | 64 | 90.6 | 84.4 |
| common-word names | 56 | 100.0 | 100.0 |
| masked partials | 56 | 100.0 | 100.0 |
| coreference | 48 | 97.9 | 97.9 |
| odd spacing / line breaks | 44 | 100.0 | 100.0 |
| glued text | 40 | 100.0 | 100.0 |
| prompt injection | 40 | 100.0 | 100.0 |
| keyword ids | 24 | 100.0 | 100.0 |
| public bodies / dates | 24 | 100.0 | 100.0 |
| chat log | 20 | 100.0 | 100.0 |

### Recall by template exposure

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| templates also rendered (other values) for training | 356 | 99.4 | 98.9 |
| templates never used in training | 352 | 98.3 | 97.2 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 10278 | 80.8 |
| FIN_ID | 3530 | 79.5 |
| NAME | 2306 | 89.9 |
| tier:indirect | 2035 | 51.5 |
| CONTACT | 1954 | 96.1 |
| ADDRESS | 1462 | 82.0 |
| ORG | 814 | 78.3 |
| SECRET | 733 | 14.6 |
| DEMOGRAPHIC | 620 | 2.6 |
| DATE | 601 | 65.9 |
| GOV_ID | 240 | 100.0 |
| NETWORK | 53 | 0.0 |

## eval_gretel_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 304 | 99.3 | 98.0 |
| ORG | 284 | 95.1 | 93.0 |
| ADDRESS | 200 | 99.5 | 96.0 |
| DATE | 94 | 97.9 | 95.7 |
| CONTACT | 69 | 98.6 | 95.7 |
| FIN_ID | 65 | 92.3 | 92.3 |
| GOV_ID | 19 | 100.0 | 100.0 |
| NETWORK | 11 | 100.0 | 100.0 |
| SECRET | 11 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 284 | 95.1 | 93.0 |
| direct:name | 271 | 99.3 | 97.8 |
| direct:street_address | 191 | 99.5 | 95.8 |
| indirect:date | 68 | 100.0 | 100.0 |
| direct:email | 36 | 100.0 | 100.0 |
| direct:phone_number | 33 | 97.0 | 90.9 |
| direct:first_name | 31 | 100.0 | 100.0 |
| indirect:time | 13 | 92.3 | 76.9 |
| direct:account_pin | 12 | 58.3 | 58.3 |
| direct:date_of_birth | 11 | 90.9 | 90.9 |
| direct:credit_card_security_code | 10 | 100.0 | 100.0 |
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
| Loan Application | 101 | 100.0 | 98.0 |
| BAI Format | 50 | 100.0 | 96.0 |
| SWIFT Message | 47 | 100.0 | 97.9 |
| Policyholder's Report | 43 | 100.0 | 90.7 |
| IT support ticket | 39 | 97.4 | 97.4 |
| Customer support conversational log | 37 | 100.0 | 100.0 |
| Customer Agreement | 35 | 100.0 | 100.0 |
| Payment Confirmation | 31 | 100.0 | 93.5 |
| Audit Report | 31 | 100.0 | 100.0 |
| EDI | 31 | 100.0 | 100.0 |
| Supply Chain Management Agreement | 29 | 100.0 | 100.0 |
| FIX Protocol | 29 | 100.0 | 96.6 |
| Bill of Lading | 29 | 100.0 | 96.6 |
| Financial Risk Assessment | 25 | 100.0 | 96.0 |
| Regulatory Compliance Guide | 25 | 84.0 | 80.0 |
| Insurance Policy | 24 | 100.0 | 100.0 |
| Trade Confirmation | 23 | 100.0 | 95.7 |
| CSV | 21 | 100.0 | 100.0 |
| Financial Disclosure Statement | 21 | 100.0 | 100.0 |
| Compliance Certificate | 21 | 100.0 | 95.2 |
| MT940 | 17 | 70.6 | 70.6 |
| Employment Contract | 17 | 100.0 | 100.0 |
| Credit Card Statement | 16 | 100.0 | 100.0 |
| Email | 16 | 87.5 | 87.5 |
| Health Insurance Claim Form | 16 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 26515 | 42.7 |
| tier:indirect | 23910 | 25.4 |
| DEMOGRAPHIC | 11314 | 1.7 |
| ADDRESS | 9375 | 58.1 |
| ORG | 8005 | 58.5 |
| SECRET | 5596 | 4.3 |
| NAME | 5309 | 64.6 |
| DATE | 4591 | 26.3 |
| CONTACT | 3354 | 33.9 |
| FIN_ID | 2213 | 29.1 |
| NETWORK | 407 | 59.5 |
| GOV_ID | 261 | 73.6 |

## eval_nemotron_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 480 | 100.0 | 100.0 |
| NAME | 370 | 100.0 | 100.0 |
| ADDRESS | 265 | 99.6 | 99.2 |
| CONTACT | 262 | 99.6 | 99.6 |
| DATE | 221 | 99.1 | 99.1 |
| DEMOGRAPHIC | 158 | 91.8 | 90.5 |
| ORG | 127 | 100.0 | 100.0 |
| GOV_ID | 103 | 100.0 | 100.0 |
| NETWORK | 49 | 100.0 | 100.0 |
| SECRET | 34 | 100.0 | 97.1 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:first_name | 194 | 100.0 | 100.0 |
| direct:account_number | 167 | 100.0 | 100.0 |
| direct:last_name | 144 | 100.0 | 100.0 |
| indirect:date | 137 | 98.5 | 98.5 |
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
| indirect:employment_status | 31 | 83.9 | 80.6 |
| direct:swift_bic | 29 | 100.0 | 100.0 |
| indirect:postcode | 28 | 100.0 | 100.0 |
| direct:ipv4 | 26 | 100.0 | 100.0 |
| direct:biometric_identifier | 26 | 100.0 | 100.0 |
| direct:ssn | 25 | 100.0 | 100.0 |
| direct:cvv | 23 | 100.0 | 100.0 |
| indirect:race_ethnicity | 20 | 100.0 | 100.0 |
| direct:health_plan_beneficiary_number | 19 | 100.0 | 100.0 |
| indirect:date_time | 18 | 100.0 | 100.0 |
| direct:http_cookie | 17 | 100.0 | 94.1 |
| direct:pin | 17 | 100.0 | 100.0 |
| indirect:blood_type | 17 | 64.7 | 64.7 |
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
| Mortgage | 401 | 99.0 | 98.8 |
| Investment | 342 | 99.1 | 99.1 |
| Banking | 337 | 100.0 | 100.0 |
| User Account and Transaction Services | 282 | 100.0 | 99.6 |
| Brokerage | 279 | 100.0 | 99.6 |
| Insurance | 214 | 96.7 | 96.3 |
| Credit | 214 | 98.6 | 98.6 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 26609 | 86.2 |
| tier:indirect | 13119 | 50.0 |
| CONTACT | 9179 | 97.9 |
| DEMOGRAPHIC | 7166 | 23.5 |
| FIN_ID | 5347 | 95.5 |
| NAME | 3575 | 71.0 |
| ADDRESS | 3284 | 83.8 |
| SECRET | 3283 | 51.2 |
| ORG | 3232 | 77.5 |
| DATE | 2721 | 87.1 |
| GOV_ID | 1005 | 95.3 |
| NETWORK | 936 | 96.3 |

## dev_nemotron_fin_structured (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 378 | 100.0 | 99.5 |
| NAME | 310 | 100.0 | 100.0 |
| DATE | 274 | 94.2 | 93.4 |
| ADDRESS | 189 | 93.7 | 92.1 |
| CONTACT | 171 | 100.0 | 100.0 |
| ORG | 135 | 99.3 | 99.3 |
| GOV_ID | 98 | 100.0 | 100.0 |
| DEMOGRAPHIC | 98 | 80.6 | 78.6 |
| SECRET | 25 | 88.0 | 76.0 |
| NETWORK | 19 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:date | 193 | 93.3 | 92.2 |
| direct:first_name | 164 | 100.0 | 100.0 |
| indirect:company_name | 135 | 99.3 | 99.3 |
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
| indirect:occupation | 29 | 48.3 | 48.3 |
| indirect:time | 28 | 92.9 | 92.9 |
| indirect:state | 28 | 89.3 | 89.3 |
| direct:ssn | 27 | 100.0 | 100.0 |
| direct:cvv | 27 | 100.0 | 100.0 |
| direct:biometric_identifier | 25 | 100.0 | 100.0 |
| indirect:city | 23 | 100.0 | 100.0 |
| indirect:date_time | 23 | 95.7 | 95.7 |
| indirect:county | 22 | 59.1 | 50.0 |
| direct:user_name | 22 | 100.0 | 100.0 |
| indirect:postcode | 19 | 100.0 | 100.0 |
| direct:pin | 16 | 100.0 | 100.0 |
| indirect:employment_status | 15 | 86.7 | 86.7 |
| direct:medical_record_number | 15 | 100.0 | 100.0 |
| indirect:blood_type | 14 | 85.7 | 78.6 |
| direct:swift_bic | 13 | 100.0 | 100.0 |
| direct:password | 12 | 83.3 | 75.0 |
| indirect:race_ethnicity | 11 | 100.0 | 90.9 |
| direct:ipv4 | 10 | 100.0 | 100.0 |
| direct:http_cookie | 9 | 88.9 | 66.7 |
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
| Market Analysis Report | 22 | 86.4 | 86.4 |
| Insurance Endorsement | 22 | 100.0 | 95.5 |
| Investment Forecast | 22 | 100.0 | 100.0 |
| Investment Review | 22 | 100.0 | 95.5 |
| System Diagnostic Log | 22 | 100.0 | 100.0 |
| blood bank inventory record | 21 | 81.0 | 76.2 |
| Account Closing Form | 21 | 100.0 | 100.0 |
| Quitclaim Deed | 20 | 90.0 | 85.0 |
| Incident Report | 20 | 100.0 | 100.0 |
| Investment Proposal | 20 | 100.0 | 100.0 |
| Insurance Compliance Report | 19 | 100.0 | 100.0 |
| Driver License | 19 | 100.0 | 100.0 |
| Debt Settlement Plan | 19 | 100.0 | 100.0 |
| Affidavit of No Unpaid Liabilities | 19 | 94.7 | 89.5 |
| Reinsurance Agreement | 19 | 100.0 | 100.0 |
| Affidavit of Title | 18 | 100.0 | 100.0 |
| clinical trial participant biometric file | 17 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 18673 | 86.4 |
| tier:indirect | 12201 | 53.9 |
| CONTACT | 6216 | 97.2 |
| ORG | 4704 | 61.2 |
| DEMOGRAPHIC | 4428 | 20.0 |
| FIN_ID | 4274 | 96.1 |
| DATE | 3069 | 91.7 |
| NAME | 2561 | 78.8 |
| ADDRESS | 2439 | 81.9 |
| SECRET | 2146 | 43.3 |
| GOV_ID | 672 | 99.9 |
| NETWORK | 365 | 100.0 |
