# P6_DIAGNOSIS.md: KG sync strands numeric triples on edit (issue ta2-minmod-kg#107)

*Aditi Bombe · USC ISI · run 2026-10-07 · **investigation only, read-only**. Live queries were SELECT/ASK only. Nothing was fixed. No branch, commit, PR, or issue comment was made.*
*Code: `usc-isi-i2/ta2-minmod-kg` @ **`83f9b7b2580790b2c7e197610ae905bd23c49a74`** (main, 2026-09-29). Every line number below is at this SHA unless another repo is named.*
*Run record: `probe-runs/2026-10-07/` (see `MANIFEST.md`). Confidence: 🟢 verified by running it · 🟡 likely, read from code · 🔴 assumed.*

---

## 1. Summary (for non-engineers)

1. **Amandeep is right about the cause.** When an existing site or sample is saved, the sync rewrites its numbers in a different number format and fails to delete the old copies, which stay behind detached from everything. 🟢
2. **Any save triggers it, even one that only changes a name.** It happens once per record, though: later saves of the same record clean up after themselves, so junk does not pile up with every edit. 🟢
3. **Only records curators edit can be hit:** a curator's own copy of a site (from their second save onwards) and GeoChem samples and sites. The bulk team data (UMN, SRI, USC, Inferlink) cannot be edited through this path. 🟢 / 🟡
4. **Production is clean today:** none of the 3.6 million number values checked are affected. That is because the production graph was rebuilt from backup on 28 Jul 2026 and no edit has reached it since. The bug is still in the code and will fire on the next qualifying save. 🟢
5. **The website's numbers come from Postgres, which never reads the graph, so they are not affected.** Only people who query the SPARQL endpoint directly would see stale or doubled values. 🟢 / 🟡

---

## 2. Location table

| repo | file | function | lines | commit SHA |
|---|---|---|---|---|
| ta2-minmod-kg | `minmodkg/misc/utils.py` | `norm_literal` (**the converter**) | 19–26 | 83f9b7b |
| ta2-minmod-kg | `minmodkg/services/sync/kgsync_listener.py` | `handle_site_update` (**bug site 1**) | 61–82 (norm 68–69, DELETE 73–76, INSERT 77–80, write 82) | 83f9b7b |
| ta2-minmod-kg | `minmodkg/services/sync/kgsync_listener.py` | `handle_sample_update` (**bug site 2**) | 128–149 (norm 135–136, DELETE 140–143, INSERT 144–147, write 149) | 83f9b7b |
| ta2-minmod-kg | `minmodkg/services/sync/kgsync_listener.py` | `_get_mineral_site_graph_by_uri` / `_get_sample_graph_by_uri` (read the old graph) | 187–203 / 151–166 | 83f9b7b |
| ta2-minmod-kg | `minmodkg/libraries/rdf/rdf_model.py` | `ResourceSchema.get_uri` / `get_uriref` / `get_uri_n3` (**uuid4 minting**) | 79–120 (uuid4 at 87, 100, 117) | 83f9b7b |
| ta2-minmod-kg | `minmodkg/libraries/rdf/rdf_model.py` | `_parse_type_hint` (Python `float` → `xsd:decimal`) | 344–354 (351) | 83f9b7b |
| ta2-minmod-kg | `minmodkg/libraries/rdf/triple_store.py` | `TripleStore.delete_insert` (`DELETE {…} INSERT {…} WHERE {}`) | 217–235 | 83f9b7b |
| ta2-minmod-kg | `minmodkg/libraries/rdf/fuseki.py` | `FusekiDB._sparql_update` (POST to `/minmod/update`) | 41–55 | 83f9b7b |
| ta2-minmod-kg | `minmodkg/api/routers/mineral_site.py` | `update_site` (PUT) / `create_site` (POST) | 138–187 / 104–121 | 83f9b7b |
| ta2-minmod-kg | `minmodkg/api/routers/sample.py` | `update_sample` (PUT) / `patch_sample` (PATCH) / `create_sample` / `publish_paper` | 66–103 / 106–136 / 34–63 / 139– | 83f9b7b |
| ta2-minmod-kg | `minmodkg/services/mineral_site.py` | `MineralSiteService.update` / `.create` | 270–353 / 146–268 | 83f9b7b |
| ta2-minmod-kg | `minmodkg/services/sample.py` | `SampleService.update` / `.patch` / `.create` | 207–252 / 256–416 / 158–202 | 83f9b7b |
| ta2-minmod-kg | `minmodkg/services/sync/sync.py`, `listener.py`, `__main__.py`, `geochem.py` | `process_pending_events`, `Listener.handle`, sync loops | 14–75; 14–42; 16–57; 21–47 | 83f9b7b |
| ta2-minmod-editor | `www/src/pages/editor/components/edit-dedup-site/EditSiteField.tsx` | save handler (create vs update) | 647–680 | 3272355 |
| ta2-minmod-editor | `www/src/models/mineralSite/MineralSiteStore.ts` | `createAndUpdateDedup` / `updateAndUpdateDedup` | 21–41 | 3272355 |

