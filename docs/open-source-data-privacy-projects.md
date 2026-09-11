# Open Source Data Privacy Projects to Contribute To

Curated list of open-source projects across data privacy areas, with notes
on where they're most contributor-friendly, plus a survey of cutting-edge
topics that are still underbuilt.

## 1. PII detection & redaction (most relevant to `redactd`)

- **[microsoft/presidio](https://github.com/microsoft/presidio)** — detects,
  redacts, masks, and anonymizes PII in text, images, and structured data
  (NER + regex + rule-based recognizers, multi-language). ~8,800 stars, 183
  contributors, MIT license, actively releasing in 2026. Has labeled
  "good first issue" tickets and a separate
  [presidio-research](https://github.com/microsoft/presidio-research) repo
  for building/evaluating new PII recognizers — a good entry point for
  contributing new entity recognizers (e.g. non-US ID formats, new locales)
  rather than core architecture.
- **[OpenMined/PyDP](https://github.com/OpenMined/PyDP)** — Python wrapper
  around Google's DP library; smaller surface area, good for a first PR.

## 2. Differential privacy

- **[opendp/opendp](https://github.com/opendp/opendp)** — reference
  implementation behind the OpenDP Project (Harvard/Microsoft). Rust core
  with Python/R bindings. Rigorous, formal contribution/vetting process for
  new DP mechanisms — good for learning DP theory deeply.
- **[google/differential-privacy](https://github.com/google/differential-privacy)**
  — Google's C++/Go/Java DP libraries plus "Privacy on Beam" for
  pipeline-scale DP aggregation.
- **[IBM/differential-privacy-library](https://github.com/IBM/differential-privacy-library)**
  (diffprivlib) — scikit-learn-style DP library, easiest on-ramp for anyone
  familiar with Python ML tooling.
- **[tensorflow/privacy](https://github.com/tensorflow/privacy)** — DP-SGD
  optimizers for training models with formal privacy guarantees.

## 3. Federated learning & privacy-preserving ML

- **[OpenMined/PySyft](https://github.com/OpenMined/PySyft)** — flagship
  "compute on data you don't hold" framework combining federated learning,
  DP, and MPC. Large active community (Slack + GitHub Discussions), explicit
  contributor onboarding docs — probably the best community for mentorship.
- **[adap/flower](https://github.com/adap/flower)** (Flower) —
  framework-agnostic federated learning, very active, good docs.
- Alternatives: FederatedAI/FATE, TensorFlow Federated, FedML-AI/FedML.

## 4. Homomorphic encryption / secure multi-party computation

- **[zama-ai/concrete](https://github.com/zama-ai/concrete)** — Zama's fully
  homomorphic encryption compiler; one of the most active FHE projects
  (Rust, strong momentum in 2025–2026).
- **[homenc/HElib](https://github.com/homenc/HElib)**, Microsoft SEAL —
  established HE libraries.
- **[facebookresearch/CrypTen](https://github.com/facebookresearch/CrypTen)**
  — MPC for PyTorch, privacy-preserving ML via secure computation.
- **[data61/MP-SPDZ](https://github.com/data61/MP-SPDZ)** — general-purpose
  MPC framework widely used in research.

## 5. Anonymization & synthetic data

- **[arx-deidentifier/arx](https://github.com/arx-deidentifier/arx)** —
  mature Java tool implementing k-anonymity, l-diversity, t-closeness, and
  DP for tabular de-identification. Long-running academic project,
  approachable for algorithmic contributions.
- **[sdv-dev/SDV](https://github.com/sdv-dev/SDV)** (Synthetic Data Vault) —
  most widely used open synthetic tabular/relational/time-series data
  library; active issue tracker.
- **[vanderschaarlab/synthcity](https://github.com/vanderschaarlab/synthcity)**
  — research-grade synthetic data + privacy-evaluation library, good for
  those who like reading papers alongside code.

## Cutting-edge / underbuilt areas worth watching

- **Machine unlearning** — verifiably removing a user's data's influence
  from an already-trained model, directly tied to GDPR/CCPA "right to be
  forgotten" for AI models. Still young and academic; most implementations
  live in arXiv-linked repos rather than mature libraries, so it's a good
  area to get in early (search GitHub for "machine unlearning" / "graph
  unlearning" for current papers-with-code).
- **Zero-knowledge proofs for AI/privacy** — ZK proofs of unlearning, ZK
  proofs of model provenance/inference correctness without revealing
  weights. Mostly research code (e.g. work from a16z crypto, zkML
  frameworks like `ezkl`); high ceiling for anyone with a cryptography
  background.
- **Synthetic data provenance/governance** — as regulators (EU AI Act,
  GDPR) start requiring traceability of how synthetic training data was
  derived from real data, tooling for provenance-tagging synthetic datasets
  is thin — an underbuilt niche.
- **DP + synthetic data combined pipelines** — increasingly treated as the
  practical "standard" for privacy-safe data sharing; SDV/synthcity plus a
  DP layer is an active integration point.

## Sources

- [opendp/opendp](https://github.com/opendp/opendp)
- [OpenMined/PyDP](https://github.com/OpenMined/PyDP)
- [google/differential-privacy](https://github.com/google/differential-privacy)
- [IBM/differential-privacy-library](https://github.com/IBM/differential-privacy-library)
- [microsoft/presidio](https://github.com/microsoft/presidio)
- [presidio issues](https://github.com/microsoft/presidio/issues)
- [presidio-research](https://github.com/microsoft/presidio-research)
- [OpenMined/PySyft](https://github.com/OpenMined/PySyft)
- [Privacy Enhancing Technologies (PET) Initiative](https://github.com/privacy-enhancing-technologies)
- [data-anonymization GitHub topic](https://github.com/topics/data-anonymization)
- [SDV vs. SynthCity comparison paper](https://arxiv.org/pdf/2506.17847)
- [Data Privacy Trends 2026 (TrustArc)](https://trustarc.com/resource/2026-data-privacy-landscape-strategic-roadmap/)
- [zkUnlearner: Zero-Knowledge Framework for Verifiable Unlearning](https://arxiv.org/pdf/2509.07290)
- [ZK-APEX: Zero-Knowledge Approximate Personalized Unlearning](https://arxiv.org/pdf/2512.09953)
- [Checks and balances: ML and zero-knowledge proofs (a16z crypto)](https://a16zcrypto.com/posts/article/checks-and-balances-machine-learning-and-zero-knowledge-proofs/)
