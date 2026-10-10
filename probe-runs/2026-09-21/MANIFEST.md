# probe-runs/2026-09-21 — run manifest

*Aditi Bombe · 2026-09-21 · read-only. No graph mutation, no write endpoint contacted, TLS verification never disabled, no repository modified.*

## Endpoint status: UNREACHABLE

`minmod.isi.edu` (128.9.36.11) accepted no TCP connection on 443 or 80 and answered no ICMP,
across four attempts between 21:13Z and 21:24Z. Controls in the same seconds: `www.isi.edu` 200,
`example.com` 200, `cdn.proj.org` 206.

**This is NOT the 2026-09-13 certificate expiry.** No TLS handshake is reached, so there is no
certificate to inspect. curl fails with exit **28** (`Failed to connect to minmod.isi.edu port 443`),
not exit 60 (`SSL certificate problem`). See `00_connectivity.md` and `PF-0-ask.*`.

Same host, same result for the dedup REST API: `/api/v1/dedup-mineral-sites/{id}` -> curl exit 28.

## Queries sent

| id | result |
|---|---|
| `PF-0-ask` | HTTP 0, curl exit 28, 0 bytes, 75,038 ms. The only query the harness sent. |

## Queries staged and UNRUN

| file | section | note before firing |
|---|---|---|
| `PF-1.rq` | pre-flight — LocationInfo predicates | — |
| `PF-2.rq` | pre-flight — CRS node predicates | answers the unverified `:confidence` question |
| `S1-crs-distribution.rq` | 1 | **defective as written** — non-optional `:observed_name` drops 7,869 nodes |
| `S3-non4326-sweep.rq` | 3 | **defective as written** — same, plus the `4326` substring filter admits the one `WGS84`-literal node as a phantom |
| `S5-nad27-pairs.rq` | 5 | relaxes the both-sides-4326 filter that would otherwise exclude every NAD27 record by construction |

Section 2 needs the dedup REST API, not SPARQL; nothing staged.

## Offline analysis (all ran, all 🟢)

Environment: pyproj 3.8.0, PROJ 9.8.1, fresh venv in scratch space.
`PROJ_USER_WRITABLE_DIRECTORY` pointed at scratch; grid downloads confined there, no system PROJ data touched.

| script | output | what |
|---|---|---|
| `crs_sweep.py` | `crs_sweep.json` | per-CRS geographic/projected, axis order, area of use, no-op test; 4 corpus + 25 speculative codes |
| `noop_mechanism.py` | `noop_mechanism.json` | longitude sweep; rules out the "latitude outside ±90" explanation |
| `noop_proof.py` | `noop_proof.json` | no-op made to disappear by moving the swapped point inside NAD27's area of use |
| `s4_uncorrectable.py` | `s4-summary.json`, `s4-all-7720.csv` | first pass, flat-earth metres |
| `s4_grid_compare.py` | `s4-grid-net.json`, `s4-grid-nonet.json` | grids absent vs present |
| `s4_geodesic.py` | `s4-geodesic.json`, `s4-all-7720-geodesic.csv` | **final** — geodesic, all 7,720, both configurations |
| `s4_which_op.py` | `s4-which-op-net.json`, `s4-which-op-nonet.json` | operation PROJ selects per area of interest, with declared accuracy |

## Input substitution

The brief names `nad27_stored_as_wgs84.csv` and `04_nad27_datum.md`. **Neither exists** in
`data_issues/` or anywhere under `~`. Coordinates were taken from
`probe-runs/2026-09-14/n2-nad27-coords-all.csv` — 7,720 rows, verbatim WKT, HTTP 200,
`truncated_by_limit: false`, and the same file `NAD27_IMPACT.md` was computed from.
Section 4's numbers are therefore 2026-09-14 coordinates, not today's.

## Headline

The current code no-ops on 7,720/7,720 ARDF records (100.00%, bit-identical) — reproduced
independently on a different PROJ build. `EPSG:4267` is the only affected CRS in the corpus.
**The 24 "uncorrectable" records are correctable**; `us_noaa_alaska.tif` was simply absent.
