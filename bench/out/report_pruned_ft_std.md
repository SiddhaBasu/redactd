# redactd benchmark report

Generated 2026-11-13 18:16 UTC · mode **standard** · shipped `redactd.pipeline.Pipeline` · 2 worker processes × 1 thread · total wall time 1.6 min

Recall = share of gold identifiers with ≥50% / ≥90% of their characters redacted. Precision = share of redacted characters that fall inside a gold span (Gretel leaves real PII unlabelled, so its precision understates reality). *Raw* uses dataset labels as-is; *policy* removes gold spans that are template placeholders and, for organisation labels only, generic phrases and public bodies (`bench/gold_policy.py`).

**Held-out** sets are never used to tune rules, thresholds or prompts. **Dev** sets are. The **regression** set (hand-built hard cases) was written by us and rules were fixed against it, so it shows that known hard cases pass, not how unseen text behaves.

## Summary

| Set | Role | Docs | Direct ≥50 raw | Direct ≥90 raw | Indirect ≥50 raw | Indirect ≥90 raw | Prec raw | Direct ≥50 pol | Direct ≥90 pol | Indirect ≥50 pol | Indirect ≥90 pol | Prec pol |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| eval_gretel_fin | dev | 200 | 99.3 | 98.7 | 97.3 | 96.2 | 34.8 | 99.6 | 99.3 | 100.0 | 99.4 | 33.1 |
| eval_nemotron_fin | dev | 300 | 99.9 | 99.9 | 97.4 | 97.1 | 73.9 | 99.9 | 99.9 | 98.5 | 98.2 | 73.8 |
| dev_nemotron_fin_structured | dev | 200 | 99.7 | 99.5 | 95.2 | 92.4 | 71.4 | 99.7 | 99.5 | 98.8 | 97.7 | 71.2 |
| eval_gretel_fin_holdout | held-out | 300 | 99.0 | 97.8 | 96.0 | 94.0 | 31.7 | 99.5 | 99.3 | 98.4 | 97.8 | 30.6 |
| eval_fin_holdout2 | held-out | 300 | 99.4 | 98.3 | 93.0 | 91.3 | 33.4 | 99.8 | 99.1 | 95.5 | 94.2 | 32.9 |

## Leak regression (A3)

`leak_check` must be empty for every rendered document. *Gold direct values in output* is a raw string search of the redacted output for every gold DIRECT value; it counts every miss and also short values that survive as substrings of unrelated words.

| Set | leak_check failures | Gold direct values still in output | of | Docs affected |
|---|---:|---:|---:|---:|
| eval_gretel_fin | 0 | 3 | 513 | 3 / 200 |
| eval_nemotron_fin | 0 | 1 | 1270 | 1 / 300 |
| dev_nemotron_fin_structured | 0 | 1 | 824 | 1 / 200 |
| eval_gretel_fin_holdout | 0 | 4 | 773 | 4 / 300 |
| eval_fin_holdout2 | 0 | 3 | 720 | 3 / 300 |

## Latency (per document, measured inside the worker; all workers busy)

| Set | mean chars | p50 ms | p95 ms | p99 ms | ms / 1k chars | stage share |
|---|---:|---:|---:|---:|---:|---|
| eval_gretel_fin | 1481 | 161 | 572 | 694 | 120 | rules 1%, distilled 99%, finalize 1% |
| eval_nemotron_fin | 615 | 40 | 105 | 145 | 80 | rules 1%, distilled 98%, finalize 1% |
| dev_nemotron_fin_structured | 1031 | 88 | 595 | 686 | 138 | rules 1%, distilled 99%, finalize 1% |
| eval_gretel_fin_holdout | 1399 | 151 | 588 | 673 | 127 | rules 1%, distilled 99%, finalize 1% |
| eval_fin_holdout2 | 1427 | 165 | 569 | 655 | 122 | rules 1%, distilled 98%, finalize 1% |

