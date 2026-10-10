# MinMod data quality — what I found

*Aditi Bombe · 2 September 2026 · for Craig Knoblock, Amandeep Singh, Adriana Trejo-Sheu*

This is a standalone summary of an investigation into three data quality problems in the MinMod knowledge graph. It assumes no prior reading. Supporting detail is in `PROBE_REPORT.md` (findings and evidence), `DATA_SHAPE.md` (how the data is actually structured), and `OPEN_QUESTIONS.md` (what is still unresolved).

A note on terminology, used throughout: MinMod stores **679,781 individual records** collected from 48 sources. Because several sources often describe the same real mine, those records are merged down into **419,099 "deduplicated" entities** — the things the user interface shows. Adriana's problem counts are on the merged entities; my queries run against the individual records, which live in a different database. Individual-record counts should therefore come out **higher** than hers, and where they don't, that is itself a finding.

---

## 1. What I set out to investigate

Adriana flagged three problems on 26 August.

**Problem 1 — impossible latitudes.** 24,818 merged entities (6.2% of those with coordinates) have a latitude outside the range −90 to +90, which is geographically impossible. Her read was that most of these look like the latitude and longitude having been written in the wrong order, and she asked for them to be corrected, with the corrected point landing inside the country and state the record claims to be in.

**Problem 2 — a state in the wrong country.** 5,858 merged entities where the record's state disagrees with its country. Her example: a record observed as "Florida, United States" was matched to a place called Florida that the system believes is in **Puerto Rico**, while the record's own country is the United States. She asked for a review of the disagreement list.

**Problem 3 — coordinates that are too coarse.** 3,633 entities give coordinates to only one decimal place, 232 to none at all, and 29 sit at exactly (0, 0) — a point in the Gulf of Guinea used as a placeholder when a real location is missing. A further 93,673 give latitude and longitude to *different* precision. She asked only for a list of which data sources this comes from, so extraction could be changed if worthwhile. She would handle the error calculations herself.

---

## 2. How I investigated it

The work happened in five stages, and the third is the one worth describing.

**First, I read the structure.** Before writing any query I read MinMod's schema and its reference lists of countries, states and coordinate systems, and reconstructed how a record is laid out — where the name lives, where the coordinates live, how a state name gets matched to a known place.

**Second, I wrote queries** against that reconstruction — nine of them, one or more per problem, designed to measure each problem directly.

**Third — and this is the step that mattered — I checked the reconstruction against the live system before trusting a single query result.** Ten short "pre-flight" queries asked the database to describe itself: what fields actually exist on a record, what the coordinate text actually looks like, whether the arithmetic functions I depend on behave as expected.

That step took about ninety seconds and it changed the conclusion of the whole exercise. It found that **two of my nine queries were quietly wrong**:

- One asked for a field called `name`. **That field does not exist** — the name is stored under a different label. The database did not report an error. It returned a perfectly well-formed, entirely empty answer. Had I not checked, I would have reported "no matching records found" as a result.
- Another counted decimal places without accounting for the fact that some records are not stored in latitude and longitude at all. It confidently ranked the *most* precise source in the database as the *least* precise one.

This is the general hazard: a query against a field that does not exist, or against data whose units you have assumed, does not fail. It succeeds and returns something plausible. **The only defence is to ask the database to describe itself before you ask it to count anything**, and that is worth building into how this kind of work is done here.

**Fourth, I ran the corrected queries** — 70 in total across two sessions, all read-only. Nothing was written to the graph, and no data files were modified.

**Fifth, I verified the arithmetic offline.** The central claim about Problem 1 depended on coordinates being in a different measurement system than assumed. Rather than argue that from circumstantial evidence, I installed a standard geographic conversion library and converted the actual stored numbers to see where they land on a map.

---

## 3. What I found

### Problem 1 is not the problem it was reported as

There are **31,109 individual records** with an out-of-range latitude. Splitting them by the coordinate system each record declares:

| Coordinate system | Records | What it is |
|---|---|---|
| Oregon GIC Lambert (feet) | 23,316 | a flat-map grid for Oregon, measured in **feet** |
| UTM zone 12N (metres) | 7,792 | a flat-map grid for Utah, measured in **metres** |
| WGS 84 (ordinary latitude/longitude) | **1** | degrees |

