# Neo4j Data Privacy Solutions: GDPR & CCPA

Notes on how Neo4j positions its graph database for GDPR/CCPA compliance work.

## Core idea: data lineage as a graph problem

Neo4j's central pitch is not "built-in compliance features" but that a **graph
model is structurally the right tool** for the hardest parts of GDPR/CCPA:
knowing where personal data lives and how it flows between systems.

GDPR (Art. 30) and CCPA both require answering "where did this person's data
come from, where did it go, and who touched it." Relational/NoSQL stores need
expensive joins across siloed systems to reconstruct that path. Modeling
systems, datasets, consent records, and personal-data flows as nodes/edges
lets you query lineage directly — e.g. "what is the lineage of report Y" or
"which systems hold data from user X."

## Right to be forgotten / data subject deletion requests

Because the graph already encodes which systems/tables/pipelines a given
individual's data touched, a deletion or access request becomes a graph
query that returns every location to purge or export, instead of manually
auditing each downstream system.

This was central to Neo4j's 2017–2018 GDPR push, including a partner
solution with **CluedIn** (a data-integration/master-data-management vendor)
combining Neo4j with CluedIn's PII discovery/data-unification layer to
automate GDPR right-to-be-forgotten and data-mapping workflows.

## CCPA-specific angle

Neo4j's CCPA content ("Graphs: The Secret to CCPA Success") makes the same
lineage argument applied to CCPA's requirements: consumers' rights to know
what's collected, opt out of sale, and request deletion. The claim is that
graph queries let a business answer "what do we have on this consumer and
where" fast enough to meet CCPA's response-time requirements, versus
building a one-off compliance data warehouse.

## Product-level compliance (platform certifications)

Separate from the graph-modeling pitch, **Neo4j AuraDB** (managed cloud
offering) advertises standard enterprise compliance certifications:
SOC 2 Type II, SOC 3, ISO 27001, ISO 20243, HIPAA, and stated GDPR/CCPA
readiness. This is a claim about the platform itself (hosting, DPA terms,
sub-processor disclosures), distinct from "helps you build a GDPR solution."

## Caveats

- Much of the concrete "GDPR/CCPA + Neo4j" content is old (2017–2020 press
  releases and landing pages) — reads as a marketing narrative built around
  GDPR's 2018 rollout and CCPA's 2020 rollout, not an actively evolving
  product line. No recent (2024–2026) material found suggesting a dedicated,
  actively maintained "privacy product" — it's positioned as a use case for
  the general graph platform plus a Data Processing Addendum.
- neo4j.com was not directly fetchable in the research environment used for
  this summary; findings are reconstructed from search snippets and
  third-party recaps of Neo4j's own blog posts and landing pages, not the
  primary source text.

## Sources

- [Data privacy, risk, and compliance graph database use cases](https://neo4j.com/use-cases/privacy-risk-compliance/)
- [Neo4j Offers Graph Solution for GDPR Compliance](https://www.prnewswire.com/news-releases/neo4j-offers-graph-solution-for-gdpr-compliance-300517754.html)
- [How to comply with GDPR by using Neo4j graphs](https://go.neo4j.com/using-graphs-to-comply-with-gdpr-lp.html)
- [No more talk: It's time to solve GDPR with Neo4j and CluedIn](https://go.neo4j.com/solving-gdpr-with-neo4j-and-cluedin-lp.html)
- [Overcoming CCPA Compliance Challenges: Why Graph Technology Is the Best Solution](https://neo4j.com/blog/ccpa-compliance-challenges-graph-technology-best-solution/)
- [Overcoming CCPA challenges: graph technology solves personal data privacy challenges](https://neo4j.com/blog/security/overcoming-ccpa-challenges-graph-technology-solves-personal-data-privacy-challenges/)
- [Neo4j, The Leader in Graph Databases (CCPA landing page)](https://go.neo4j.com/graphs-the-secret-to-ccpa-success-lp.html)
- [Neo4j Data Processing Addendum](https://neo4j.com/legal-terms/data-processing-addendum/)
- [Neo4j AuraDB product page](https://neo4j.com/product/auradb/)
- [Data lineage: Using knowledge graphs for deeper insights into your data pipelines](https://neo4j.com/blog/knowledge-graph/data-lineage-using-knowledge-graphs-deeper-insights-data-pipelines/)
