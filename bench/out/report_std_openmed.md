# redactd benchmark report

Generated 2026-11-13 17:07 UTC · mode **standard** · shipped `redactd.pipeline.Pipeline` · 4 worker processes × 1 thread · total wall time 1.4 min

Recall = share of gold identifiers with ≥50% / ≥90% of their characters redacted. Precision = share of redacted characters that fall inside a gold span (Gretel leaves real PII unlabelled, so its precision understates reality). *Raw* uses dataset labels as-is; *policy* removes gold spans that are template placeholders and, for organisation labels only, generic phrases and public bodies (`bench/gold_policy.py`).

**Held-out** sets are never used to tune rules, thresholds or prompts. **Dev** sets are. The **regression** set (hand-built hard cases) was written by us and rules were fixed against it, so it shows that known hard cases pass, not how unseen text behaves.

## Summary

| Set | Role | Docs | Direct ≥50 raw | Direct ≥90 raw | Indirect ≥50 raw | Indirect ≥90 raw | Prec raw | Direct ≥50 pol | Direct ≥90 pol | Indirect ≥50 pol | Indirect ≥90 pol | Prec pol |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| eval_gretel_fin_holdout | held-out | 300 | 85.9 | 74.1 | 72.6 | 66.8 | 53.5 | 87.4 | 75.6 | 79.9 | 73.8 | 53.3 |
| eval_fin_holdout2 | held-out | 300 | 89.6 | 75.7 | 75.6 | 72.2 | 56.0 | 90.2 | 76.5 | 78.9 | 75.3 | 55.5 |
| eval_nemotron_fin_structured | held-out | 300 | 98.7 | 96.9 | 84.8 | 84.3 | 93.5 | 98.7 | 96.9 | 88.1 | 87.6 | 93.5 |
| eval_gretel_en | held-out | 300 | 98.2 | 93.6 | 100.0 | 95.2 | 90.5 | 98.2 | 93.6 | 100.0 | 95.2 | 90.5 |
| eval_adversarial | regression | 160 | 97.2 | 93.5 | 100.0 | 97.2 | 91.6 | 97.2 | 93.5 | 100.0 | 97.2 | 91.4 |
| eval_gretel_fin | dev | 200 | 89.3 | 78.7 | 80.9 | 76.6 | 63.5 | 89.8 | 79.2 | 87.8 | 83.3 | 62.4 |
| eval_nemotron_fin | dev | 300 | 99.6 | 98.3 | 91.6 | 90.3 | 97.2 | 99.6 | 98.3 | 92.6 | 91.2 | 97.2 |
| dev_nemotron_fin_structured | dev | 200 | 97.8 | 96.5 | 86.3 | 85.6 | 91.3 | 97.8 | 96.5 | 91.1 | 90.5 | 91.3 |

## Leak regression (A3)

`leak_check` must be empty for every rendered document. *Gold direct values in output* is a raw string search of the redacted output for every gold DIRECT value; it counts every miss and also short values that survive as substrings of unrelated words.

| Set | leak_check failures | Gold direct values still in output | of | Docs affected |
|---|---:|---:|---:|---:|
| eval_gretel_fin_holdout | 1 | 83 | 773 | 45 / 300 |
| eval_fin_holdout2 | 1 | 49 | 720 | 35 / 300 |
| eval_nemotron_fin_structured | 0 | 11 | 1287 | 11 / 300 |
| eval_gretel_en | 0 | 13 | 1130 | 12 / 300 |
| eval_adversarial | 0 | 10 | 592 | 8 / 160 |
| eval_gretel_fin | 1 | 29 | 513 | 25 / 200 |
| eval_nemotron_fin | 0 | 4 | 1270 | 4 / 300 |
| dev_nemotron_fin_structured | 0 | 9 | 824 | 9 / 200 |

## Latency (per document, measured inside the worker; all workers busy)

| Set | mean chars | p50 ms | p95 ms | p99 ms | ms / 1k chars | stage share |
|---|---:|---:|---:|---:|---:|---|
| eval_gretel_fin_holdout | 1399 | 189 | 791 | 1006 | 160 | rules 1%, openmed 99%, finalize 0% |
| eval_fin_holdout2 | 1427 | 199 | 777 | 927 | 156 | rules 1%, openmed 99%, finalize 0% |
| eval_nemotron_fin_structured | 1087 | 123 | 804 | 899 | 184 | rules 1%, openmed 99%, finalize 0% |
| eval_gretel_en | 221 | 26 | 81 | 123 | 144 | rules 1%, openmed 98%, finalize 1% |
| eval_adversarial | 147 | 17 | 43 | 54 | 144 | rules 1%, openmed 98%, finalize 1% |
| eval_gretel_fin | 1481 | 200 | 769 | 895 | 151 | rules 1%, openmed 99%, finalize 0% |
| eval_nemotron_fin | 615 | 43 | 113 | 179 | 87 | rules 1%, openmed 98%, finalize 1% |
| dev_nemotron_fin_structured | 1031 | 101 | 734 | 832 | 163 | rules 1%, openmed 99%, finalize 0% |