**31,108 of the 31,109 records are not errors.** They are correct coordinates measured on a flat-map grid rather than in degrees. A number like 4,199,554 is a distance in metres, not a latitude. They fail an "is latitude between −90 and +90" test for the same reason a temperature in Kelvin fails a "is this between −50 and 50" test — the check is being applied to the wrong units.

Every one of these records **states which system it is in**, in a field that is filled in on 99.7% of the database. The check that flagged them did not read that field.

I verified this rather than assuming it. Taking the extreme records from each source — the northernmost, southernmost, easternmost and westernmost — and converting them from their declared system into ordinary latitude and longitude, **89 of 90 land inside the state the record names**. The single exception lands 123 metres outside Utah, on the Utah–Arizona border, which is a limitation of testing against a rectangle rather than the state's real outline.

**The clearest case is Adriana's own headline example.** "Harts Draw Deposits" exists as three separate records. Two are ordinary latitude/longitude and are already correct. The third stores `632887 4199554` in the Utah metre grid. Converted properly, it lands **6.4 metres and 7.3 metres** from the other two — the same mine, correctly recorded, in different units.

**Exactly one record in the entire database is a genuine transposed coordinate**: a site called Tagaung Taung in Myanmar, stored as longitude 23.6, latitude 96.2, which should be longitude 96.2, latitude 23.6. Five other records for the same place independently confirm the corrected position.

So: **the brief said most of these look like transposed coordinates. One does.** Had a correction script been written to the original brief, it would have swapped the coordinates of 31,108 correct records and destroyed two entire source datasets.

### Problem 2 is real, and it has one mechanical cause

I reproduced Adriana's figures at record level: **6,156 records** with a state/country disagreement against her 5,858 merged entities, and her individual examples line up (Florida/Puerto Rico: 1,609 records against her 1,587).

The cause is a name-matching failure with two ingredients. The reference list of world states stores full official names — `La Paz Department`, `Potosí Department`, `Camagüey Province` — while the data sources write the short form: `La Paz`, `Potosi`, `Camaguey`. The matcher, comparing text, scored `La Pampa` in Argentina above `La Paz Department` in Bolivia, and `Porto` in Portugal above `Potosí Department`. Accented characters make it worse. And the matcher was **not restricted to the country the record already says it is in**, so a Bolivian record was free to match an Argentine state.

I tested the obvious fix offline: strip the trailing word (`Department`, `Province`, `Parish`, `Region`…), ignore accents, and require the answer to be in the record's own country. Against the real reference list of 5,084 states, that resolves **5,145 of 6,134 disagreements — 83.9% — to the correct place**, including every one of Adriana's examples that has a correct answer:

```
Florida      + United States  ->  Florida, United States
La Paz       + Bolivia        ->  La Paz Department
Potosi       + Bolivia        ->  Potosí Department
Bolivar      + Venezuela      ->  Bolívar, Venezuela
Camaguey     + Cuba           ->  Camagüey Province
Saint Andrew + Jamaica        ->  Saint Andrew, Jamaica
```

Only 15 records out of 6,134 come out ambiguous.

I also found **a second population nobody has counted**: 3,245 records whose state name failed to match anything at all. These never appear in the disagreement list, because a disagreement requires both sides to have matched something. It is the same root cause with a quieter symptom — `Camagüey`, for instance, appears in *both*: 158 records matched wrongly, and another 216 that failed to match at all. The same fix recovers 1,090 of those.

**One change fixes 6,235 records across both populations.**

What it does not fix, about 3,100 records, are places the reference list simply does not contain: `Orissa` (renamed Odisha in 2011), `Katanga` (split into four provinces in 2015), `Newfoundland`, `Greenland`, and — revealingly — `CO`, a bare two-letter abbreviation appearing 51 times where a state name was expected. Those need entries added to the reference list, not better matching.

### Problem 3 cannot be answered as posed

Two things get in the way.

**The counting does not reconcile.** Counting one-decimal-place latitudes across individual records gives **2,853** against Adriana's 3,633 merged entities. Individual records should always outnumber merged ones, so a smaller number means we are not counting the same thing. The same happens with mismatched precision: 33,950 individual records against her 93,673. Something differs in the definition, and I do not know what.