**Age of the bug:** `handle_site_update` has had this exact normalise-then-diff logic since **`52f3e62`, 17 Jan 2025** (`git log -S norm_literal`), unchanged through main. `norm_literal` itself dates from `7ddc532`, 27 Dec 2024, "tested virtuoso implementation". `handle_sample_update` copied the logic in `8acdc58`, 3 Sep 2026. 🟢

---

## 3. The edit path, hop by hop

**Direction: Postgres first, graph second.** The API writes the edit to Postgres together with an `event_log` row in one transaction. A separate polling process later replays the event into Fuseki. Nothing flows from Fuseki back to Postgres. 🟢 (code read, plus the offline run of the last two hops)

| # | Hop | Where | What happens |
|---|---|---|---|
| 1 | Curator saves in the editor | editor `EditSiteField.tsx:647–680` | Looks for a site in the dedup group that the **current user** created (`site.createdBy.includes(currentUser.url)`, line 648). **If there is none, it POSTs a new curator-owned site** (`createAndUpdateDedup`, line 680). If there is one, it **PUTs that site** (`updateAndUpdateDedup`, line 678). `ConfirmDataButton.tsx:115–118` makes the same choice. 🟡 |
| 2 | HTTP | editor `MineralSiteStore.ts:17` → `${SERVER}/api/v1/mineral-sites[/{id}]`; nginx `location /api/` → `api:8000` (`containers/nginx/nginx.conf`) | 🟡 |
| 3 | API route | `api/routers/mineral_site.py:138` `update_site` | For any site that is not GeoChem, **the owner is forced to the editing user** (`if not is_geochem: owner = user.get_uri()`, 157–158). A URL id that does not match is rejected (161–168). **A curator can PUT only their own sites. GeoChem sites (`owner == GEOCHEM_USER_URI`) can be PUT by any curator** (155). Samples: `sample.py:66` (PUT), `:106` (PATCH), `:139` (`/papers/publish`). 🟡 |
| 4 | Postgres write | `services/mineral_site.py:270–353` `update` | One REPEATABLE READ transaction does three things. It recomputes the **dedup row from Postgres rows** (313–338). It updates the site row (341). It adds `EventLog.from_site_update(site, edited_by, changed)` (350). Then it commits (353). Samples: `services/sample.py:252` (update), `:416` (patch), `:202` (create). 🟡 |
| 5 | Event row | `models/kgrel/event.py:57–74` | `event_log` row `type="site:update"` holding `site.to_dict()` as JSON. The five event types are listed at 25–33. 🟡 |
| 6 | **Trigger** | `services/sync/__main__.py:29–54`, run as `docker-compose.yml:67–73` `api_sync` (`python -m minmodkg.services.sync …`) | A `while True` loop calls `process_pending_events(KGSyncListener())` **every ~1 s** (`time.sleep(1)`, 54). The GeoChem lane runs the same class with `lane="geochem"` in `services/sync/geochem.py:32–37`. It is **polling, not a DB trigger or queue.** 🟡 |
| 7 | Batch | `services/sync/sync.py:30–56` | Selects up to 500 rows with `kg_synced == False`, ordered by id. Calls `listener.handle(events)` (49). Marks them synced (52–56). 🟡 |
| 8 | Dispatch | `services/sync/listener.py:14–42` | `site:update` → `handle_site_update(MineralSiteAndInventory.from_dict(event.data["site"]))`. 🟡 |
| 9 | Build and diff | `kgsync_listener.py:61–80` | `site.ms.to_kg().to_graph()` gives the new graph. A CONSTRUCT gives the old graph (`_get_mineral_site_graph_by_uri`, 187–203). **Both are passed through `norm_literal`**, set differences are taken, and the result is serialised with `.n3()`. 🟢 (run) |
| 10 | Write | `triple_store.py:217–235` → `fuseki.py:41` | `DELETE { … } INSERT { … } WHERE {}` POSTed to `update_endpoint` (`http://kg:3030/minmod/update` in `config.yml.template`). 🟢 (text generated, then executed on local Jena TDB2) |
| 11 | Store | `containers/fuseki/config.ttl:20–25`, `Dockerfile` | Fuseki **5.2.0**, TDB2, service `minmod` with a `sparql` endpoint (query) and an `update` endpoint. Public `https://minmod.isi.edu/sparql` is nginx `location = /sparql` → `kg:3030/minmod/sparql` (`nginx.conf:149–156`), which is query-only. The Fuseki container binds `127.0.0.1:{PORT}:3030` (`etl.yml:32`), which is Amandeep's "prod Fuseki only listens on localhost". 🟡 |