## eval_gretel_fin_holdout (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 439 | 77.2 | 62.6 |
| ORG | 437 | 68.6 | 61.3 |
| ADDRESS | 244 | 94.3 | 81.1 |
| DATE | 130 | 87.7 | 87.7 |
| CONTACT | 125 | 92.8 | 92.0 |
| FIN_ID | 94 | 88.3 | 76.6 |
| NETWORK | 19 | 100.0 | 100.0 |
| GOV_ID | 15 | 100.0 | 93.3 |
| SECRET | 10 | 100.0 | 60.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 437 | 68.6 | 61.3 |
| direct:name | 406 | 76.8 | 61.3 |
| direct:street_address | 240 | 94.6 | 81.2 |
| indirect:date | 85 | 97.6 | 97.6 |
| direct:phone_number | 81 | 93.8 | 92.6 |
| direct:email | 44 | 90.9 | 90.9 |
| indirect:time | 25 | 52.0 | 52.0 |
| direct:swift_bic_code | 18 | 100.0 | 100.0 |
| direct:last_name | 16 | 81.2 | 75.0 |
| direct:date_of_birth | 16 | 87.5 | 87.5 |
| direct:bban | 14 | 57.1 | 21.4 |
| direct:first_name | 14 | 92.9 | 92.9 |
| direct:iban | 14 | 100.0 | 100.0 |
| direct:ipv6 | 12 | 100.0 | 100.0 |
| direct:bank_routing_number | 11 | 100.0 | 90.9 |
| direct:credit_card_number | 9 | 100.0 | 77.8 |
| direct:customer_id | 8 | 100.0 | 100.0 |
| direct:ssn | 8 | 100.0 | 100.0 |
| direct:employee_id | 8 | 100.0 | 75.0 |
| direct:ipv4 | 7 | 100.0 | 100.0 |
| direct:account_pin | 7 | 71.4 | 57.1 |
| direct:password | 6 | 100.0 | 50.0 |
| direct:passport_number | 5 | 100.0 | 80.0 |
| direct:credit_card_security_code | 5 | 40.0 | 40.0 |
| direct:local_latlng | 4 | 75.0 | 75.0 |
| direct:api_key | 4 | 100.0 | 75.0 |
| indirect:date_time | 4 | 100.0 | 100.0 |
| direct:user_name | 3 | 33.3 | 33.3 |
| direct:driver_license_number | 2 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Bill of Lading | 98 | 83.7 | 70.4 |
| CSV | 89 | 47.2 | 44.9 |
| IT support ticket | 74 | 77.0 | 64.9 |
| Loan Application | 73 | 93.2 | 79.5 |
| Health Insurance Claim Form | 65 | 96.9 | 87.7 |
| Business Plan | 61 | 67.2 | 65.6 |
| ISDA Definition | 61 | 63.9 | 59.0 |
| Insurance Claim Form | 48 | 89.6 | 83.3 |
| Policyholder's Report | 43 | 83.7 | 67.4 |
| Payment Confirmation | 42 | 83.3 | 73.8 |
| FpML | 38 | 100.0 | 92.1 |
| Financial Aid Application | 38 | 78.9 | 71.1 |
| SWIFT Message | 38 | 71.1 | 50.0 |
| Trade Confirmation | 37 | 86.5 | 81.1 |
| Safety Data Sheet | 36 | 66.7 | 61.1 |
| Customer support conversational log | 36 | 80.6 | 55.6 |
| Email | 34 | 97.1 | 85.3 |
| Regulatory Filing | 33 | 84.8 | 66.7 |
| Financial Statement | 33 | 90.9 | 81.8 |
| EDI | 31 | 77.4 | 61.3 |
| Insurance Policy | 30 | 96.7 | 86.7 |
| Tax Return | 24 | 95.8 | 70.8 |
| Financial Risk Assessment | 22 | 100.0 | 100.0 |
| Compliance Certificate | 22 | 95.5 | 86.4 |
| Corporate Governance Guidelines | 21 | 81.0 | 81.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 26909 | 58.3 |
| tier:indirect | 14749 | 44.1 |
| ADDRESS | 9774 | 66.2 |
| ORG | 7240 | 69.0 |
| DATE | 6636 | 22.3 |
| NAME | 5902 | 88.3 |
| CONTACT | 5847 | 33.6 |
| SECRET | 2282 | 11.7 |
| FIN_ID | 1990 | 49.5 |
| NETWORK | 875 | 67.8 |
| DEMOGRAPHIC | 873 | 2.9 |
| GOV_ID | 239 | 83.7 |