## eval_gretel_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 304 | 99.7 | 98.7 |
| ORG | 284 | 96.5 | 95.4 |
| ADDRESS | 200 | 99.5 | 99.0 |
| DATE | 94 | 100.0 | 98.9 |
| CONTACT | 69 | 98.6 | 98.6 |
| FIN_ID | 65 | 96.9 | 96.9 |
| GOV_ID | 19 | 100.0 | 100.0 |
| NETWORK | 11 | 100.0 | 100.0 |
| SECRET | 11 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 284 | 96.5 | 95.4 |
| direct:name | 271 | 99.6 | 98.5 |
| direct:street_address | 191 | 99.5 | 99.0 |
| indirect:date | 68 | 100.0 | 100.0 |
| direct:email | 36 | 100.0 | 100.0 |
| direct:phone_number | 33 | 97.0 | 97.0 |
| direct:first_name | 31 | 100.0 | 100.0 |
| indirect:time | 13 | 100.0 | 92.3 |
| direct:account_pin | 12 | 100.0 | 100.0 |
| direct:date_of_birth | 11 | 100.0 | 100.0 |
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
| Loan Application | 101 | 100.0 | 100.0 |
| BAI Format | 50 | 96.0 | 96.0 |
| SWIFT Message | 47 | 100.0 | 100.0 |
| Policyholder's Report | 43 | 100.0 | 100.0 |
| IT support ticket | 39 | 100.0 | 100.0 |
| Customer support conversational log | 37 | 100.0 | 100.0 |
| Customer Agreement | 35 | 100.0 | 100.0 |
| Payment Confirmation | 31 | 96.8 | 96.8 |
| Audit Report | 31 | 100.0 | 100.0 |
| EDI | 31 | 100.0 | 100.0 |
| Supply Chain Management Agreement | 29 | 100.0 | 100.0 |
| FIX Protocol | 29 | 100.0 | 100.0 |
| Bill of Lading | 29 | 100.0 | 100.0 |
| Financial Risk Assessment | 25 | 100.0 | 96.0 |
| Regulatory Compliance Guide | 25 | 96.0 | 92.0 |
| Insurance Policy | 24 | 100.0 | 100.0 |
| Trade Confirmation | 23 | 100.0 | 100.0 |
| CSV | 21 | 100.0 | 100.0 |
| Financial Disclosure Statement | 21 | 100.0 | 100.0 |
| Compliance Certificate | 21 | 100.0 | 95.2 |
| MT940 | 17 | 100.0 | 100.0 |
| Employment Contract | 17 | 100.0 | 100.0 |
| Credit Card Statement | 16 | 100.0 | 100.0 |
| Email | 16 | 100.0 | 87.5 |
| Health Insurance Claim Form | 16 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:indirect | 27234 | 20.5 |
| tier:direct | 25765 | 46.5 |
| DEMOGRAPHIC | 13902 | 1.7 |
| ADDRESS | 9263 | 61.0 |
| ORG | 8033 | 51.2 |
| SECRET | 5625 | 4.2 |
| DATE | 5299 | 23.3 |
| NAME | 5028 | 79.3 |
| CONTACT | 3448 | 32.5 |
| FIN_ID | 1837 | 30.6 |
| NETWORK | 346 | 66.8 |
| GOV_ID | 218 | 83.5 |

