# redactd benchmark report

Generated 2026-11-14 23:42 UTC · mode **standard** · shipped `redactd.pipeline.Pipeline` · 3 worker processes × 1 thread · total wall time 0.1 min

Recall = share of gold identifiers with ≥50% / ≥90% of their characters redacted. Precision = share of redacted characters that fall inside a gold span (Gretel leaves real PII unlabelled, so its precision understates reality). *Raw* uses dataset labels as-is; *policy* removes gold spans that are template placeholders and, for organisation labels only, generic phrases and public bodies (`bench/gold_policy.py`).

**Held-out** sets are never used to tune rules, thresholds or prompts. **Dev** sets are. The **regression** set (hand-built hard cases) was written by us and rules were fixed against it, so it shows that known hard cases pass, not how unseen text behaves.

## Summary

| Set | Role | Docs | Direct ≥50 raw | Direct ≥90 raw | Indirect ≥50 raw | Indirect ≥90 raw | Prec raw | Direct ≥50 pol | Direct ≥90 pol | Indirect ≥50 pol | Indirect ≥90 pol | Prec pol |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dev_nemotron_med | dev | 200 | 99.9 | 99.9 | 95.4 | 94.5 | 65.0 | 99.9 | 99.9 | 97.5 | 96.7 | 65.0 |

## Leak regression (A3)

`leak_check` must be empty for every rendered document. *Gold direct values in output* is a raw string search of the redacted output for every gold DIRECT value; it counts every miss and also short values that survive as substrings of unrelated words.

| Set | leak_check failures | Gold direct values still in output | of | Docs affected |
|---|---:|---:|---:|---:|
| dev_nemotron_med | 0 | 1 | 863 | 1 / 200 |

## Latency (per document, measured inside the worker; all workers busy)

| Set | mean chars | p50 ms | p95 ms | p99 ms | ms / 1k chars | stage share |
|---|---:|---:|---:|---:|---:|---|
| dev_nemotron_med | 665 | 43 | 183 | 576 | 105 | rules 1%, distilled 98%, finalize 1% |

## dev_nemotron_med (dev)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 488 | 99.8 | 99.8 |
| GOV_ID | 303 | 100.0 | 100.0 |
| DEMOGRAPHIC | 279 | 97.1 | 96.1 |
| DATE | 220 | 97.3 | 97.3 |
| CONTACT | 102 | 100.0 | 100.0 |
| ADDRESS | 77 | 88.3 | 88.3 |
| FIN_ID | 56 | 100.0 | 100.0 |
| ORG | 41 | 100.0 | 97.6 |
| SECRET | 8 | 100.0 | 100.0 |
| NETWORK | 5 | 100.0 | 100.0 |