## eval_fin_holdout2 (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| ORG | 413 | 69.0 | 65.1 |
| NAME | 396 | 84.8 | 65.2 |
| ADDRESS | 271 | 93.0 | 80.8 |
| DATE | 156 | 94.9 | 92.9 |
| FIN_ID | 96 | 87.5 | 82.3 |
| CONTACT | 81 | 98.8 | 96.3 |
| GOV_ID | 21 | 95.2 | 76.2 |
| NETWORK | 15 | 100.0 | 100.0 |
| SECRET | 7 | 100.0 | 57.1 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 413 | 69.0 | 65.1 |
| direct:name | 376 | 85.6 | 64.9 |
| direct:street_address | 267 | 92.9 | 80.5 |
| indirect:date | 110 | 99.1 | 99.1 |
| direct:phone_number | 49 | 100.0 | 98.0 |
| direct:email | 32 | 96.9 | 93.8 |
| indirect:time | 24 | 75.0 | 62.5 |
| direct:employee_id | 21 | 90.5 | 85.7 |
| direct:bban | 16 | 100.0 | 81.2 |
| direct:date_of_birth | 15 | 93.3 | 93.3 |
| direct:swift_bic_code | 15 | 100.0 | 100.0 |
| direct:credit_card_number | 10 | 100.0 | 100.0 |
| direct:bank_routing_number | 10 | 80.0 | 80.0 |
| direct:last_name | 10 | 40.0 | 40.0 |
| direct:customer_id | 8 | 87.5 | 87.5 |
| direct:ipv6 | 8 | 100.0 | 100.0 |
| direct:passport_number | 7 | 100.0 | 71.4 |
| indirect:date_time | 7 | 100.0 | 100.0 |
| direct:ipv4 | 7 | 100.0 | 100.0 |
| direct:ssn | 7 | 100.0 | 85.7 |
| direct:account_pin | 7 | 57.1 | 42.9 |
| direct:driver_license_number | 7 | 85.7 | 71.4 |
| direct:first_name | 5 | 100.0 | 100.0 |
| direct:credit_card_security_code | 5 | 20.0 | 20.0 |
| direct:user_name | 5 | 100.0 | 100.0 |
| direct:password | 4 | 100.0 | 50.0 |
| direct:local_latlng | 4 | 100.0 | 100.0 |
| direct:iban | 4 | 100.0 | 100.0 |
| direct:api_key | 3 | 100.0 | 66.7 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Insurance Policy | 91 | 97.8 | 85.7 |
| Bill of Lading | 86 | 88.4 | 77.9 |
| CSV | 66 | 75.8 | 63.6 |
| Payment Confirmation | 64 | 92.2 | 85.9 |
| IT support ticket | 54 | 81.5 | 72.2 |
| Customer support conversational log | 49 | 83.7 | 77.6 |
| Health Insurance Claim Form | 45 | 97.8 | 88.9 |
| Loan Application | 44 | 97.7 | 84.1 |
| Credit Card Statement | 36 | 55.6 | 52.8 |
| Shareholder Agreement | 35 | 22.9 | 20.0 |
| Investment Prospectus | 34 | 91.2 | 85.3 |
| Audit Report | 32 | 100.0 | 96.9 |
| BAI Format | 32 | 96.9 | 87.5 |
| FIX Protocol | 31 | 83.9 | 77.4 |
| SWIFT Message | 31 | 64.5 | 41.9 |
| Safety Data Sheet | 30 | 56.7 | 56.7 |
| Tax Return | 30 | 93.3 | 86.7 |
| Real Estate Loan Agreement | 29 | 79.3 | 75.9 |
| Policyholder's Report | 29 | 86.2 | 79.3 |
| Transaction Confirmation | 28 | 96.4 | 85.7 |
| Compliance Certificate | 27 | 100.0 | 96.3 |
| ISDA Definition | 26 | 84.6 | 69.2 |
| Insurance Claim Form | 25 | 92.0 | 92.0 |
| MT940 | 25 | 76.0 | 60.0 |
| Annual Report | 24 | 95.8 | 83.3 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 26546 | 58.4 |
| tier:indirect | 14255 | 50.2 |
| ADDRESS | 10405 | 70.0 |
| ORG | 7667 | 68.6 |
| CONTACT | 6185 | 21.5 |
| DATE | 5749 | 32.9 |
| NAME | 5713 | 89.7 |
| FIN_ID | 2150 | 44.7 |
| SECRET | 1123 | 15.9 |
| DEMOGRAPHIC | 839 | 1.2 |
| NETWORK | 717 | 60.7 |
| GOV_ID | 253 | 75.9 |