## eval_nemotron_fin (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 480 | 100.0 | 100.0 |
| NAME | 370 | 100.0 | 100.0 |
| ADDRESS | 265 | 99.6 | 99.6 |
| CONTACT | 262 | 99.6 | 99.6 |
| DATE | 221 | 99.1 | 99.1 |
| DEMOGRAPHIC | 158 | 91.1 | 89.9 |
| ORG | 127 | 100.0 | 100.0 |
| GOV_ID | 103 | 100.0 | 100.0 |
| NETWORK | 49 | 100.0 | 100.0 |
| SECRET | 34 | 100.0 | 100.0 |

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
| direct:street_address | 71 | 100.0 | 100.0 |
| indirect:country | 67 | 100.0 | 100.0 |
| direct:credit_debit_card | 64 | 100.0 | 100.0 |
| direct:bank_routing_number | 61 | 100.0 | 100.0 |
| indirect:state | 45 | 97.8 | 97.8 |
| direct:phone_number | 43 | 100.0 | 100.0 |
| indirect:city | 35 | 100.0 | 100.0 |
| direct:date_of_birth | 35 | 100.0 | 100.0 |
| indirect:occupation | 33 | 93.9 | 93.9 |
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
| direct:http_cookie | 17 | 100.0 | 100.0 |
| direct:pin | 17 | 100.0 | 100.0 |
| indirect:blood_type | 17 | 58.8 | 58.8 |
| direct:fax_number | 17 | 100.0 | 100.0 |
| indirect:education_level | 14 | 100.0 | 92.9 |
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
| Mortgage | 401 | 98.8 | 98.5 |
| Investment | 342 | 99.4 | 99.4 |
| Banking | 337 | 100.0 | 100.0 |
| User Account and Transaction Services | 282 | 100.0 | 100.0 |
| Brokerage | 279 | 100.0 | 100.0 |
| Insurance | 214 | 96.3 | 95.8 |
| Credit | 214 | 98.6 | 98.6 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 25653 | 89.5 |
| tier:indirect | 14353 | 45.8 |
| CONTACT | 9078 | 99.1 |
| DEMOGRAPHIC | 8616 | 20.5 |
| FIN_ID | 5190 | 97.2 |
| ADDRESS | 3396 | 82.6 |
| ORG | 3118 | 78.4 |
| NAME | 3012 | 82.8 |
| SECRET | 2955 | 58.0 |
| DATE | 2619 | 90.1 |
| GOV_ID | 1074 | 94.3 |
| NETWORK | 948 | 95.0 |

## dev_nemotron_fin_structured (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| FIN_ID | 378 | 99.2 | 99.2 |
| NAME | 310 | 100.0 | 100.0 |
| DATE | 274 | 97.8 | 94.5 |
| ADDRESS | 189 | 93.7 | 92.1 |
| CONTACT | 171 | 100.0 | 100.0 |
| ORG | 135 | 99.3 | 99.3 |
| GOV_ID | 98 | 100.0 | 100.0 |
| DEMOGRAPHIC | 98 | 89.8 | 84.7 |
| SECRET | 25 | 100.0 | 88.0 |
| NETWORK | 19 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:date | 193 | 97.4 | 92.7 |
| direct:first_name | 164 | 100.0 | 100.0 |
| indirect:company_name | 135 | 99.3 | 99.3 |
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
| indirect:occupation | 29 | 75.9 | 69.0 |
| indirect:time | 28 | 100.0 | 100.0 |
| indirect:state | 28 | 89.3 | 89.3 |
| direct:ssn | 27 | 100.0 | 100.0 |
| direct:cvv | 27 | 88.9 | 88.9 |
| direct:biometric_identifier | 25 | 100.0 | 100.0 |
| indirect:city | 23 | 100.0 | 95.7 |
| indirect:date_time | 23 | 95.7 | 95.7 |
| indirect:county | 22 | 59.1 | 50.0 |
| direct:user_name | 22 | 100.0 | 100.0 |
| indirect:postcode | 19 | 100.0 | 100.0 |
| direct:pin | 16 | 100.0 | 100.0 |
| indirect:employment_status | 15 | 86.7 | 86.7 |
| direct:medical_record_number | 15 | 100.0 | 100.0 |
| indirect:blood_type | 14 | 100.0 | 100.0 |
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
| Trade Authorization | 26 | 100.0 | 92.3 |
| Medical Records Release Form | 25 | 100.0 | 100.0 |
| Investment Policy Statement | 24 | 100.0 | 100.0 |
| Investment Objectives | 22 | 100.0 | 100.0 |
| Market Analysis Report | 22 | 90.9 | 86.4 |
| Insurance Endorsement | 22 | 100.0 | 90.9 |
| Investment Forecast | 22 | 100.0 | 100.0 |
| Investment Review | 22 | 86.4 | 81.8 |
| System Diagnostic Log | 22 | 100.0 | 100.0 |
| blood bank inventory record | 21 | 90.5 | 90.5 |
| Account Closing Form | 21 | 100.0 | 100.0 |
| Quitclaim Deed | 20 | 95.0 | 90.0 |
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
| tier:direct | 18547 | 87.8 |
| tier:indirect | 13619 | 48.6 |
| CONTACT | 6313 | 96.5 |
| DEMOGRAPHIC | 5253 | 16.4 |
| ORG | 4953 | 58.7 |
| FIN_ID | 4195 | 94.0 |
| DATE | 3413 | 83.7 |
| ADDRESS | 2459 | 79.7 |
| NAME | 2282 | 87.4 |
| SECRET | 2088 | 52.9 |
| GOV_ID | 855 | 97.5 |
| NETWORK | 355 | 98.6 |

