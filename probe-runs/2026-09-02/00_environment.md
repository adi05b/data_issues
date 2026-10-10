# Probe run environment — 2026-09-02

## Endpoint discovery

| Candidate | Method | Result |
|---|---|---|
| `https://minmod.isi.edu/dashboard/sparqlsearch` | GET | 200 — Plotly **Dash** UI, not an endpoint. Queries run server-side via `/dashboard/_dash-update-component`; no SPARQL URL appears in the HTML or JS bundles. |
| **`https://minmod.isi.edu/sparql`** | **POST** | **200 — WORKING ENDPOINT** |
| `https://minmod.isi.edu/api/v1/sparql` | POST | 404 `{"detail":"Not Found"}` |
| `https://minmod.isi.edu/ontology/sparql` | POST | 405 `{"detail":"Method Not Allowed"}` |
| `https://minmod.isi.edu/dashboard/sparql` | POST | 405 Method Not Allowed |
| `https://minmod.isi.edu/api/sparql` | POST | 404 `{"detail":"Not Found"}` |

## Working endpoint

- **URL:** `https://minmod.isi.edu/sparql`
- **Method:** `POST` with `Content-Type: application/sparql-query`, body sent as `--data-binary @file.rq`. Accepted on the first try; the form-encoded fallback was never needed. No GET was ever used.
- **Auth:** none required (no credentials sent on any request in this run).
- **Accept:** `application/sparql-results+json`

## Response headers (smoke test)

```
HTTP/2 200
server: nginx/1.29.3
content-type: application/sparql-results+json; charset=utf-8
vary: Accept-Encoding
vary: Origin
fuseki-request-id: 4685
cache-control: must-revalidate,no-cache,no-store
pragma: no-cache
strict-transport-security: max-age=31536000; includeSubDomains; preload;
```

- **Server software:** Apache Jena **Fuseki** — confirmed by the `fuseki-request-id` header. 🟢
- **Fuseki version:** **not exposed.** No `X-Powered-By`, no version string in any header. nginx/1.29.3 is the reverse proxy in front, not the triplestore. 🔴 *(version-specific behaviour was established empirically by P0.5 instead — see below)*

## Smoke tests

- `ASK { ?s ?p ?o }` → `{"boolean": true}`
- `SELECT * WHERE { ?s ?p ?o } LIMIT 1` → `<https://minmod.isi.edu/ontology/> rdf:type owl:Ontology`

## Run window

- Start: 2026-09-02T21:48:05Z (dashboard fetch)
- End:   2026-09-02T22:03Z (last probe)
- 39 probes sent, 38 returned HTTP 200, 1 returned HTTP 400 (`P0.4-datatype`, amended as `P0.4-alt-datatype`).
- Total endpoint time: 335.9 s. Slowest single probe: 11.4 s (`3a`). No probe approached the §11 ten-minute limit; no timeouts.

## Harness

`run.sh` posts `<id>.rq` and writes `<id>.json` (raw curl bytes, never round-tripped through a JSON parser), `<id>.headers`, `<id>.meta.json`.
`tocsv.py` derives `<id>.csv` as a **separate** file with `<var>_bound` sibling columns. `show.py` renders a result for reading only.

## Not available in this environment

- **`data-quality-auditor` skill / `scripts/data_profiler.py`** — not installed on this machine (checked the local skills folder). The `<id>.profile.json` outputs specified in §3 could not be produced. The CSVs are written and are ready for the profiler if the skill is installed later. Profiling that the report needed (term type, datatype, % unbound, rows per site) was computed directly from the raw JSON instead and appears in `DATA_SHAPE.md`.
- **`ta2-minmod-data` / `ta2-minmod-kg` checkouts** — not present anywhere under the working directory. §9's upstream check and the SHACL grep could not be run. Nothing was cloned.
- **The ISWC paper** — not in this folder; only the four `.md` plan files are.