## eval_nemotron_fin_structured (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 586 | 97.4 | 95.6 |
| NAME | 498 | 99.8 | 98.2 |
| DATE | 414 | 93.2 | 93.2 |
| CONTACT | 348 | 99.7 | 99.4 |
| ADDRESS | 322 | 89.1 | 86.3 |
| ORG | 225 | 99.6 | 99.1 |
| DEMOGRAPHIC | 176 | 48.3 | 47.7 |
| GOV_ID | 130 | 100.0 | 100.0 |
| SECRET | 47 | 91.5 | 78.7 |
| NETWORK | 28 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:date | 312 | 91.7 | 91.7 |
| direct:first_name | 248 | 100.0 | 99.6 |
| indirect:company_name | 225 | 99.6 | 99.1 |
| direct:last_name | 218 | 100.0 | 97.7 |
| direct:account_number | 189 | 98.9 | 98.4 |
| direct:email | 174 | 99.4 | 99.4 |
| direct:customer_id | 110 | 100.0 | 100.0 |
| direct:credit_debit_card | 102 | 97.1 | 95.1 |
| direct:street_address | 95 | 97.9 | 91.6 |
| indirect:occupation | 94 | 23.4 | 23.4 |
| direct:url | 83 | 100.0 | 100.0 |
| direct:bank_routing_number | 75 | 97.3 | 97.3 |
| direct:phone_number | 71 | 100.0 | 98.6 |
| indirect:state | 61 | 85.2 | 82.0 |
| indirect:country | 52 | 80.8 | 80.8 |
| indirect:city | 50 | 100.0 | 98.0 |
| direct:ssn | 44 | 100.0 | 100.0 |
| direct:swift_bic | 41 | 92.7 | 82.9 |
| indirect:time | 40 | 97.5 | 97.5 |
| direct:date_of_birth | 36 | 100.0 | 100.0 |
| indirect:county | 35 | 60.0 | 60.0 |
| direct:cvv | 33 | 84.8 | 78.8 |
| direct:user_name | 32 | 96.9 | 90.6 |
| direct:biometric_identifier | 31 | 100.0 | 100.0 |
| direct:password | 29 | 89.7 | 82.8 |
| indirect:postcode | 29 | 100.0 | 100.0 |
| indirect:date_time | 26 | 96.2 | 96.2 |
| indirect:employment_status | 21 | 42.9 | 42.9 |
| direct:fax_number | 20 | 100.0 | 100.0 |
| direct:pin | 20 | 100.0 | 90.0 |
| direct:health_plan_beneficiary_number | 19 | 100.0 | 100.0 |
| direct:tax_id | 14 | 100.0 | 100.0 |
| indirect:education_level | 13 | 100.0 | 92.3 |
| direct:ipv4 | 11 | 100.0 | 100.0 |
| indirect:language | 10 | 90.0 | 90.0 |
| indirect:race_ethnicity | 10 | 90.0 | 90.0 |
| direct:medical_record_number | 10 | 100.0 | 100.0 |
| direct:api_key | 10 | 100.0 | 100.0 |
| indirect:age | 9 | 88.9 | 88.9 |
| direct:employee_id | 9 | 100.0 | 100.0 |
| direct:http_cookie | 8 | 87.5 | 37.5 |
| direct:mac_address | 8 | 100.0 | 100.0 |
| indirect:political_view | 7 | 71.4 | 71.4 |
| direct:unique_id | 7 | 100.0 | 100.0 |
| direct:ipv6 | 6 | 100.0 | 100.0 |
| direct:national_id | 5 | 100.0 | 100.0 |
| direct:certificate_license_number | 5 | 100.0 | 100.0 |
| indirect:religious_belief | 4 | 75.0 | 75.0 |
| indirect:gender | 4 | 100.0 | 100.0 |
| direct:device_identifier | 3 | 100.0 | 100.0 |
| indirect:blood_type | 2 | 100.0 | 100.0 |
| indirect:sexuality | 2 | 50.0 | 50.0 |
| direct:license_plate | 1 | 100.0 | 100.0 |
| direct:vehicle_identifier | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Investment Agreement | 58 | 96.6 | 96.6 |
| Mortgage Loan | 54 | 92.6 | 92.6 |
| Premium Payment Schedule | 48 | 100.0 | 100.0 |
| Emergency Planning | 44 | 68.2 | 68.2 |
| Corporate Solutions | 41 | 97.6 | 90.2 |
| Affidavit of No Contingencies | 40 | 90.0 | 90.0 |
| Privacy Policy Document | 39 | 94.9 | 92.3 |
| Investment Statement | 38 | 97.4 | 94.7 |
| Bank Services | 35 | 100.0 | 97.1 |
| Audit Report | 34 | 100.0 | 100.0 |
| Affidavit of No Unpaid Insurance Premiums | 34 | 61.8 | 58.8 |
| Debt Consolidation Agreement | 33 | 93.9 | 93.9 |
| Investment Proposal | 33 | 78.8 | 78.8 |
| Investment Strategy | 32 | 93.8 | 93.8 |
| Affidavit of Title | 31 | 93.5 | 93.5 |
| Due Diligence Report | 30 | 100.0 | 100.0 |
| Affidavit of No Unpaid Maintenance Fees | 30 | 93.3 | 86.7 |
| Credit Card Replacement Form | 29 | 89.7 | 89.7 |
| Application Setup Guide | 29 | 100.0 | 96.6 |
| Investment Evaluation | 29 | 86.2 | 86.2 |
| Risk Management Plan | 27 | 85.2 | 85.2 |
| Authorization Form | 27 | 70.4 | 70.4 |
| Investment Portfolio | 26 | 92.3 | 92.3 |
| Personal Identification | 26 | 100.0 | 100.0 |
| Power of Attorney | 26 | 96.2 | 96.2 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 27538 | 98.2 |
| CONTACT | 11716 | 99.5 |
| tier:indirect | 11421 | 82.2 |
| FIN_ID | 6153 | 97.7 |
| ORG | 5992 | 69.1 |
| DATE | 4335 | 96.4 |
| NAME | 3483 | 95.7 |
| ADDRESS | 3240 | 96.4 |
| SECRET | 1326 | 99.8 |
| GOV_ID | 1111 | 97.7 |
| DEMOGRAPHIC | 1094 | 98.2 |
| NETWORK | 509 | 100.0 |