**More fundamentally, the stored decimal places are not real precision.** Coordinates pass through the system as binary floating-point numbers and are written back out at whatever length reproduces the number exactly. One MRDS record stores `-109.4878899999999931` — sixteen decimal places for a value the source publishes with five. In the other direction, a value of `63.330` comes back as `63.33`, losing a digit that was never measured differently.

So counting decimal places measures **the number format, not the accuracy of the measurement**. Most of the 93,673 "mismatched precision" records are that artefact rather than two coordinates from two different origins. There is also no field anywhere in the schema recording how precise a coordinate is.

**One part of Problem 3 is clean and closeable.** All 34 records at (0, 0) come from a **single extraction pipeline**, and 29 of them carry a real observed country — Madagascar, Canada, Spain, Zimbabwe, Kazakhstan and more. A point at (0, 0) with a country of "Madagascar" attached is plainly a missing value with a placeholder in it, not a location.

### What was wrong in our own planning documents

Worth recording, because the pattern matters more than the individual errors. Our working notes described the data structure from reading the schema files and reference spreadsheets rather than from querying the live system. Checking them:

- The field holding a record's name **does not exist** under the name we used.
- The coordinate text is stored as **plain text**, not the geographic type we assumed.
- The identifier we had for the United States was **wrong**.
- The coordinate-system field was described as rarely filled in. It is filled in on **99.7%** of records, and it is the single most important field in Problem 1.
- Our list of coordinate systems included one that appears **zero** times in the data, and **omitted** the one carrying the largest block of flagged records.
- We expected records to carry several competing country and state candidates, so that naive counting would inflate results. In practice **essentially every record carries exactly one** — 33 records out of 451,527 have more.

Five of the six were caught only by asking the live system. **The reference spreadsheets are not a reliable mirror of what is deployed.**

---

## 4. What it means

**Problem 1 is a misdiagnosis, and the underlying defect is in the validation, not the data.** 31,108 records are correctly stored, correctly labelled, internally consistent, and were flagged by a check that ignored the field telling it what units it was looking at. The remedy is not 31,108 corrections. It is one validation rule that reads the coordinate system before judging the coordinate. There is a genuine issue underneath — any part of the system that reads a coordinate without reading its coordinate system will place these records in the wrong hemisphere — but that is a question about how coordinates are consumed, not about repairing bad data.

The one real transposed coordinate is worth fixing on its own merits. It is also the whole of the visible problem: **any transposition where both numbers happen to fall between −90 and 90 stays inside the valid range and is invisible to this kind of check.** With the visible population now known to be a single record, that invisible population is the entire remaining risk, and finding it needs a different technique — testing whether each point actually falls inside the country the record claims.

**Problem 2 is a genuine defect with a single mechanical cause and a quantified fix.** It is not thousands of individual judgement calls. It is one matching rule that compares names without normalising them and without using the country it already knows. Correcting the 5,858 rows without correcting the matcher would leave the rows to be regenerated the next time the data is rebuilt. The disagreement count also **understates the problem by about half**, because names that failed to match at all never enter it.

**Problem 3, as posed, is asking for a number the system cannot produce.** Adriana wants to know coordinate precision so she can propagate error when comparing two records. But precision is not recorded anywhere, and the decimal places that look like precision are an artefact of numeric storage. Giving her a source list built on decimal counting would hand her a number that does not mean what she needs it to mean. The real finding is that **the quantity she needs does not exist yet** and would have to be captured at extraction time. The (0, 0) records are a separate, straightforward bug in one extraction pipeline.

**Across all three, one theme.** Every one of these problems is a validation or normalisation step that ran without the context sitting right next to it — a range check that ignored the units field, a name matcher that ignored the country field, a precision measure applied to a number format rather than a measurement. None is really a data-entry problem.

---

## 5. What could be done about it

Options rather than recommendations, since the decisions belong to Craig and Adriana.

### Problem 1

