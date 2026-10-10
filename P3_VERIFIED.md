# P3_VERIFIED.md — Problem 3 checked against the real rule

*Aditi Bombe · run 2026-09-15 · verification pass over `P3_AFFECTED_RECORDS.md` · **read-only**, 7 queries + 60 REST reads, nothing written.*
*Record in `probe-runs/2026-09-14/` (`v*` files). Confidence: 🟢 verified · 🟡 likely · 🔴 assumed.*

**Gate.** `ASK { ?s ?p ?o }` → `HTTP 200`, `true`. 🟢 `v0-gate.json`

---

## Lead: what changed

**Both flagged errors are confirmed, and correcting them changed the membership of the headline finding almost entirely — while leaving its size intact.**

> The election count goes from **1,123 → 1,269**. But only **419 of the original 1,123 survive**. **704 were artefacts** of the wrong default score, and **850 are newly found**. The old set and the new set overlap by 33%.

That is the most serious correction in this run, and it is not visible from the totals. A reader comparing 1,123 to 1,269 would conclude the finding was robust. It was not — it was **roughly two-thirds wrong in its particulars** while being about the right size. Anyone who had started opening the named groups from the old list would have been working from a list that is 63% incorrect.

**The finding itself survives, and is now validated against the real system rather than simulated.** 20/20 on the API check (§2).

---

## 1 — Corrections

| # | Claim in `P3_AFFECTED_RECORDS.md` | Corrected | Why |
|---|---|---|---|
| 1 | "1,778 of 7,362 groups (24.1%) contain no scored member … the election among them is arbitrary" | **Wrong. Withdrawn.** Unscored → `DEFAULT_SOURCE_SCORE = 0.5` | Confirmed 🟢 |
| 2 | "`P9HTERGK` … is the single biggest loser of good coordinates" (524 groups) | **Artefact.** It is now **both** #2 elected-coarser (396) **and** #2 discarded-better (571) | My simulation ranked unscored sources at −1.0, i.e. last. 🟢 |
| 3 | "give the seven unscored sources a trust score" | **Reversed — see §3** | They are already at 0.5; a lower score makes it worse |
| 4 | Tie-break "arbitrary" | **Deterministic**: `(source_id, record_id, modified_at)` descending | Confirmed 🟢 |
| 5 | **1,123** groups elect a coarser coordinate | **1,269** — but only 419 in common | 🟢 `v1-election-corrected.csv` |
| 6 | "Two groups elect a `(0,0)` placeholder over a real coordinate" | **One**, under the real rule | 🟢 |
| 7 | *(new)* — not previously measured | **5,555 groups (75.5%) are decided by the alphabetical tie-break, not by score** | 🟢 |
| 8 | *(new)* — not previously measured | **0 groups contain an expert (1.0) record.** The human-edit tier is irrelevant here | 🟢 |
| 9 | MRDS DMS false-positive rate "≈1.3%" (from `PRECISION_ANALYSIS.md`) | **0.030%** under a both-axes rule | 🟢 — see §6 |

**Unchanged and re-verified:** populations A (6,046), B (5,287), C (36, of which 13 carry no CRS) and A ∩ B (463) all re-derive exactly, re-parsed from raw WKT in Python rather than trusting the SPARQL filters. 🟢 `v_recheck.py`

### Correction 1, resolved 🟢

`created_by` splits cleanly: `/users/s/…` are the five system accounts (679,737 sites), `/users/u/…` and `/users/a/…` are humans (**44 sites total**). 🟢 `v1a-createdby`

The real rule, implemented exactly: expert → `1.0`; otherwise `min(source_score or 0.5, 0.99)`; ties on `(source_id, record_id, modified_at)` descending.

**The report was wrong and the code is right.** My earlier simulation used `scores.get(src, -1.0)`, which ranked all seven unscored sources *below* every scored one — the precise inverse of the real behaviour. `P9HTERGK` (42,744 records, unscored → 0.5) could therefore never be elected in the old simulation, which manufactured its appearance as a pure victim. Under the real rule it both wins and loses in large numbers, which is what a big feed at the default score should do.

---

## 2 — Does section 4 survive?

**Yes, and it is now the best-verified finding in Problem 3.** 🟢

### The `owl:sameAs` proxy, tested against the real dedup table

