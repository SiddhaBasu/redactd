# redactd benchmark report

Generated 2026-11-13 11:35 UTC · mode **thorough** · shipped `redactd.pipeline.Pipeline` · 2 worker processes × 1 thread · total wall time 0.4 min

Recall = share of gold identifiers with ≥50% / ≥90% of their characters redacted. Precision = share of redacted characters that fall inside a gold span (Gretel leaves real PII unlabelled, so its precision understates reality). *Raw* uses dataset labels as-is; *policy* removes gold spans that are template placeholders and, for organisation labels only, generic phrases and public bodies (`bench/gold_policy.py`).

**Held-out** sets are never used to tune rules, thresholds or prompts. **Dev** sets are.

## Summary

| Set | Role | Docs | Direct ≥50 raw | Direct ≥90 raw | Indirect ≥50 raw | Indirect ≥90 raw | Prec raw | Direct ≥50 pol | Direct ≥90 pol | Indirect ≥50 pol | Indirect ≥90 pol | Prec pol |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| eval_adversarial | held-out | 160 | 100.0 | 99.7 | 100.0 | 100.0 | 76.2 | 100.0 | 99.7 | 100.0 | 100.0 | 76.1 |

## Leak regression (A3)

`leak_check` must be empty for every rendered document. *Gold direct values in output* is a raw string search of the redacted output for every gold DIRECT value; it counts every miss and also short values that survive as substrings of unrelated words.

| Set | leak_check failures | Gold direct values still in output | of | Docs affected |
|---|---:|---:|---:|---:|
| eval_adversarial | 0 | 0 | 592 | 0 / 160 |

## Latency (per document, measured inside the worker; all workers busy)

| Set | mean chars | p50 ms | p95 ms | p99 ms | ms / 1k chars | stage share |
|---|---:|---:|---:|---:|---:|---|
| eval_adversarial | 147 | 210 | 401 | 461 | 1628 | rules 0%, openmed 11%, gliner 88%, finalize 0% |

## eval_adversarial (held-out)

### Recall per coarse type (raw labels)

| | n | ≥50% | ≥90% |
|---|---:|---:|---:|
| NAME | 224 | 100.0 | 99.6 |
| FIN_ID | 220 | 100.0 | 100.0 |
| ADDRESS | 112 | 100.0 | 99.1 |
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
| direct:street_address | 40 | 100.0 | 97.5 |
| indirect:city | 40 | 100.0 | 100.0 |
| direct:last_name | 36 | 100.0 | 100.0 |
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
| structured keys | 92 | 100.0 | 100.0 |
| email threads | 76 | 100.0 | 98.7 |
| SWIFT / FIX | 64 | 100.0 | 100.0 |
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
| templates never used in training | 352 | 100.0 | 99.7 |

### Character precision by predicted type (policy-adjusted gold)

| predicted | chars | precision |
|---|---:|---:|
| tier:direct | 10459 | 80.9 |
| FIN_ID | 3544 | 79.6 |
| NAME | 2460 | 89.9 |
| CONTACT | 1954 | 96.1 |
| tier:indirect | 1916 | 49.8 |
| ADDRESS | 1489 | 82.1 |
| SECRET | 719 | 12.9 |
| ORG | 706 | 78.3 |
| DEMOGRAPHIC | 609 | 0.8 |
| DATE | 601 | 65.9 |
| GOV_ID | 240 | 100.0 |
| NETWORK | 53 | 0.0 |