### Recall per fine label (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| direct:first_name | 310 | 99.7 | 99.7 |
| direct:last_name | 175 | 100.0 | 100.0 |
| direct:medical_record_number | 172 | 100.0 | 100.0 |
| direct:date_of_birth | 107 | 100.0 | 100.0 |
| indirect:date | 86 | 96.5 | 96.5 |
| indirect:occupation | 83 | 94.0 | 92.8 |
| direct:health_plan_beneficiary_number | 78 | 100.0 | 100.0 |
| indirect:blood_type | 55 | 98.2 | 94.5 |
| indirect:gender | 50 | 100.0 | 100.0 |
| direct:email | 49 | 100.0 | 100.0 |
| indirect:company_name | 41 | 100.0 | 97.6 |
| direct:phone_number | 38 | 100.0 | 100.0 |
| indirect:age | 26 | 100.0 | 100.0 |
| direct:certificate_license_number | 25 | 100.0 | 100.0 |
| indirect:county | 24 | 62.5 | 62.5 |
| direct:biometric_identifier | 19 | 100.0 | 100.0 |
| direct:street_address | 15 | 100.0 | 100.0 |
| indirect:time | 15 | 86.7 | 86.7 |
| indirect:race_ethnicity | 14 | 100.0 | 100.0 |
| direct:employee_id | 14 | 100.0 | 100.0 |
| indirect:city | 14 | 100.0 | 100.0 |
| indirect:employment_status | 14 | 92.9 | 92.9 |
| indirect:state | 12 | 100.0 | 100.0 |
| indirect:date_time | 12 | 91.7 | 91.7 |
| indirect:language | 12 | 100.0 | 100.0 |
| indirect:religious_belief | 10 | 100.0 | 100.0 |
| direct:unique_id | 10 | 100.0 | 100.0 |
| direct:url | 9 | 100.0 | 100.0 |
| indirect:country | 8 | 100.0 | 100.0 |
| direct:ssn | 7 | 100.0 | 100.0 |
| direct:credit_debit_card | 7 | 100.0 | 100.0 |
| indirect:sexuality | 7 | 100.0 | 100.0 |
| direct:fax_number | 6 | 100.0 | 100.0 |
| direct:password | 6 | 100.0 | 100.0 |
| direct:cvv | 6 | 100.0 | 100.0 |
| direct:swift_bic | 6 | 100.0 | 100.0 |
| indirect:education_level | 6 | 83.3 | 83.3 |
| direct:device_identifier | 5 | 100.0 | 100.0 |
| direct:pin | 4 | 100.0 | 100.0 |
| direct:customer_id | 4 | 100.0 | 100.0 |
| direct:bank_routing_number | 4 | 100.0 | 100.0 |
| indirect:postcode | 4 | 100.0 | 100.0 |
| direct:user_name | 3 | 100.0 | 100.0 |
| direct:tax_id | 2 | 100.0 | 100.0 |
| indirect:political_view | 2 | 100.0 | 100.0 |
| direct:http_cookie | 2 | 100.0 | 100.0 |
| direct:account_number | 1 | 100.0 | 100.0 |

### Recall per document type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| Health Insurance Card | 47 | 100.0 | 100.0 |
| Medical Certificate | 44 | 95.5 | 95.5 |
| Emergency Information Form | 43 | 100.0 | 100.0 |
| Wellness Plan | 39 | 97.4 | 97.4 |
| Chronic Disease Management Plan | 37 | 100.0 | 100.0 |
| Age Verification | 35 | 100.0 | 100.0 |
| Advance Directive | 34 | 73.5 | 73.5 |
| Health Questionnaire | 33 | 100.0 | 100.0 |
| Healthcare Benefits Summary | 33 | 100.0 | 100.0 |
| Referral Letter | 33 | 100.0 | 100.0 |
| Immunization Record | 33 | 100.0 | 100.0 |
| Healthcare Proxy Form | 33 | 100.0 | 100.0 |
| Care Coordination Plan | 33 | 100.0 | 100.0 |
| Employment Contract | 33 | 100.0 | 100.0 |
| school biometric access profile | 32 | 100.0 | 100.0 |
| Therapy Progress Notes | 32 | 100.0 | 100.0 |
| Respite Care Plan | 30 | 100.0 | 100.0 |
| Surgical Record | 28 | 92.9 | 92.9 |
| Palliative Care Plan | 27 | 100.0 | 100.0 |
| Substance Abuse Treatment Plan | 26 | 100.0 | 100.0 |
| Arthritis Management Plan | 24 | 95.8 | 95.8 |
| SWIFT Code Document | 24 | 100.0 | 100.0 |
| Alzheimer's Care Plan | 24 | 100.0 | 100.0 |
| Discharge Summary | 24 | 100.0 | 100.0 |
| Health Screening Form | 23 | 100.0 | 100.0 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:indirect | 12818 | 40.7 |
| tier:direct | 11314 | 92.5 |
| DEMOGRAPHIC | 8980 | 24.4 |
| CONTACT | 3371 | 98.0 |
| NAME | 3260 | 90.7 |
| DATE | 2657 | 84.0 |
| GOV_ID | 2580 | 99.0 |
| ORG | 1181 | 66.9 |
| ADDRESS | 976 | 76.0 |
| FIN_ID | 561 | 91.4 |
| SECRET | 518 | 68.3 |
| NETWORK | 48 | 100.0 |

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