The dedup entities are absent from SPARQL but reachable at `/api/v1/dedup-mineral-sites/{id}`, and each site exposes `dedup_site_uri`. Twenty groups drawn from the corrected 1,269: 🟢 `v2-proxy-check.json`

| Check | Result |
|---|---|
| Elected and best record land in the **same** dedup entity | **20 / 20** |
| sameAs component is a **subset** of the dedup entity | **20 / 20** |
| Member lists **identical** | 10 / 20 |
| **Dedup entity's coordinate == the simulation's predicted elected coordinate** | **20 / 20** |
| Dedup entity's coordinate == the better available one | **0 / 20** |

**The prediction matched on all twenty**, so the proxy is sound and section 4 stands.

**One qualification the test exposed, which strengthens rather than weakens it:** in 10 of 20 cases the real dedup entity contains **more** records than the sameAs component — my pair query required *both* sides to carry EPSG:4326 coordinates, so members without them were never pulled. The component is always a subset, never a superset. **1,269 is therefore a lower bound**; the true count can only be higher. 🟢

### The corrected finding

| | |
|---|---|
| Multi-record groups | 7,362 |
| **Electing a materially coarser coordinate (>3×)** | **1,269 (17.2%)** |
| Separation ≤ 1 km | 933 (73.5%) |
| Separation 1–11 km | 258 (20.3%) |
| Separation > 50 km (likely bad links, not precision loss) | 41 (3.2%) |
| Electing `(0,0)` over a real coordinate | 1 |

**Most often elected but coarser:** `mrds` 460 (rank 0.1), `P9HTERGK` 396 (0.5), `podchrome` 165 (0.5), `major-deposits` 46, `deposit` 46 (0.7).
**Most often discarded but better:** `mrds` 592 (0.1), `P9HTERGK` 571 (0.5), `P9K1HBNT` 64, `api.cdr.land` 26.

**The mechanism is not what the original report said.** It is not misplaced trust and not arbitrariness. **75.5% of groups are decided by reverse-alphabetical source id**, because the scores tie — and with most sources sitting at the 0.5 default, ties are the normal case rather than the exception. The election is effectively *sorting by URL* three-quarters of the time.

---

## 3 — Revised recommendations

### ❌ Drop — and reverse — "give the seven unscored sources a trust score"

**This recommendation was wrong and acting on it could have made things worse.** The seven unscored sources already rank at 0.5 by default, above MRDS (0.1) and level with most of the graph. Assigning them anything below 0.5 would demote 42,744 `P9HTERGK` records — currently the second-largest holder of *better* discarded coordinates — and increase the number of groups electing a coarse value. If scores are to be set for them, the only safe direction is **upward**, and only with evidence.

### ✅ Keep, and strengthen — a resolution tie-break

Now the primary recommendation, and the evidence is stronger than before. Since **75.5% of groups tie on score**, the tie-break is where the damage happens, and it currently sorts by source URL. Inserting coordinate resolution *ahead of* `source_id` in `SystemCmpKey` — after the score, before the alphabetical fields — would address the large majority of the 1,269 without touching the trust model at all. It changes no source data and fabricates nothing: it picks between two numbers already in the database.

### ✅ Keep — `(0,0)` must never be electable

One group elects Null Island over a real coordinate (was two). Small, but categorically wrong, and a resolution tie-break alone will not fix it — `POINT(0 0)` has *zero* decimals and would lose on resolution, so in this instance the tie-break happens to help. A placeholder guard is still the correct fix. See §4 for where the zeros come from.

### ✅ Keep — the ontology precision field

Untouched by this run and still correct.

---

## 4 — Where `(0, 0)` comes from

All 36 pulled with full provenance. 🟢 `v3-nullisland-all`

**The 13 and the 23 differ in exactly one thing: whether a `:crs` node exists.** Every other field behaves identically across both groups — same `created_by` (`/users/s/inferlink`), same document structure, overlapping `modified_at` windows (both start 2024-11-13, within 80 seconds of each other).

**The more informative finding is the WKT spelling.** Three distinct serialisations appear — `POINT(0 0)` (27), `POINT(0.0 0.0)` (6), `MULTIPOINT(0 0)` (3) — and they are spread across **both** the CRS and no-CRS groups **and** across all three months:

