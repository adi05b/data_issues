# DR Congo ADM1 in the other geoBoundaries editions

*Aditi Bombe · 2026-10-09 · read-only. Only the public geoBoundaries API and GitHub were used. No repository was edited.*

The API responses, the downloaded file, the script and its outputs are in `gb_editions/`.

## 1. Metadata

| | **gbHumanitarian / COD / ADM1** | **gbAuthoritative / COD / ADM1** | gbOpen / COD / ADM1 (for reference) |
|---|---|---|---|
| API response | HTTP 200 | **HTTP 404** | HTTP 200 |
| boundaryLicense | **Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)** | — | Open Data Commons Open Database License 1.0 |
| boundarySource | Referenciel Géographique Commun, HDX | — | OpenStreetMap, Wambacher |
| licenseDetail | empty (`nan`) | — | empty (`nan`) |
| licenseSource | data.humdata.org/dataset/cod-ab-cod | — | |
| year represented / build | 2019 / Dec 12, 2023 (commit `9469f09`) | — | |
| shapes | 26 | — | 26 |

**gbAuthoritative has no DR Congo entry at all.**
- Its ALL listing exists and covers 32 countries, none of which is DR Congo.
- `COD/ADM0/` and `COD/ALL/` also return 404.

**gbHumanitarian has 26 shapes, the post-2015 provinces.** Their `shapeISO` is empty.
- Bas-Uele, Equateur, **Haut-Katanga**, **Haut-Lomami**, Haut-Uele, Ituri
- Kasaï, Kasaï-Central, Kasaï-Oriental, Kinshasa, Kongo-Central, Kwango, Kwilu
- Lomami, **Lualaba**, Maniema, Maï-Ndombe, Mongala, Nord-Kivu, Nord-Ubangi
- Sankuru, Sud-Kivu, Sud-Ubangi, **Tanganyika**, Tshopo, Tshuapa

**gbHumanitarian has all four successors, under CC BY**, which is attribution-only, not share-alike. The four map by name to MinMod: Haut-Katanga Q3000, Lualaba Q3012, Haut-Lomami Q3001, Tanganyika Q3021. So the rerun below was done.

**Caveat:** I read the licence from the geoBoundaries API metadata only. I did not check the HDX source page (`licenseSource`), and I make no judgement about what CC BY 3.0 IGO's attribution terms require of MinMod.

## 2. Katanga points: gbHumanitarian against gbOpen, both full resolution

The points and usability rules are the same as `katanga_points_fullres.csv`. The gbHumanitarian file has 70,328 vertices; gbOpen's has 194,049.

| | Haut-Katanga | Lualaba | Tanganyika | Haut-Lomami | outside DR Congo | no location | placeholder |
|---|--:|--:|--:|--:|--:|--:|--:|
| 111 drop-list: gbOpen | 50 | 43 | 4 | 1 | 4 | 8 | 1 |
| 111 drop-list: **gbHumanitarian** | **51** | **42** | 4 | 1 | 4 | 8 | 1 |
| 148 never normalized: gbOpen | 77 | 71 | | | | | |
| 148 never normalized: **gbHumanitarian** | 77 | 71 | | | | | |
| 2 already Haut-Katanga: both | | 1 | | | | 1 | |

**7 of the 247 in-province points disagree.** All 7 sit near the Haut-Katanga/Lualaba boundary. Distances are from the point to the boundary of the province it falls in, in each source.

| group | record id | location | gbOpen | gbHumanitarian | km to boundary (gbOpen / gbHum.) |
|---|---|---|---|---|---|
| drop list | cdr `02c41f98…0129` | 26.0917, −10.9542 | Haut-Katanga | Lualaba | 0.88 / 1.24 |
| drop list | mrds `10400590` | 25.9324, −10.9712 | Lualaba | Haut-Katanga | 0.45 / 0.65 |
| drop list | mrds `10400593` | 26.5743, −10.8110 | Lualaba | Haut-Katanga | 0.58 / 1.27 |
| never normalized | sir20105090z `10244` | 25.9324, −10.9712 | Lualaba | Haut-Katanga | 0.45 / 0.65 |
| never normalized | sir20105090z `10234` | 26.0022, −10.9555 | Haut-Katanga | Lualaba | 2.09 / 1.11 |
| never normalized | sir20105090z `10265` | 26.5029, −10.8769 | Haut-Katanga | Lualaba | 1.71 / 2.04 |
| never normalized | sir20105090z `10276` | 26.2508, −11.0782 | Lualaba | Haut-Katanga | 0.14 / 7.28 |

- **Drop list:** the net change is one record from Lualaba to Haut-Katanga (2 one way, 1 the other).
- **The 148:** 2 move each way, so the totals are unchanged.
- **Every disagreement is within 2.1 km of the boundary in at least one source.**
- **The two editions draw the boundary differently.** At `10276` the gap between them is at least 7 km.
- **No point is near a Tanganyika or Haut-Lomami boundary in a way that changes its result.**

**The 4 sign-flip points are still outside DR Congo** in gbHumanitarian, 588–4,293 km away, the same 4 as in gbOpen.

## 3. Verdict

**gbHumanitarian has the four successors under CC BY 3.0 IGO (not share-alike), so it can replace gbOpen for Katanga.**
- It gives the same province for 240 of the 247 in-province points, and the same 4 out-of-country points.
- The 7 records near the Haut-Katanga/Lualaba boundary get a different province, and neither source can be called right for them from these numbers alone.

**Files (`gb_editions/`):**
- `api_gbHumanitarian_COD_ADM1.json`
- `api_gbAuthoritative_COD_ADM1.json` (the 404 page)
- `api_gbAuthoritative_ALL_ADM1_.json` and the other probes
- `gbHumanitarian_COD_ADM1.geojson`
- `katanga_gbhumanitarian.py`
- `katanga_points_gbhumanitarian.csv`
- `katanga_gbhumanitarian_results.json`