## eval_gretel_en (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| GOV_ID | 341 | 98.5 | 95.0 |
| DATE | 225 | 100.0 | 100.0 |
| NAME | 224 | 100.0 | 96.0 |
| FIN_ID | 189 | 94.2 | 89.9 |
| ADDRESS | 101 | 100.0 | 80.2 |
| CONTACT | 100 | 96.0 | 95.0 |
| NETWORK | 50 | 100.0 | 100.0 |
| ORG | 16 | 100.0 | 62.5 |
| SECRET | 8 | 100.0 | 75.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:medical_record_number | 161 | 98.8 | 97.5 |
| direct:date_of_birth | 130 | 100.0 | 100.0 |
| direct:ssn | 103 | 98.1 | 91.3 |
| direct:street_address | 87 | 100.0 | 77.0 |
| direct:first_name | 78 | 100.0 | 100.0 |
| indirect:date | 77 | 100.0 | 100.0 |
| direct:last_name | 71 | 100.0 | 98.6 |
| direct:employee_id | 61 | 95.1 | 91.8 |
| direct:customer_id | 56 | 91.1 | 83.9 |
| direct:name | 55 | 100.0 | 85.5 |
| direct:phone_number | 50 | 92.0 | 90.0 |
| direct:email | 49 | 100.0 | 100.0 |
| direct:license_plate | 44 | 97.7 | 93.2 |
| direct:ipv4 | 36 | 100.0 | 100.0 |
| direct:credit_card_number | 35 | 97.1 | 91.4 |
| direct:user_name | 20 | 100.0 | 100.0 |
| indirect:company_name | 16 | 100.0 | 62.5 |
| direct:bank_routing_number | 14 | 100.0 | 100.0 |
| direct:account_number | 13 | 100.0 | 100.0 |
| direct:device_identifier | 12 | 100.0 | 100.0 |
| direct:certificate_license_number | 11 | 100.0 | 100.0 |
| indirect:date_time | 11 | 100.0 | 100.0 |
| direct:unique_id | 10 | 80.0 | 80.0 |
| direct:biometric_identifier | 7 | 100.0 | 100.0 |
| direct:vehicle_identifier | 7 | 100.0 | 85.7 |
| indirect:time | 7 | 100.0 | 100.0 |
| indirect:city | 6 | 100.0 | 100.0 |
| direct:password | 5 | 100.0 | 80.0 |
| indirect:postcode | 4 | 100.0 | 100.0 |
| direct:api_key | 3 | 100.0 | 66.7 |
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
| Invoice | 15 | 100.0 | 86.7 |
| Bill of Lading | 14 | 85.7 | 78.6 |
| Packing List | 14 | 85.7 | 85.7 |
| Incident Report | 13 | 100.0 | 92.3 |
| Vaccination Record | 13 | 100.0 | 100.0 |
| BillOfLading | 13 | 100.0 | 92.3 |
| PackageInsert | 12 | 100.0 | 91.7 |
| UserManual | 12 | 100.0 | 91.7 |
| IncidentReport | 12 | 91.7 | 91.7 |
| InsurancePolicy | 11 | 100.0 | 81.8 |
| Audit Report | 11 | 100.0 | 81.8 |
| Shipment Notice | 10 | 90.0 | 70.0 |
| Contract | 10 | 100.0 | 100.0 |
| CaseReportForm | 10 | 100.0 | 100.0 |
| PromotionDetails | 10 | 90.0 | 80.0 |
| DisciplinaryActionForm | 10 | 100.0 | 100.0 |
| QualityControlReport | 10 | 100.0 | 100.0 |
| Distribution Agreement | 10 | 100.0 | 90.0 |
| AccountClosureForm | 10 | 100.0 | 90.0 |
| Data Privacy Notice | 10 | 100.0 | 100.0 |
| Title Report | 10 | 100.0 | 90.0 |
| Bill | 10 | 100.0 | 100.0 |
| DrugMasterFile | 10 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 13550 | 96.5 |
| tier:indirect | 3813 | 69.1 |
| DATE | 3394 | 73.7 |
| GOV_ID | 3122 | 99.3 |
| ADDRESS | 2885 | 95.0 |
| NAME | 2477 | 93.3 |
| FIN_ID | 2251 | 98.6 |
| CONTACT | 1957 | 95.7 |
| NETWORK | 709 | 96.6 |
| ORG | 278 | 47.1 |
| SECRET | 149 | 97.3 |
| DEMOGRAPHIC | 141 | 0.0 |

## eval_adversarial (regression)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 224 | 95.1 | 92.4 |
| FIN_ID | 220 | 98.6 | 94.5 |
| ADDRESS | 112 | 97.3 | 88.4 |
| CONTACT | 80 | 100.0 | 100.0 |
| DATE | 28 | 100.0 | 100.0 |
| GOV_ID | 24 | 100.0 | 100.0 |
| ORG | 16 | 100.0 | 100.0 |
| SECRET | 4 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:name | 132 | 99.2 | 95.5 |
| direct:account_number | 76 | 100.0 | 98.7 |
| direct:iban | 60 | 100.0 | 100.0 |
| direct:first_name | 52 | 84.6 | 84.6 |
| direct:phone_number | 44 | 100.0 | 100.0 |
| direct:street_address | 40 | 92.5 | 75.0 |
| indirect:city | 40 | 100.0 | 100.0 |
| direct:last_name | 36 | 94.4 | 91.7 |
| direct:email | 36 | 100.0 | 100.0 |
| direct:credit_debit_card | 32 | 100.0 | 100.0 |
| indirect:postcode | 28 | 100.0 | 89.3 |
| indirect:date | 20 | 100.0 | 100.0 |
| direct:customer_id | 20 | 90.0 | 60.0 |
| direct:swift_bic | 20 | 95.0 | 85.0 |
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
| international formats | 124 | 97.6 | 89.5 |
| structured keys | 92 | 100.0 | 100.0 |
| email threads | 76 | 100.0 | 88.2 |
| SWIFT / FIX | 64 | 96.9 | 92.2 |
| common-word names | 56 | 94.6 | 92.9 |
| masked partials | 56 | 98.2 | 98.2 |
| coreference | 48 | 100.0 | 100.0 |
| odd spacing / line breaks | 44 | 100.0 | 100.0 |
| glued text | 40 | 82.5 | 80.0 |
| prompt injection | 40 | 100.0 | 100.0 |
| keyword ids | 24 | 100.0 | 100.0 |
| public bodies / dates | 24 | 100.0 | 100.0 |
| chat log | 20 | 95.0 | 90.0 |