| Option | Cost | Fixes | Leaves |
|---|---|---|---|
| **A. Make the validation rule aware of coordinate systems** — only apply the −90/+90 check to records actually in degrees | Very low — a rule change, no data touched | Removes 31,108 false alarms permanently | Consumers that read coordinates without reading units still misplace these records |
| **B. Convert everything to standard latitude/longitude when data is loaded**, keeping the original and its system for provenance | Moderate — an ingest change affecting two whole source datasets; the conversion itself is verified working to within 7 metres | Every consumer gets usable coordinates without needing to know about grids | A conversion step to maintain; original values must be preserved |
| **C. Do both** | A now, B when there is appetite | — | — |
| **D. Fix the one genuine transposition by hand** | Trivial, one record | The entire visible transposition problem | — |
| **E. Add an automated data quality rule bounding latitude** | Low | Stops the class recurring | **Must be conditional on the coordinate system** — an unconditional rule would reject two valid sources |
| **F. Test whether each point falls inside its stated country** | Higher — needs country outlines and a script | The invisible transpositions, which are now the only remaining risk | — |

**Blocked on:** Craig, for B and F. A, D and E can proceed on their own.

### Problem 2

| Option | Cost | Fixes | Leaves |
|---|---|---|---|
| **A. Correct the 5,858 rows directly** | Moderate, mostly mechanical | The current symptom | Regenerates on the next rebuild; ignores the 3,245 never-matched records |
| **B. Fix the matcher** — ignore accents, strip trailing `Department`/`Province`/`Parish`, and restrict candidates to the record's own country | Low to moderate, one component | **83.9% of disagreements and 33.6% of never-matched names — 6,235 records** — and stops recurrence | ~3,100 records where the reference list has no correct entry |
| **C. Add a review gate on low-confidence matches** | Very low | Flags 58.7% of disagreements in a queue of 10,732 — about 23× better than random | Misses the largest single group (2,058 Florida records) which the matcher reported at 99.99% confidence |
| **D. Add missing entries and aliases to the reference list** — Orissa→Odisha, Katanga's four successors, Newfoundland, Greenland | Low, a data edit | The ~3,100 records no matcher can resolve | Needs an owner |
| **E. Investigate `CO` appearing as a state name 51 times** | Very low | Possibly an extractor writing codes into a name field | — |

**Blocked on:** whether the matching pipeline is in scope to change — Craig and Amandeep. C, D and E are independent of that.

### Problem 3

| Option | Cost | Fixes | Leaves |
|---|---|---|---|
| **A. Clear the coordinates on the 34 (0, 0) records, keep the records and their countries** | Very low | A clearly wrong value pretending to be a location | The pipeline will produce more |
| **B. Fix the null handling in the one extraction pipeline producing them** | Low, one component | The cause | — |
| **C. Ask Adriana exactly what she counted** | An email | Whether there is a reconcilable number at all | — |
| **D. Publish the source list, corrected for coordinate systems** | Low | Answers the question as asked | The number still reflects storage format, not measurement accuracy |
| **E. Add a precision field to the schema, populated at extraction** | High — a schema change plus extractor work | Gives Adriana the quantity she actually needs | Only helps data loaded after the change |

**Blocked on:** Adriana, for C. Craig, for E. A and B can proceed.

### Sequencing, if it helps

The cheap, unblocked, high-certainty items are: the coordinate-system-aware validation rule, the single transposition fix, clearing the (0, 0) records, and the low-confidence review gate. The matcher fix is the highest value single change in the whole investigation — 6,235 records — and needs only a decision that the component is in scope.

---

## What remains unknown

**How the merged entities are built.** If the merge *recalculates* a coordinate by averaging the records it combines, rather than picking one, that would explain both of Problem 3's impossible-looking counts at once — and would mean Adriana's precision figures describe the merge, not any data source. This is one file to read, and it should be read before asking her anything.

**Whether the coarse coordinates were always coarse.** Whether a one-decimal-place coordinate came in that way or was rounded somewhere in our own processing decides whether Problem 3 is "record what the source gave us" or "fix a bug". I could not check — it needs the data repository, which is not on this machine. The floating-point finding makes "our own processing" the more likely answer, but that is inference.

**What creates the record-linking in the graph.** 72% of the links marked "same as" turn out to be one source record processed by two different teams, rather than two sources describing one mine. Until someone confirms what writes that field, any argument about deduplication quality — including my own — rests on an assumption.

**How many transposed coordinates are still hidden.** Every one where both numbers fall inside the valid range is undetectable by any check of this kind. That population is now the entire genuine risk in Problem 1 and its size is completely unknown.