| | with CRS | without CRS |
|---|---|---|
| `POINT(0 0)` | 20 | 7 |
| `POINT(0.0 0.0)` | 2 | 4 |
| `MULTIPOINT(0 0)` | 1 | 2 |

So the split is **not** two code paths and **not** two extractor versions — both hypotheses are excluded by the cross-tabulation. 🟢 Three spellings of the same zero, uncorrelated with everything else, is what you get when a value is *parsed and re-serialised* per record rather than written as a constant. That points at the zeros arriving as data 🟡 — but this cannot be settled from the graph, and I am not claiming it. 🔴

**Many of these records know where they are.** `country_obs` is populated on 22 of 36 — Canada (10), Mexico, Spain — and `state_obs` names Ontario, Sonora, Quebec, Salamanca. The extractor captured the region and still wrote zeros for the coordinate.

**The route to the source document is direct and now established:** `record_id` is a prefix of the document hash, and `:reference` → `:document` → `:uri` resolves to a PDF. Every one of the 36 has one. 🟢

```
record_id 0205e384bede4889373d9e97  ("SONORA LITHIUM PROJECT")
  -> https://web.minmod.isi.edu/files/0205e384bede4889373d9e9788b27e984c76aec51a0ba876f098cd08541ac7ab54.pdf
```

---

## 5 — Populations A and B: prepared, not answered 🔴

**The graph cannot say whether the source published these values.** Samples and paths below; **nothing is claimed about file contents.** 🔴

### Population A — top three by rate, plus top by volume

| Source | Rate | Team | Likely repo path 🔴 | Sample `record_id` + stored WKT |
|---|---|---|---|---|
| `mrdata.usgs.gov/ree` | 37.02% | `umn` | `ta2-minmod-data/data/mineral-sites/umn/mrdata-usgs-gov-ree/` | `100` `POINT (79 39.5)` · `104` `POINT (-105.4 38.2)` · `106` `POINT (102 25.5)` · `114` `POINT (-51.75 -16)` |
| `mrdata.usgs.gov/phosphate` | 32.69% | `umn` | `…/umn/mrdata-usgs-gov-phosphate/` | `102` `POINT (139 -20)` · `103` `POINT (145 -23)` · `1008` `POINT (21 51.25)` · `1006` `POINT (22.9 51.7)` |
| `api.cdr.land/v1/docs/documents` | 30.19% | `inferlink` | `…/inferlink/api-cdr-land-v1-docs-documents/` | `02003096a464…` `POINT(24.6 45.7)` · `0202df58d4d9…` `POINT(21.0 -22.0)` · `020a4657b12d…` `POINT(105.0 46.0)` |
| `mrdata.usgs.gov/nicrpge` | 21.68% (**3,892 records**) | `umn` | `…/umn/mrdata-usgs-gov-nicrpge/` | `101137` `POINT (117.06 -20.8)` · `102902` `POINT (131 -12.97)` · `103380` `POINT (152.5 -26.52)` |

Worth noting for whoever opens these: `ree` record `109` is `POINT (-49.083333333333 -27.8)` — a **repeating decimal on one axis and 1 dp on the other**. That is the A ∩ B signature, and there are 463 of them.

### Population B — the two 100% feeds

| Source | Rate | Team | Likely repo path 🔴 | Sample `record_id` + stored WKT |
|---|---|---|---|---|
| `mrdata.usgs.gov/vms` | **100.00%** (1,090/1,090) | `umn` | `…/umn/mrdata-usgs-gov-vms/` | `1000` `POINT (-71.9588888888888931 45.318…)` · `1002` `POINT (-101.5875000000000057 54.61…)` · `1007` `POINT (5.0822222222222200 61.50166…)` |
| `mrdata.usgs.gov/carbonatite` | **100.00%** (60/60) | `umn` | `…/umn/mrdata-usgs-gov-carbonatite/` | `10` `POINT (-46.8866666666667 -18.92027…)` · `14` `POINT (-119.175 52.3094444444444)` · `16` `POINT (-83.165 47.7477777777778)` |

A feed at *exactly* 100% is a strong hint at systematic conversion rather than a historical survey convention 🟡 — but `carbonatite` `14` (`-119.175`, a clean 3-dp value, paired with a repeating one) is the kind of record that would distinguish the two, and only the file can say.