### Recall by template exposure

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| templates also rendered (other values) for training | 356 | 98.3 | 94.4 |
| templates never used in training | 352 | 96.9 | 93.8 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 9074 | 92.2 |
| FIN_ID | 2829 | 93.5 |
| NAME | 2329 | 95.3 |
| CONTACT | 1917 | 97.9 |
| ADDRESS | 1382 | 87.0 |
| tier:indirect | 999 | 84.7 |
| DATE | 531 | 75.9 |
| ORG | 460 | 96.3 |
| GOV_ID | 310 | 96.1 |
| SECRET | 156 | 69.9 |
| NETWORK | 151 | 9.9 |
| DEMOGRAPHIC | 8 | 0.0 |

## eval_gretel_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 304 | 86.2 | 70.4 |
| ORG | 284 | 76.1 | 71.1 |
| ADDRESS | 200 | 95.5 | 88.0 |
| DATE | 94 | 96.8 | 94.7 |
| CONTACT | 69 | 98.6 | 95.7 |
| FIN_ID | 65 | 70.8 | 60.0 |
| GOV_ID | 19 | 100.0 | 94.7 |
| NETWORK | 11 | 100.0 | 100.0 |
| SECRET | 11 | 81.8 | 81.8 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 284 | 76.1 | 71.1 |
| direct:name | 271 | 86.7 | 69.7 |
| direct:street_address | 191 | 95.3 | 87.4 |
| indirect:date | 68 | 100.0 | 100.0 |
| direct:email | 36 | 100.0 | 100.0 |
| direct:phone_number | 33 | 97.0 | 90.9 |
| direct:first_name | 31 | 80.6 | 74.2 |
| indirect:time | 13 | 84.6 | 69.2 |
| direct:account_pin | 12 | 50.0 | 41.7 |
| direct:date_of_birth | 11 | 90.9 | 90.9 |
| direct:credit_card_security_code | 10 | 10.0 | 10.0 |
| direct:employee_id | 10 | 70.0 | 40.0 |
| direct:local_latlng | 9 | 100.0 | 100.0 |
| direct:customer_id | 9 | 100.0 | 88.9 |
| direct:ssn | 8 | 100.0 | 100.0 |
| direct:passport_number | 8 | 100.0 | 87.5 |
| direct:credit_card_number | 7 | 100.0 | 85.7 |
| direct:ipv4 | 7 | 100.0 | 100.0 |
| direct:password | 7 | 100.0 | 100.0 |
| direct:swift_bic_code | 6 | 100.0 | 100.0 |
| direct:iban | 6 | 100.0 | 100.0 |
| direct:ipv6 | 4 | 100.0 | 100.0 |
| direct:api_key | 4 | 50.0 | 50.0 |
| direct:bank_routing_number | 3 | 66.7 | 33.3 |
| direct:driver_license_number | 3 | 100.0 | 100.0 |
| indirect:date_time | 2 | 100.0 | 100.0 |
| direct:bban | 2 | 100.0 | 100.0 |
| direct:last_name | 1 | 100.0 | 100.0 |
| direct:user_name | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Loan Application | 101 | 97.0 | 93.1 |
| BAI Format | 50 | 90.0 | 80.0 |
| SWIFT Message | 47 | 89.4 | 87.2 |
| Policyholder's Report | 43 | 93.0 | 79.1 |
| IT support ticket | 39 | 92.3 | 82.1 |
| Customer support conversational log | 37 | 94.6 | 94.6 |
| Customer Agreement | 35 | 68.6 | 57.1 |
| Payment Confirmation | 31 | 90.3 | 83.9 |
| Audit Report | 31 | 100.0 | 87.1 |
| EDI | 31 | 83.9 | 74.2 |
| Supply Chain Management Agreement | 29 | 96.6 | 93.1 |
| FIX Protocol | 29 | 89.7 | 82.8 |
| Bill of Lading | 29 | 100.0 | 89.7 |
| Financial Risk Assessment | 25 | 100.0 | 96.0 |
| Regulatory Compliance Guide | 25 | 36.0 | 24.0 |
| Insurance Policy | 24 | 79.2 | 70.8 |
| Trade Confirmation | 23 | 95.7 | 87.0 |
| CSV | 21 | 100.0 | 95.2 |
| Financial Disclosure Statement | 21 | 42.9 | 33.3 |
| Compliance Certificate | 21 | 95.2 | 90.5 |
| MT940 | 17 | 41.2 | 29.4 |
| Employment Contract | 17 | 100.0 | 88.2 |
| Credit Card Statement | 16 | 81.2 | 75.0 |
| Email | 16 | 56.2 | 50.0 |
| Health Insurance Claim Form | 16 | 100.0 | 87.5 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 16097 | 68.9 |
| tier:indirect | 9408 | 51.2 |
| ADDRESS | 6583 | 80.8 |
| ORG | 5093 | 71.0 |
| NAME | 3765 | 93.7 |
| DATE | 3572 | 33.3 |
| CONTACT | 2914 | 38.2 |
| FIN_ID | 1231 | 37.2 |
| SECRET | 922 | 25.4 |
| DEMOGRAPHIC | 743 | 1.7 |
| NETWORK | 428 | 54.0 |
| GOV_ID | 254 | 85.0 |

