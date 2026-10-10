Fixes #107

- **Both update handlers** (`handle_site_update`, `handle_sample_update`) now share one helper. `norm_literal` is used only as the comparison key: the DELETE removes the terms exactly as they are stored in Fuseki, and the INSERT writes the model's own terms. Before, the DELETE asked for `xsd:double`, missed the stored `xsd:decimal`, and left orphaned numbers (or, on Sample depths, two values for one field). The INSERT also turned decimals into doubles.
- **Decimal writer:** `xsd:decimal` literals are always written in plain notation (`5e-05` → `0.00005`), because exponents are not legal in `xsd:decimal`. All writers in `RDFModel` (`to_triples`, `to_graph`) go through one helper, and normal values such as `1.25` and `1.0` are written exactly as before.
- **Tests:** a site saved twice and a sample saved twice (with a depth change), each checked against the triple store directly: no `xsd:double`, no untyped orphan nodes, numbers stored as `xsd:decimal` and equal to the model, and one depth value after the change. Plus a unit test for small decimals. The three new tests fail on `main` and pass here.
- **Cleanup:** existing doubles and orphans in dev are cleared by a dev rebuild. Nothing is needed in prod, which has none.
- **Known edge:** a `5e-05`-style decimal already stored in the graph can still leave an orphan when that record is edited, because rdflib rewrites it on read. Prod's 6 such values are on ETL sites, which aren't edited through this path, and the next rebuild writes them correctly.

Stable URIs for nested nodes (the uuid4 in `rdf_model.py`) are left for a separate issue.

Sync tests pass against the real Fuseki/Postgres containers; the 3 new tests fail on `main`.
