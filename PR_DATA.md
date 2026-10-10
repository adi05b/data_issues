# State table: alt names, Niamey and Zacapa

Branch `adi05b/ta2-minmod-data` `add-niamey-ekaterinburg` @ `250abc7` (4 commits on `3a086a5`). Only `data/entities/state_or_province.csv` changes.

**Merge this before the `ta2-minmod-kg` state-repair PR.** The kg merge cache is keyed on the site files and the same-as file, not the entity files. A table change that lands after the kg build has run would not be picked up.

## What changes

- **A new `alt names` column**, added last.
  - It holds other names that sources use for a state, pipe-separated where there is more than one, like `country.csv`'s.
  - It is filled on 50 rows with 53 names, for example Orissa → Odisha, Niedersachsen → Lower Saxony and Buryatiya → Republic of Buryatia.
  - **The kg repair uses an alias only after the real name, the name without administrative words and the state code have all found nothing.** An alias can turn a dropped state into a repointed one, but it never changes a match the table already makes.
- **Ekaterinburg is an alt name of Sverdlovsk (`Q5481`),** not a row of its own. Ekaterinburg is a city in Sverdlovsk Oblast.
- **Two new rows:**
  - **`Q7085` Niamey** (Niger, code `8`).
  - **`Q7086` Zacapa Department** (Guatemala, code `ZA`). The table had 21 of Guatemala's 22 departments. The name and code follow the other 21 rows.
- **The file format is kept:** CRLF line endings, and no newline at the end of the file.
  - Every line is its old bytes plus `,` and the value, so git shows every line as changed. A new column cannot avoid that.
  - No existing value changes.
  - The positional extractor (`extractors/state_or_province.yml`) still reads the country from column 5.

## Effect (with the kg PR, all records)

| | candidates |
|---|--:|
| states that resolve to nothing, before | 737 |
| states that resolve to nothing, after | 340 |
| ↳ recovered through the approved aliases | 366 |
| ↳ recovered through Ekaterinburg on Sverdlovsk | 19 |
| ↳ recovered through the new Zacapa row | 7 |
| ↳ recovered through the new Niamey row | 5 |

- **No regressions:** every candidate that was kept before is still kept, and every one that was repointed before goes to the same state.
- **Each of the 5,086 states, given its own name and country, resolves to itself or to nothing.** It never resolves to another state, and each of the 53 alt names resolves to its own row.