## eval_nemotron_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 480 | 99.2 | 97.5 |
| NAME | 370 | 100.0 | 99.5 |
| ADDRESS | 265 | 97.7 | 93.2 |
| CONTACT | 262 | 99.6 | 99.6 |
| DATE | 221 | 97.7 | 97.7 |
| DEMOGRAPHIC | 158 | 72.8 | 70.3 |
| ORG | 127 | 99.2 | 99.2 |
| GOV_ID | 103 | 100.0 | 100.0 |
| NETWORK | 49 | 100.0 | 100.0 |
| SECRET | 34 | 97.1 | 94.1 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:first_name | 194 | 100.0 | 100.0 |
| direct:account_number | 167 | 99.4 | 99.4 |
| direct:last_name | 144 | 100.0 | 98.6 |
| indirect:date | 137 | 96.4 | 96.4 |
| indirect:company_name | 127 | 99.2 | 99.2 |
| direct:email | 121 | 99.2 | 99.2 |
| direct:customer_id | 106 | 100.0 | 100.0 |
| direct:url | 81 | 100.0 | 100.0 |
| direct:street_address | 71 | 100.0 | 90.1 |
| indirect:country | 67 | 92.5 | 89.6 |
| direct:credit_debit_card | 64 | 100.0 | 96.9 |
| direct:bank_routing_number | 61 | 100.0 | 96.7 |
| indirect:state | 45 | 97.8 | 93.3 |
| direct:phone_number | 43 | 100.0 | 100.0 |
| indirect:city | 35 | 100.0 | 100.0 |
| direct:date_of_birth | 35 | 100.0 | 100.0 |
| indirect:occupation | 33 | 81.8 | 81.8 |
| direct:user_name | 32 | 100.0 | 100.0 |
| indirect:time | 31 | 100.0 | 100.0 |
| indirect:employment_status | 31 | 38.7 | 32.3 |
| direct:swift_bic | 29 | 100.0 | 93.1 |
| indirect:postcode | 28 | 100.0 | 96.4 |
| direct:ipv4 | 26 | 100.0 | 100.0 |
| direct:biometric_identifier | 26 | 100.0 | 100.0 |
| direct:ssn | 25 | 100.0 | 100.0 |
| direct:cvv | 23 | 95.7 | 91.3 |
| indirect:race_ethnicity | 20 | 95.0 | 95.0 |
| direct:health_plan_beneficiary_number | 19 | 100.0 | 100.0 |
| indirect:date_time | 18 | 100.0 | 100.0 |
| direct:http_cookie | 17 | 94.1 | 88.2 |
| direct:pin | 17 | 88.2 | 82.4 |
| indirect:blood_type | 17 | 41.2 | 41.2 |
| direct:fax_number | 17 | 100.0 | 100.0 |
| indirect:education_level | 14 | 92.9 | 92.9 |
| direct:tax_id | 14 | 100.0 | 100.0 |
| direct:password | 12 | 100.0 | 100.0 |
| indirect:county | 11 | 100.0 | 100.0 |
| direct:mac_address | 10 | 100.0 | 100.0 |
| direct:ipv6 | 10 | 100.0 | 100.0 |
| indirect:religious_belief | 10 | 60.0 | 40.0 |
| direct:employee_id | 9 | 100.0 | 100.0 |
| indirect:age | 8 | 100.0 | 100.0 |
| indirect:language | 8 | 100.0 | 100.0 |
| direct:coordinate | 8 | 100.0 | 100.0 |
| direct:medical_record_number | 8 | 100.0 | 100.0 |
| indirect:sexuality | 8 | 75.0 | 75.0 |
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
| Mortgage | 401 | 95.8 | 93.3 |
| Investment | 342 | 97.1 | 96.5 |
| Banking | 337 | 98.2 | 96.7 |
| User Account and Transaction Services | 282 | 99.3 | 98.2 |
| Brokerage | 279 | 98.6 | 97.1 |
| Insurance | 214 | 92.1 | 91.6 |
| Credit | 214 | 97.7 | 96.7 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 23102 | 98.0 |
| CONTACT | 9056 | 99.3 |
| tier:indirect | 6738 | 94.8 |
| FIN_ID | 5036 | 99.0 |
| ADDRESS | 2786 | 94.4 |
| ORG | 2767 | 89.1 |
| NAME | 2614 | 94.9 |
| DATE | 2383 | 98.8 |
| SECRET | 1639 | 99.9 |
| DEMOGRAPHIC | 1588 | 98.5 |
| GOV_ID | 1064 | 94.6 |
| NETWORK | 907 | 99.3 |