---

## 4. Mechanism

### 4a. `norm_literal`: what it converts 🟢

```python
# minmodkg/misc/utils.py:19-26
def norm_literal(val: Node) -> Node:
    """Normalize the literal value between triple store and python. For example, xsd.decimal saved to Virtuoso is converted into xsd.double when read back."""
    if isinstance(val, Literal):
        if val.datatype in {XSD.decimal, XSD.float, XSD.double}:
            return MyLiteral(val.value, datatype=XSD.double)
        elif val.datatype is None or val.datatype == XSD.string:
            return MyLiteral(str(val.value), datatype=None, lang=val.language)
    return val
```

Run on every literal kind (`p6-repro-results.json` → `S0-norm_literal-table`):

| input | output | effect |
|---|---|---|
| `"1.25"^^xsd:decimal` | `"1.25"^^xsd:double` | **re-typed** |
| `"1.25"^^xsd:float` | `"1.25"^^xsd:double` | **re-typed** |
| `"1.25"^^xsd:double` | `"1.25"^^xsd:double` | unchanged |
| `"3"^^xsd:integer` | unchanged | — |
| `"true"^^xsd:boolean`, `xsd:date`, `xsd:dateTime` | unchanged | — |
| `"abc"^^xsd:string` | `"abc"` (plain) | harmless: plain and `xsd:string` are the same term in RDF 1.1 |
| `"abc"@en` | `"abc"@en` | language tag kept |
| IRI | unchanged | — |

**Only decimal, float, and double are affected.** Integers, booleans, dates, datetimes, language-tagged strings, and IRIs are not. 🟢

**Callers:** only `kgsync_listener.py` lines **68, 69, 135, 136**, via the import at line 5. 🟢 (grep) There is a **different** function with the same name, `rdf_model.norm_literal` (`rdf_model.py:375–380`). It returns the Python value and is used only by `from_graph` (199, 201), so it does not take part in the sync diff. 🟡

The docstring says it exists because **Virtuoso** reads decimals back as doubles. Virtuoso is commented out in `docker-compose.yml:12–17`, and the store is Fuseki. Fuseki returns `xsd:decimal` unchanged, so the normalisation now only causes harm. 🟢 (Jena run: decimals came back as decimals)

### 4b. Where the DELETE is built: yes, from the normalised terms 🟢

```python
# kgsync_listener.py:64-82 (handle_site_update; handle_sample_update 131-149 is identical)
kgms = site.ms.to_kg()
ng = kgms.to_graph()                                   # new graph: float -> "x"^^xsd:decimal
og = self._get_mineral_site_graph_by_uri(kgms.uri)     # old graph read from Fuseki: "x"^^xsd:decimal
current_triples = {(s, p, norm_literal(o)) for s, p, o in og}   # decimal -> double
new_triples     = {(s, p, norm_literal(o)) for s, p, o in ng}   # decimal -> double
del_triples = [... for s, p, o in current_triples.difference(new_triples)]   # DELETE built from DOUBLES
add_triples = [... for s, p, o in new_triples.difference(current_triples)]   # INSERT built from DOUBLES
MINMOD_KG.delete_insert(del_triples, add_triples)
```

`delete_insert` (`triple_store.py:222–233`) emits `DELETE { <ground triples> } INSERT { … } WHERE {}`. A ground DELETE removes only exact RDF terms, and `"1.25"^^xsd:double` is not the same term as `"1.25"^^xsd:decimal`. Jena TDB2 keeps them as different values, so the numeric triple stays. Text, boolean, integer, and IRI triples are unchanged by `norm_literal`, so those **are** removed, including `rdf:type` and the parent's link to the node. 🟢

### 4c. Where the INSERT is built: also from normalised terms, so it writes `xsd:double` 🟢

The same normalised set produces the INSERT (lines 77–80), so every numeric value that is inserted is `xsd:double`. Jena stores it as a canonical double, which reads back as `1.25e0` (seen in the repro: `12.75e0^^xsd:double`). For comparison, the add path (`handle_site_add`, 36–59) uses `to_triples()` → `MyLiteral(x, datatype=xsd:decimal)` (`rdf_model.py:231, 241`) and **writes decimals**. So added and edited records end up with different datatypes. 🟢

### 4d. Nested-node URIs: a new uuid4 on every save 🟢

```python
# rdf_model.py:79-90 (get_uriref 92-103 and get_uri_n3 105-120 are the same)
def get_uri(self, resource):
    if self.subj.key is not None:
        return getattr(resource, self.subj.key)
    if not hasattr(resource, "__uri__"):
        setattr(resource, "__uri__",
                self.subj.key_ns.uristr(self.subj.type.name + "_" + str(uuid4()).replace("-", "_")))
    return getattr(resource, "__uri__")
```