## eval_gretel_fin_holdout (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 439 | 99.3 | 98.2 |
| ORG | 437 | 95.7 | 93.4 |
| ADDRESS | 244 | 98.0 | 97.1 |
| DATE | 130 | 97.7 | 96.9 |
| CONTACT | 125 | 98.4 | 95.2 |
| FIN_ID | 94 | 100.0 | 100.0 |
| NETWORK | 19 | 100.0 | 100.0 |
| GOV_ID | 15 | 100.0 | 100.0 |
| SECRET | 10 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 437 | 95.7 | 93.4 |
| direct:name | 406 | 99.3 | 98.0 |
| direct:street_address | 240 | 97.9 | 97.1 |
| indirect:date | 85 | 98.8 | 97.6 |
| direct:phone_number | 81 | 97.5 | 96.3 |
| direct:email | 44 | 100.0 | 93.2 |
| indirect:time | 25 | 92.0 | 92.0 |
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
| Bill of Lading | 98 | 98.0 | 94.9 |
| CSV | 89 | 100.0 | 100.0 |
| IT support ticket | 74 | 98.6 | 97.3 |
| Loan Application | 73 | 100.0 | 98.6 |
| Health Insurance Claim Form | 65 | 96.9 | 96.9 |
| Business Plan | 61 | 93.4 | 93.4 |
| ISDA Definition | 61 | 95.1 | 86.9 |
| Insurance Claim Form | 48 | 97.9 | 97.9 |
| Policyholder's Report | 43 | 93.0 | 93.0 |
| Payment Confirmation | 42 | 100.0 | 97.6 |
| FpML | 38 | 100.0 | 100.0 |
| Financial Aid Application | 38 | 100.0 | 100.0 |
| SWIFT Message | 38 | 100.0 | 100.0 |
| Trade Confirmation | 37 | 100.0 | 100.0 |
| Safety Data Sheet | 36 | 100.0 | 100.0 |
| Customer support conversational log | 36 | 100.0 | 100.0 |
| Email | 34 | 100.0 | 100.0 |
| Regulatory Filing | 33 | 97.0 | 97.0 |
| Financial Statement | 33 | 100.0 | 100.0 |
| EDI | 31 | 100.0 | 100.0 |
| Insurance Policy | 30 | 100.0 | 100.0 |
| Tax Return | 24 | 95.8 | 95.8 |
| Financial Risk Assessment | 22 | 100.0 | 100.0 |
| Compliance Certificate | 22 | 100.0 | 100.0 |
| Corporate Governance Guidelines | 21 | 100.0 | 90.5 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:indirect | 42411 | 19.0 |
| tier:direct | 40865 | 42.8 |
| DEMOGRAPHIC | 22010 | 1.6 |
| ADDRESS | 14391 | 48.0 |
| ORG | 11511 | 52.7 |
| DATE | 8890 | 18.1 |
| NAME | 8463 | 75.3 |
| SECRET | 7132 | 4.2 |
| CONTACT | 6997 | 28.8 |
| FIN_ID | 2878 | 40.3 |
| NETWORK | 794 | 70.8 |
| GOV_ID | 210 | 71.9 |

