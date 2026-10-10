# Katanga with Natural Earth

*Aditi Bombe · 2026-10-09 · read-only. Nothing was queried live, and no repository was edited.*

## 1. Version and licence

- **Natural Earth 1:10m Admin 1 – States, Provinces** (`ne_10m_admin_1_states_provinces.geojson`), from `nvkelso/natural-earth-vector`.
- **Version 5.1.2.** That is the release tag `v5.1.2`, commit `f1890d9`, released 2022-05-13, and `VERSION` reads `5.1.2`.
- **The file on `master` is byte-identical.** Both have SHA-256 `22d0e3ad…2fb5`. Master's `VERSION` says `5.2.0-pre`, an unreleased label, so I used the tag.
- **The licence (`LICENSE.md`, the same text in both) states:** "Everything here is public domain. … All versions of Natural Earth raster + vector map data found on this website are in the public domain. You may use the maps in any manner, including modifying the content and design, electronic dissemination, and offset printing. … No permission is needed to use Natural Earth. Crediting the authors is unnecessary."

The source files are in `src/v5.1.2/`.

## 2. Does it have the four successors? **No.**

Natural Earth has **11 DR Congo features. These are the pre-2015 provinces**, plus Kinshasa:

| name | iso_3166_2 | type_en | name_alt |
|---|---|---|---|
| Bandundu | CD-BN | Province | |
| Bas-Congo | CD-BC | Province | Bas-Zaire, Bas-Zaïre, Kongo-Central, Lower Zaire |
| Équateur | CD-EQ | Province | Equator, Equatorial |
| Kasaï-Occidental | CD-KW | Province | Kasai West, West Kasai, West Kassai |
| Kasaï-Oriental | CD-KE | Province | East Kasai, Kasai East |
| **Katanga** | **CD-KA** | Province | Shaba |
| Kinshasa City | CD-KN | Neutral City | Kinshasa, Léopoldville |
| Maniema | CD-MA | Province | |
| Nord-Kivu | CD-NK | Province | |
| Orientale | CD-OR | Province | Haut-Zaire, Haut-Zaïre, Upper Zaire |
| Sud-Kivu | CD-SK | Province | Sud-Kivou, Sud Kivou, Sud Kivu |

- **There is one Katanga feature**, the old province (`CD-KA`).
- **None of the four successors exists.** Haut-Katanga (Q3000), Lualaba (Q3012), Haut-Lomami (Q3001) and Tanganyika (Q3021) do not appear in the file under any country, in `name`, `name_en` or `name_alt`.
- The Q-ids are confirmed in `state_or_province.csv`.

**Under the stop rule, Steps 3 and 4 were not run.** There is no Natural Earth agreement count and no polygon size, and `katanga_successors.geojson` was not written.

## 3. Verdict

**Natural Earth cannot replace geoBoundaries for Katanga.** It has only the single pre-2015 Katanga polygon, so it cannot tell Haut-Katanga, Lualaba, Haut-Lomami and Tanganyika apart.

Files:
- `ne_katanga_check.py`, the script.
- `ne_katanga_check.txt`, its output.
- `ne_cod_features.csv`, the feature list.
- `src/v5.1.2/`, the source files and commit.