## dev_nemotron_fin_structured (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 378 | 96.3 | 94.7 |
| NAME | 310 | 99.4 | 99.0 |
| DATE | 274 | 92.3 | 92.3 |
| ADDRESS | 189 | 89.9 | 86.2 |
| CONTACT | 171 | 100.0 | 100.0 |
| ORG | 135 | 99.3 | 99.3 |
| GOV_ID | 98 | 95.9 | 95.9 |
| DEMOGRAPHIC | 98 | 57.1 | 55.1 |
| SECRET | 25 | 84.0 | 76.0 |
| NETWORK | 19 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:date | 193 | 91.2 | 91.2 |
| direct:first_name | 164 | 100.0 | 100.0 |
| indirect:company_name | 135 | 99.3 | 99.3 |
| direct:last_name | 124 | 100.0 | 99.2 |
| direct:account_number | 121 | 95.0 | 94.2 |
| direct:customer_id | 86 | 100.0 | 97.7 |
| direct:email | 82 | 100.0 | 100.0 |
| direct:street_address | 59 | 100.0 | 91.5 |
| direct:credit_debit_card | 56 | 98.2 | 94.6 |
| direct:url | 50 | 100.0 | 100.0 |
| direct:bank_routing_number | 46 | 100.0 | 97.8 |
| indirect:country | 35 | 85.7 | 85.7 |
| direct:phone_number | 31 | 100.0 | 100.0 |
| direct:date_of_birth | 30 | 100.0 | 100.0 |
| indirect:occupation | 29 | 27.6 | 27.6 |
| indirect:time | 28 | 89.3 | 89.3 |
| indirect:state | 28 | 89.3 | 85.7 |
| direct:ssn | 27 | 100.0 | 100.0 |
| direct:cvv | 27 | 85.2 | 85.2 |
| direct:biometric_identifier | 25 | 100.0 | 100.0 |
| indirect:city | 23 | 100.0 | 100.0 |
| indirect:date_time | 23 | 95.7 | 95.7 |
| indirect:county | 22 | 54.5 | 50.0 |
| direct:user_name | 22 | 90.9 | 90.9 |
| indirect:postcode | 19 | 94.7 | 94.7 |
| direct:pin | 16 | 100.0 | 100.0 |
| indirect:employment_status | 15 | 33.3 | 33.3 |
| direct:medical_record_number | 15 | 100.0 | 100.0 |
| indirect:blood_type | 14 | 78.6 | 71.4 |
| direct:swift_bic | 13 | 100.0 | 100.0 |
| direct:password | 12 | 83.3 | 75.0 |
| indirect:race_ethnicity | 11 | 63.6 | 63.6 |
| direct:ipv4 | 10 | 100.0 | 100.0 |
| direct:http_cookie | 9 | 77.8 | 66.7 |
| direct:health_plan_beneficiary_number | 8 | 75.0 | 75.0 |
| direct:employee_id | 8 | 100.0 | 100.0 |
| direct:fax_number | 8 | 100.0 | 100.0 |
| indirect:language | 8 | 87.5 | 87.5 |
| direct:tax_id | 8 | 87.5 | 87.5 |
| indirect:religious_belief | 6 | 83.3 | 83.3 |
| direct:certificate_license_number | 6 | 100.0 | 100.0 |
| direct:national_id | 6 | 83.3 | 83.3 |
| direct:ipv6 | 5 | 100.0 | 100.0 |
| direct:unique_id | 5 | 40.0 | 40.0 |
| indirect:age | 5 | 80.0 | 80.0 |
| indirect:gender | 4 | 75.0 | 75.0 |
| direct:api_key | 4 | 100.0 | 100.0 |
| direct:coordinate | 3 | 100.0 | 100.0 |
| indirect:education_level | 3 | 100.0 | 100.0 |
| indirect:political_view | 3 | 100.0 | 66.7 |
| direct:device_identifier | 2 | 100.0 | 100.0 |
| direct:mac_address | 2 | 100.0 | 100.0 |
| direct:vehicle_identifier | 2 | 100.0 | 100.0 |
| direct:license_plate | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Risk Assessment | 33 | 87.9 | 87.9 |
| Affidavit of No Unpaid Assessments | 32 | 93.8 | 93.8 |
| Investment Strategy | 29 | 89.7 | 89.7 |
| Credit Policy Document | 27 | 96.3 | 96.3 |
| Trade Authorization | 26 | 80.8 | 80.8 |
| Medical Records Release Form | 25 | 100.0 | 100.0 |
| Investment Policy Statement | 24 | 100.0 | 100.0 |
| Investment Objectives | 22 | 100.0 | 100.0 |
| Market Analysis Report | 22 | 86.4 | 86.4 |
| Insurance Endorsement | 22 | 86.4 | 81.8 |
| Investment Forecast | 22 | 100.0 | 100.0 |
| Investment Review | 22 | 81.8 | 81.8 |
| System Diagnostic Log | 22 | 100.0 | 90.9 |
| blood bank inventory record | 21 | 66.7 | 61.9 |
| Account Closing Form | 21 | 100.0 | 100.0 |
| Quitclaim Deed | 20 | 90.0 | 85.0 |
| Incident Report | 20 | 100.0 | 100.0 |
| Investment Proposal | 20 | 100.0 | 100.0 |
| Insurance Compliance Report | 19 | 94.7 | 94.7 |
| Driver License | 19 | 100.0 | 100.0 |
| Debt Settlement Plan | 19 | 84.2 | 84.2 |
| Affidavit of No Unpaid Liabilities | 19 | 78.9 | 68.4 |
| Reinsurance Agreement | 19 | 100.0 | 94.7 |
| Affidavit of Title | 18 | 100.0 | 100.0 |
| clinical trial participant biometric file | 17 | 82.4 | 82.4 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 16343 | 96.4 |
| tier:indirect | 7883 | 80.6 |
| CONTACT | 6173 | 97.5 |
| ORG | 4328 | 66.4 |
| FIN_ID | 3975 | 97.9 |
| DATE | 2904 | 97.7 |
| NAME | 2067 | 95.7 |
| ADDRESS | 1936 | 96.1 |
| SECRET | 1065 | 83.4 |
| GOV_ID | 760 | 99.9 |
| DEMOGRAPHIC | 651 | 98.3 |
| NETWORK | 367 | 100.0 |

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