## eval_fin_holdout2 (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| ORG | 413 | 91.3 | 89.3 |
| NAME | 396 | 99.0 | 98.5 |
| ADDRESS | 271 | 99.6 | 97.4 |
| DATE | 156 | 98.1 | 97.4 |
| FIN_ID | 96 | 100.0 | 100.0 |
| CONTACT | 81 | 100.0 | 97.5 |
| GOV_ID | 21 | 100.0 | 100.0 |
| NETWORK | 15 | 100.0 | 100.0 |
| SECRET | 7 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| indirect:company | 413 | 91.3 | 89.3 |
| direct:name | 376 | 98.9 | 98.4 |
| direct:street_address | 267 | 99.6 | 97.4 |
| indirect:date | 110 | 99.1 | 99.1 |
| direct:phone_number | 49 | 100.0 | 98.0 |
| direct:email | 32 | 100.0 | 96.9 |
| indirect:time | 24 | 91.7 | 87.5 |
| direct:employee_id | 21 | 100.0 | 100.0 |
| direct:bban | 16 | 100.0 | 100.0 |
| direct:date_of_birth | 15 | 100.0 | 100.0 |
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
| direct:credit_card_security_code | 5 | 100.0 | 100.0 |
| direct:user_name | 5 | 100.0 | 100.0 |
| direct:password | 4 | 100.0 | 100.0 |
| direct:local_latlng | 4 | 100.0 | 100.0 |
| direct:iban | 4 | 100.0 | 100.0 |
| direct:api_key | 3 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Insurance Policy | 91 | 98.9 | 98.9 |
| Bill of Lading | 86 | 98.8 | 97.7 |
| CSV | 66 | 100.0 | 100.0 |
| Payment Confirmation | 64 | 96.9 | 96.9 |
| IT support ticket | 54 | 100.0 | 96.3 |
| Customer support conversational log | 49 | 100.0 | 100.0 |
| Health Insurance Claim Form | 45 | 100.0 | 100.0 |
| Loan Application | 44 | 100.0 | 97.7 |
| Credit Card Statement | 36 | 91.7 | 91.7 |
| Shareholder Agreement | 35 | 74.3 | 74.3 |
| Investment Prospectus | 34 | 94.1 | 94.1 |
| Audit Report | 32 | 100.0 | 100.0 |
| BAI Format | 32 | 100.0 | 100.0 |
| FIX Protocol | 31 | 96.8 | 93.5 |
| SWIFT Message | 31 | 100.0 | 90.3 |
| Safety Data Sheet | 30 | 83.3 | 83.3 |
| Tax Return | 30 | 100.0 | 100.0 |
| Real Estate Loan Agreement | 29 | 96.6 | 96.6 |
| Policyholder's Report | 29 | 89.7 | 82.8 |
| Transaction Confirmation | 28 | 100.0 | 100.0 |
| Compliance Certificate | 27 | 100.0 | 100.0 |
| ISDA Definition | 26 | 96.2 | 88.5 |
| Insurance Claim Form | 25 | 96.0 | 96.0 |
| MT940 | 25 | 96.0 | 96.0 |
| Annual Report | 24 | 95.8 | 91.7 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 40921 | 42.2 |
| tier:indirect | 38179 | 23.0 |
| DEMOGRAPHIC | 17957 | 2.3 |
| ADDRESS | 15152 | 53.3 |
| ORG | 12210 | 52.6 |
| NAME | 8211 | 72.7 |
| DATE | 8012 | 24.3 |
| SECRET | 7021 | 2.6 |
| CONTACT | 7008 | 19.2 |
| FIN_ID | 2742 | 38.5 |
| NETWORK | 461 | 88.1 |
| GOV_ID | 326 | 69.9 |

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