---

## 6 — The MRDS control, run first 🟢

`v6-mrds-control` — 20,000 MRDS records, EPSG:4326, `ORDER BY ?site`.

| | |
|---|---|
| Eligible (≥6 stored decimals) | 20,000 |
| Falsely classified as DMS | **6** (0 arcminute, 6 arcsecond) |
| **False-positive rate** | **0.030%** |
| Verdict | **PASS** — MRDS reads as ordinary decimals |

**This is 43× better than the ~1.3% `PRECISION_ANALYSIS.md` reported**, and the difference is a real methodological improvement worth recording: that run appears to have tested **either** axis against the grid, while this one requires **both**. Requiring both is the correct test — a DMS conversion converts the whole coordinate, not one axis — and it removes almost all chance agreement. The detector is sound, so the B figure below rests on solid ground.

**This sample is `ORDER BY ?site`-deterministic, not random** 🟡, so it is a real slice rather than a uniform sample. Site URIs sort on record id, which has no relationship to coordinate formatting, so bias is unlikely — but it is not a random draw and I am not claiming it is.

### Re-derived counts

| Population | Earlier | Re-derived | |
|---|---|---|---|
| A — coarse, ≤1 dp either axis, EPSG:4326 | 6,046 | **6,046** | ✅ |
| B — arcminute or arcsecond, ≥6 dp tested | 5,287 | **5,287** (1,539 arcmin + 3,748 arcsec) | ✅ |
| C — Null Island | 36 | **36** (23 with CRS, 13 without) | ✅ |
| A ∩ B | 463 | **463** | ✅ |

All re-parsed from raw WKT in Python, independently of the SPARQL `FILTER`s that produced the pulls. 🟢

---

## 7 — The GitHub checklist

Everything about file contents is 🔴.

### 1. `SystemCmpKey` and the dedup ranking · **1,269 groups**

**Question: can coordinate resolution be inserted after the score and before `source_id`?**

75.5% of groups tie on score and fall through to reverse-alphabetical source id. That is where the damage is, and it is a one-line change to a sort key. Confirm the descending sort and that `max`-by-key matches the real selection — my simulation assumed it and matched the API 20/20, but the code is the authority. 🟡

### 2. `config.py` — `DEFAULT_SOURCE_SCORE` · **policy, not a bug**

**Question: is 0.5 the intended default, and is MRDS at 0.1 deliberate?**

MRDS is the largest feed in the graph (479,760 records) at the *lowest* score, and is simultaneously the most-elected-coarser and most-discarded-better source. Both follow from that one number. **Do not lower the seven unscored sources** — see §3.

### 3. The Inferlink extractor's coordinate path · **36 records**

**Question: where do zeros enter, and why do 13 records get no `:crs` node while 23 get EPSG:4326?**

Three WKT spellings rule out both a single constant and an extractor-version split. The document link is direct — `record_id` prefixes the PDF hash — so each of the 36 can be checked against its source document.

### 4. `ta2-minmod-data` — populations A and B · **11,333 records**

**Question: did the source publish these values, or did our ingest produce them?**

Paths and samples in §5. For B, the sharper question: `vms` and `carbonatite` are *exactly* 100% DMS.

### 5. The `(0,0)` guard

**Question: is there any placeholder check before a coordinate is elected?**

One group still elects Null Island. A resolution tie-break happens to fix this instance; an explicit guard fixes the class.

---

## Run record — `probe-runs/2026-09-14/`

| File | What |
|---|---|
| `v0-gate.json` | gate |
| `v1a-createdby` | system vs expert user split |
| `v1b-coord-pairs-full` | 15,349 pairs with `created_by`, `record_id`, `modified_at` |
| `v1-election-corrected.csv` | 1,269 groups, with an `in_earlier_set` column |
| `v2-proxy-check.json` | 20-group API validation |
| `v3-nullisland-all` | all 36 with provenance |
| `v6-mrds-control` | 20,000-record control |
| `v_election.py` `v_proxy.py` `v_recheck.py` | offline analysis |

All queries HTTP 200. `v6-mrds-control` is the only pull with a `LIMIT` (deliberate, 20,000, flagged above); every other pull is complete. Nothing written to the graph; no `ta2-minmod-*` checkout touched.