The URI is cached on the Python object, and `to_kg()` builds fresh objects from the event JSON. **So every save gets new URIs for every nested node.** 🟢 (repro: `Measure_d0202384…` in S1 becomes `Measure_603e0322…` in S2)

| uuid4, minted fresh each save (`Subject` has no `key`) | stable (`key="uri"`) |
|---|---|
| `CandidateEntity` (`candidate_entity.py:14`), `LocationInfo`, `MineralInventory`, `Measure`, `Reference`, `PageInfo`, `BoundingBox`, `GeologyInfo`, `RockType`, GeoChem `Element`, `Isotope`, `Analysis`, `EditEvent` | `MineralSite`, `Sample`, `Document`, `DataSource`, `Paper`, and the vocabulary entities (`Commodity`, `Country`, `Unit`, …) |

Because the URIs differ, every nested triple ends up in either the delete set or the insert set, **including when nothing in that node changed.** 🟢

### 4e. Proof: generated DELETE/INSERT, executed offline 🟢

The real listener functions were called on a synthetic curator site and sample. The SPARQL they generated was executed on a throwaway **Apache Jena 5.2.0 TDB2** directory (same engine and storage as prod's Dockerfile) through the `tdb2.tdbupdate`/`tdb2.tdbquery` CLIs. No server was started, the network was disabled, and Docker was not used. Full text is in `probe-runs/2026-10-07/p6-repro-sparql.log`.

One node's trail. S1, `handle_site_add`, INSERT DATA (log line 51):
```
mr:Measure_d0202384_04f5_4747_a3d8_a043c13f8745 mo:value "1.25"^^xsd:decimal .
```
S2, `handle_site_update` after a **name-only** edit (the `##### S2` block of the log; the same node's DELETE line is log line 80):
```
DELETE {
  ...
  mr:Measure_d0202384_04f5_4747_a3d8_a043c13f8745 mo:value "1.25"^^xsd:double.      <- asks for a DOUBLE; store holds a DECIMAL
  mr:Measure_d0202384_04f5_4747_a3d8_a043c13f8745 rdf:type mo:Measure.             <- matches, deleted
  mr:MineralInventory_… mo:grade mr:Measure_d0202384_04f5_4747_a3d8_a043c13f8745.   <- matches, deleted (inbound link gone)
  mr:site__mrdata-usgs-gov-mrds__10014570__curator1 rdfs:label "Eagle Mine".
  ...
} INSERT {
  mr:site__mrdata-usgs-gov-mrds__10014570__curator1 rdfs:label "Eagle Mine (renamed)".
  mr:Measure_603e0322_3a02_4356_9226_6772c05ba5d8 mo:value "1.25"^^xsd:double.      <- new uuid, DOUBLE
  ...
} WHERE {}
```
After S2, the store holds `Measure_d0202384… mo:value 1.25 (xsd:decimal)` with **no `rdf:type` and nothing pointing to it.** It is an orphan.

Store state after each step (`p6-repro-results.json`):

| step | orphan triples | `xsd:double` literals | stale value still attached |
|---|---|---|---|
| S1 site add | 0 | 0 | 0 |
| **S2 site update, name only** | **11** (5 `confidence`, 2 `value`, 4 BoundingBox) | **11** | 0 |
| S3 site update, grade 1.25 → 1.3 | **11 (no new)** | 11 | 0 |
| S4 sample add | 11 | 11 | 0 |
| **S5 sample update, name only** | **15** (+2 `gco:grade`, +1 `detection_limit`, +1 `confidence`) | 15 | 0 |
| **S6 sample update, `top_depth_m` 12.5 → 12.75** | 15 (no new) | 16 | **1** (`top_depth_m` = `12.5^^decimal` **and** `12.75e0^^double` on the live Sample) |

### What the run changes in his reading

| his claim | verdict | evidence |
|---|---|---|
| Decimals become doubles on edit (`1.25` → `1.25e0`) | **Confirmed** | S2: 11 doubles 🟢 |
| `norm_literal` re-types before the DELETE, so the DELETE matches nothing numeric | **Confirmed** | log S2 + census 🟢 |
| INSERT writes doubles | **Confirmed** | log S2 🟢 |
| Nested nodes get new UUIDs every save, old ones orphaned | **Confirmed** | S2, S5 🟢 |
| "Every edit leaves dead triples… they pile up over time" | **Partly wrong.** Only the **first** edit of a record after it was inserted (or after a rebuild) strands anything. From then on the old values are already doubles, the DELETE matches them, and they are removed. The pile is **at most one generation per record** and resets on every ETL rebuild. | S3 and S6 add 0 orphans 🟢 |
| The orphan is the whole damage | **Incomplete.** On **keyed** nodes (URI stable across saves), changing a number leaves the **old decimal attached to the live node beside the new double**. The record then has two values for one field, and no orphan query finds it. Today the only keyed decimal fields are `Sample.top_depth_m` and `bottom_depth_m`. `MineralSite`'s only keyed numeric is `discovered_year`, an integer, which is safe. | S6 🟢; schema read 🟡 |
| Orphans are "subjects of type Element/Analysis/CandidateEntity" | **Wrong for cleanup purposes.** The DELETE removes `rdf:type`, so orphans are **untyped**. Each holds only its numeric triple(s), which matches his own "exactly one triple" observation. `Analysis` carries no numerics and is never orphaned. Site edits also orphan **`Measure`** (grade, ore, cutoff tonnage) and **`BoundingBox`** nodes, which he did not list. | S2/S5 orphan list 🟢 |

---

## 5. Affected code paths

| Handler / writer | Lines | Goes through the bug? | Evidence |
|---|---|---|---|
| `handle_site_add` | `kgsync_listener.py:36–59` | **No.** INSERT DATA from `to_triples()` writes decimals, with no diff and no `norm_literal`. | S1: 0 doubles 🟢 |
| **`handle_site_update`** | 61–82 | **Yes.** | S2 🟢 |
| `handle_same_as_update` | 84–113 | **No.** It only deletes and inserts `owl:sameAs` IRI triples. No literals are involved. | 🟡 |
| `handle_sample_add` | 115–126 | **No.** | S4: doubles unchanged 🟢 |
| **`handle_sample_update`** | 128–149 | **Yes.** It is a copy of the site handler. | S5, S6 🟢 |
| Delete | — | **There is no delete event.** The only types are add, update, and same-as (`event.py:25–33`). Deletion is a soft delete (`is_deleted=True`) sent through PUT/PATCH, so **every delete is a `site:update` / `sample:update` and is affected.** | 🟡 |
| `PATCH /samples/{id}`, `POST /papers/publish` | `services/sample.py:416`, `:420` | Emit `sample:update` (patch) or `sample:add` (new sample), so they are **affected / not affected** accordingly. | 🟡 |
| GeoChem lane | `services/sync/geochem.py:32` | **Same `KGSyncListener` class**, `lane="geochem"`. It is the same code and **affected.** The lane check (`owns`, 33–34) only decides which process runs it. | 🟡 |
| `BackupListener`, `GeoChemBackupListener` | `backup_listener.py`, `geochem_listener.py` | **No.** They write event JSON (from Postgres) to the data repo or JSON-LD and never touch Fuseki. | 🟡 |
| `etl/geochem_loader.save_kg` (JSON-LD reload) | `geochem_loader.py:202–235`, `etl/queries/delete_resources.rq` | **No.** It deletes by **pattern** (`?root (…)* ?s . ?s ?p ?o`), which matches any datatype, then inserts decimals. It would also clear a keyed-node duplicate. It **cannot reach existing orphans**, because nothing links to them. | 🟡 |
| Full ETL rebuild | `etl.yml:24–44` (`kg.loader.fuseki`, `mytdbloader` into a fresh DB) | **No. It resets everything**, including all orphans and doubles. | prod evidence §7 🟢 |

---

## 6. Affected records

### Source or team branching 🟡

There is **no branch on source, team (umn, inferlink, usc, sri), or record type** in the sync path. The only branch is the lane router: `GeoChemRouting.site_paper` (`geochem_routing.py:26–29`) checks `created_by == GEOCHEM_USER_URI` and whether the `source_id` is a registered paper. **Both lanes call the same buggy handler.** Every record that reaches `handle_*_update` is hit regardless of source.

**Who can reach `handle_site_update`** is limited by the API, not by the sync:
- `PUT /mineral-sites/{id}` makes the editing user the owner unless the site is GeoChem (`mineral_site.py:155–158`), and rejects a mismatched id (161–168). **A curator can only update sites they own, plus GeoChem sites.** 🟡
- The editor's **first** save on a dedup group **creates** a curator-owned copy (POST, `site:add`, safe). **The second and later saves by that curator** update it (PUT, `site:update`, buggy). 🟡
- Team data (`/users/s/umn|sri|usc|inferlink|usc-stu`) arrives through the ETL. The batch-upsert route is commented out (`mineral_site.py:124`). **Team records are exposed only if a team service account itself calls PUT**, which I did not find in code and did not check in logs. 🟡 / 🔴
- In prod the exposed site population is the **44 curator-owned sites**: jhammars 33, caknoblock 6, bvu 3, ggraham 1, glederer 1 (`p6-c2-created-by`, `p6-v2-curator-sites`). 🟢 **GeoChem is not loaded in prod** (`gco:grade` count 0, `p6-c3`). 🟢

### Numeric properties an edit can touch 🟡 (schema read) / 🟢 (prod census)

| property | on node | datatype written by add | re-typed by edit? | node URI | in prod today (`p6-n1`) |
|---|---|---|---|---|---|
| `mo:confidence` | `CandidateEntity`: commodity, country, state, CRS, deposit type, units, category, material_form, and GeoChem units | decimal | **yes** | uuid4 → **orphaned** | 3,407,081 decimal, 0 double |
| `mo:value` | `Measure` under `mo:grade`, `mo:ore` (**tonnage**), `mo:cutoff_grade` | decimal | **yes** | uuid4 → **orphaned** | 207,765 decimal, 0 double |
| `mo:x_max/x_min/y_max/y_min` | `BoundingBox` in reference page info | decimal | **yes** | uuid4 → **orphaned** | 0 (not present) |
| `gco:grade`, `gco:detection_limit` | GeoChem `Element` | decimal | **yes** | uuid4 → **orphaned** | 0 (GeoChem not loaded) |
| `gco:top_depth_m`, `gco:bottom_depth_m` | `Sample` | decimal | **yes** | **keyed → old value stays attached** | 0 |
| `mo:discovered_year` | `MineralSite` | integer | no | keyed | 10,933 integer |
| `mo:page` | `PageInfo` | integer | no (integers untouched; deleted correctly) | uuid4 | 40,267 integer |
| **coordinates** | `LocationInfo mo:location` | **WKT `xsd:string`** | **no.** Lat/lon are not numeric literals in the graph; numeric lat/lon exist only in Postgres `location_view`. | — | — |
| `DataSource.score`, `CommodityForm.conversion` | vocabulary entities | decimal | not reachable by the listener | keyed | — |

### Which edits

- **Every update of a record, including text-only edits**, provided the record's subgraph contains at least one decimal on a uuid node. In practice that is every site, since commodity, country, and CRS all carry a `CandidateEntity` confidence. 🟢 (S2, S5 were name-only)
- **Orphans come from the first update after insert or rebuild only.** Later updates re-type nothing new and add no orphans. 🟢 (S3, S6)
- **An attached duplicate appears on any update that changes a keyed decimal** (Sample depths). 🟢 (S6)

---

## 7. Production numbers

Endpoint `https://minmod.isi.edu/sparql`, POST, SELECT/ASK only. Run 2026-10-08T00:46–00:52Z. Every query, raw JSON, and CSV is in `probe-runs/2026-10-07/`.

| question | query file | result |
|---|---|---|
| Reachable | `p6-pf0-ask` | `true`, HTTP 200 🟢 |
| Any `xsd:double` on the 10 edit-reachable numeric predicates | `p6-pf1-double-any` | **0** 🟢 |
| Control: same filter with `xsd:decimal` | `p6-c1-decimal-control` | 5 rows (filter works) 🟢 |
| Literal count by datatype, per property | `p6-n1-datatype-census` | `confidence` 3,407,081 decimal · `value` 207,765 decimal · `page` 40,267 integer · `discovered_year` 10,933 integer · **0 double anywhere** 🟢 |
| Orphans: nodes with a numeric triple but no `rdf:type` | `p6-o1-untyped-numeric` | **0** 🟢 |
| The issue's own Element-orphan SELECT (checked: SELECT only; LIMIT 100 added) | `p6-o2-issue-element-query` | **0**. GeoChem is not loaded: `p6-c3` gives 0 `gco:grade`. 🟢 |
| Reconciliation: typed nodes vs literals | `p6-n2`, `p6-n3` | 3,407,081 typed `CandidateEntity` = 3,407,081 `confidence` triples. 207,765 typed `Measure` with value = 207,765 `value` triples. **No room for a stranded literal.** 🟢 |
| Attribution | `p6-c2-created-by`, `p6-v2-curator-sites` | 679,781 sites. Team: umn 445,957 · sri 227,168 · usc 5,016 · inferlink 1,323 · usc-stu 273. **Curators: 44**, `modified_at` 2025-02-28 → **2026-06-19** (caknoblock, latest) 🟢 |
| When the graph was built | `p6-v1-kg-version` | `mr:kg dcterms:hasVersion 2e6f2e24a0d9…`, `dcterms:created 2026-07-28T21:01:22`. That SHA is **not on GitHub** (`gh api …/commits/2e6f2e24…` → 422), so it is a server-local data-repo commit, consistent with the backup listener. 🟢 |
| Earliest / latest affected record | — | **None affected.** 🟢 |

### Why zero, and how I know it is real

- **The queries can see the bug.** The exact files `p6-pf1`, `p6-o1`, and `p6-o2` were run against the offline repro store, which is known to be affected, and returned 5, 8, and 2 rows (`p6-repro-results.json` → `detection-check-…`). The decimal control returns rows, and the counts reconcile exactly. **Zero means absent, not invisible.** 🟢
- **Why it is absent:** the prod graph is an **ETL rebuild** from a data-repo commit dated **2026-07-28T21:01:22**. The newest `modified_at` of **any** site, of any owner, is **2026-06-19**, before the rebuild. Every API write stamps `modified_at = now` (`public_mineral_site.py:199`), so **no POST or PUT has reached this graph since the rebuild.** Any doubles or orphans made before it were erased by the rebuild. 🟢 (dates) / 🟡 (inference)
- **So the claim "handle_site_update has the same bug in production" is true of the code but not observable in the data today.** The production listener runs the same function (unchanged since Jan 2025, assuming prod is deployed from main 🔴). The next PUT by any of the 44 curators on their own site will strand that site's nested numerics and re-type the rest. 🟢 (code + repro) / 🔴 (deployed version)

Not checked, and important: **whether the prod sync listener is running at all**, and whether Postgres holds edits newer than 2026-07-28 that never reached Fuseki. See §10.

---

## 8. Does it reach Postgres or the website?

**Postgres: no.** 🟢 (grep) / 🟡 (flow)
- The dedup table is recomputed **from Postgres site rows** in the same transaction as the edit (`services/mineral_site.py:313–338`, `DedupMineralSite.from_sites`, `models/kgrel/dedup_mineral_site.py:227`). `services/mineral_site.py` and `models/kgrel/dedup_mineral_site.py` contain **zero** references to `MINMOD_KG`. 🟢
- Across the codebase, Fuseki is read (`MINMOD_KG.query/construct`) only by `api/dependencies.py:75` (KG version id), `api/routers/stats.py`, `api/routers/lod.py:189`, and the listener itself. **No code path loads Fuseki data into Postgres.** The ETL fills Postgres from `ta2-minmod-data` JSON, and the backup listener writes event JSON that came from Postgres. 🟢 (grep)

**Website: no, for the numbers people normally look at.** 🟡
- The dedup API `GET /dedup-mineral-sites[/{id}]` reads Postgres (`services/mineral_site.py:473` `find_dedup_mineral_sites`, SQLAlchemy selects).
- The dashboard's grade/tonnage and site pages call that API (`ta2-minmod-dashboard` `models/ms.py:30`, `models/gt.py:91`). The editor reads the same API.

**Where Fuseki readers could see it once it fires:**
- `stats.py` counts (`/mineral-sites/count`, by-commodity, and so on) always start from a typed node (`?x a mo:…`). Orphans are untyped, so **counts are not inflated.** 🟡
- `lod.py:184–204` resource pages walk out from the record's URI, so **orphans are invisible.** But an edited record shows its numbers as doubles, and an edited Sample would show **two depth values.** 🟡
- **The public SPARQL endpoint and the dashboard's free-form SPARQL page** (`pages/sparqlsearch.py:121`): any query that selects by predicate alone (for example "average `mo:value`" or "all `gco:grade`") **would count orphaned values.** A query that groups or matches by exact term would **split decimal and double.** 🟡

---

## 9. Assessment of the proposed fix (words only)

His fix: (1) use `norm_literal` only for comparison; (2) build the DELETE from the terms read from the store; (3) INSERT the model's own terms as `xsd:decimal`; (4) optionally, stable URIs for nested nodes; (5) clean up orphans.

**What it covers**
- (2) on its own removes the stranding. The DELETE then carries the store's own decimals and matches. This also fixes the **keyed-node duplicate** (Sample depths), which he did not report. ✔ 🟡
- (3) stops the re-typing, so added and edited data share a datatype. ✔ 🟡
- Both must change in **two places**: `handle_site_update` and `handle_sample_update` are copy-pasted twins. A fix to one leaves the other broken. 🟢

**What it would miss or needs adding**
1. **With uuid4 URIs, (1) does almost nothing.** Nested triples never compare equal across saves anyway, because their subjects differ. So every save still deletes and rewrites the whole nested tree, and LOD links to nested nodes still break on every save. Normalised comparison only matters on keyed nodes. (4), stable URIs, is what makes the diff meaningful. It is optional for correctness but not for churn. 🟡
2. **A simpler alternative worth weighing:** delete by **pattern** from the record root, exactly as `etl/queries/delete_resources.rq` already does for GeoChem reloads, then insert. That is datatype-agnostic, needs no read-back of terms, and is already in the codebase. The cost is a full rewrite of the record on every save, which is what happens today anyway. 🟡
3. **The "INSERT as `xsd:decimal`" path renders some floats illegally.** Both `to_triples` (`MyLiteral`) and `to_graph` (`rdflib.Literal`) write Python floats with an exponent as `"1e-05"^^xsd:decimal`, which is not a valid decimal lexical form (run in the venv 🟢). **Prod already holds 6 such literals** (`mo:value` = `5e-05`, `7e-05`, `8.9e-05`, `3e-05` on umn and inferlink grade Measures; `p6-x1`, `p6-x2`) 🟢. They come from ETL, not from this bug. A fix that routes edits through the same serializer will keep producing them, and a "read terms back from the store" DELETE should be tested against them for an exact round-trip. 🔴 (round-trip not tested)
4. **His cleanup criterion would match nothing.** "Subjects of type Element/Analysis/CandidateEntity that nothing points to" fails because the DELETE already removed their `rdf:type`. It also misses **`Measure` and `BoundingBox`** orphans (site edits) and **attached duplicates** on keyed nodes. 🟢 (repro)
5. **Tests did not catch it** because `tests/services/sync/test_kgsync_listener.py` rebuilds the site with `from_graph`, which walks only reachable nodes and compares Python values. It never looks at orphans or datatypes. A regression check needs a datatype census and an untyped-subject count after an update. 🟡 (read; suite not run)

**What a cleanup of existing orphans would have to touch**
- **Untyped subjects** in `mr:` / `gcr:` whose only triples are the edit-reachable numeric predicates, with **no inbound link**. Do not filter on type.
- **Keyed nodes with more than one value** for a single-valued numeric field (Sample depths). Keep the value that matches Postgres.
- **Live doubles** on reachable nodes, re-typed back to decimal.
- **In production there is nothing to clean today** (§7). On dev, his counts (13 Element, 24 CandidateEntity, 73 doubles) are the expected scope. 🔴 (dev not queried)

**How to do it safely**
- **Cheapest and safest option: a full ETL rebuild after the code fix is deployed.** That is how prod got clean, and it touches no individual triple. 🟢 (evidence) / 🟡 (recommendation)
- If triple-level cleanup is needed (dev), do it in this order:
  1. Stop the sync listener.
  2. Back up the TDB2 dataset (`tdb2.tdbbackup`).
  3. Run the SELECTs (`p6-o1`, plus a duplicate-value query) and **export the exact triples** to a file.
  4. Review the counts against expectations.
  5. Delete with **`DELETE DATA` built from that exported file**, not a pattern.
  6. Re-run the same SELECTs (expect 0) and the typed-node reconciliation (`p6-n2`/`p6-n3`, expect unchanged typed counts).
  7. Restart the listener.
- Do dev first.

---

## 10. What I did NOT verify, and what would be needed

| not verified | why | what would verify it |
|---|---|---|
| **Dev numbers** (~1.5M decimal, 73 doubles, 13 orphan Elements, 24 orphan CandidateEntities) 🔴 | My authorised endpoint was prod only. I did not query dev. | Run `p6-n1`, `p6-o1`, and `p6-o2` (read-only) against the dev SPARQL endpoint, with permission. The mechanism predicts orphan Elements and CandidateEntities but **no orphan Analysis**, and every orphan **untyped**. |
| **Whether the prod sync listener is running**, and whether Postgres has edits after 2026-07-28 that never reached Fuseki 🔴 | It needs server or DB access, and no read-only API exposes edit history. | Read-only SQL on prod Postgres: `SELECT type, count(*) FROM event_log WHERE NOT kg_synced GROUP BY type`, plus `max(modified_at)` on `mineral_site`. |
| **Which code is deployed in prod** 🔴 | Not exposed. I assumed main, which is safe here because the handler has been unchanged since 17 Jan 2025. | Image tag or commit on the server. |
| **Real Fuseki HTTP server behaviour** 🟡 | I ran the same Jena 5.2.0 TDB2 engine through the CLI, not through Fuseki's HTTP layer. The update text is identical, since `FusekiDB` only adds the PREFIX block. | Same run against a throwaway Fuseki container once Docker is available. |
| **Round-trip of illegal `"5e-05"^^xsd:decimal` literals** through CONSTRUCT → rdflib → `.n3()` 🔴 | Not tested. It only matters for the "DELETE from store terms" fix. | Add one such literal to the repro store and run `handle_site_update`. |
| **Team service accounts calling PUT** 🔴 | Code allows it for owned sites; logs not checked. | API access logs for PUT `/mineral-sites/*` by `/users/s/*`. |
| **Repo test suite** 🔴 | Not run (needs Postgres + Fuseki fixtures). | `pytest tests/services/sync` in a dev environment. |
| **Editor hops 1–2** 🟡 | Read from the editor source; I did not drive the UI. Per the brief, the editor was not used. | — |

Read-only throughout: SELECT/ASK only, POST to the public endpoint, no editor or API write, sync listener never run against a real store, no repository modified, TLS verification never disabled.
