#!/usr/bin/env python3
"""Problem 2, Solution C: how well does geoBoundaries gbOpen ADM1 match MinMod's
state table? Read-only: downloads public files, reads local CSV/JSON, writes
only into this folder.

    python boundary_match.py <ta2-minmod-data data dir for Katanga records>

Needs shapely. Inputs:
  ta2-minmod-data/data/entities/{state_or_province,country}.csv   (fork branch add-niamey-ekaterinburg)
  geoboundaries/api_ALL_ADM1.json + one simplified GeoJSON per country (downloaded if missing)
"""

from __future__ import annotations

import collections
import csv
import glob
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

from shapely import wkt
from shapely.geometry import MultiPoint, Point, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ENT = HERE / "ta2-minmod-data/data/entities"
GB = HERE / "geoboundaries"
API = "https://www.geoboundaries.org/api/current/gbOpen/ALL/ADM1/"
SITES = Path(sys.argv[1]) / "mineral-sites" if len(sys.argv) > 1 else None

# words that name the admin level rather than the place
ADMIN_WORDS = {
    "province", "provincia", "provincie", "provinsi", "region", "regional", "regione", "region",
    "department", "departement", "departamento", "state", "estado", "oblast", "oblysy", "krai", "kray",
    "governorate", "muhafazah", "prefecture", "county", "district", "canton", "municipality",
    "municipio", "autonomous", "republic", "territory", "voivodeship", "parish", "division",
    "emirate", "wilayat", "wilaya", "city", "special", "administrative", "capital", "metropolitan",
    "okrug", "raion", "rayon", "governorship", "zone", "area", "of", "the", "and", "de", "del", "do", "da",
}


def demojibake(s: str) -> str:
    """Some geoBoundaries names are UTF-8 bytes read as Latin-1 ('RegiÃ³n'); undo that when it round-trips."""
    try:
        fixed = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
    return fixed


def fold(s: str) -> str:
    s = demojibake(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(w for w in s.split() if w not in ADMIN_WORDS)


def fetch(url: str, dest: Path) -> None:
    if not dest.exists():
        with urllib.request.urlopen(url, timeout=120) as r:  # default TLS verification
            dest.write_bytes(r.read())


def load_states():
    with open(ENT / "state_or_province.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_shapes():
    GB.mkdir(exist_ok=True)
    fetch(API, GB / "api_ALL_ADM1.json")
    meta = json.load(open(GB / "api_ALL_ADM1.json", encoding="utf-8"))
    shapes = {}
    for m in meta:
        iso3 = m["boundaryISO"]
        dest = GB / f"{iso3}_ADM1_simplified.geojson"
        fetch(m["simplifiedGeometryGeoJSON"], dest)
        shapes[iso3] = json.load(open(dest, encoding="utf-8"))["features"]
    return meta, shapes


def match(states, iso2to3, shapes):
    out = []
    for s in states:
        iso3 = iso2to3.get(s["country_code"])
        feats = shapes.get(iso3, [])
        row = {"minmod_id": s["minmod_id"], "country_code": s["country_code"], "name": s["name"],
               "match_tier": "", "shapeISO": "", "shapeName": "", "_cands": []}
        if not feats:
            row["match_tier"] = "no gbOpen ADM1 for country"
            out.append(row)
            continue
        code = f'{s["country_code"]}-{s["state_code"]}'.upper()
        alts = [a.strip() for a in re.split(r"[;|]", s["alt names"]) if a.strip()]
        tiers = [
            ("iso", lambda f: s["state_code"] and (f["properties"].get("shapeISO") or "").upper() == code),
            ("name", lambda f: fold(s["name"]) and fold(f["properties"]["shapeName"]) == fold(s["name"])),
            ("alt name", lambda f: any(fold(a) and fold(a) == fold(f["properties"]["shapeName"]) for a in alts)),
        ]
        for tier, test in tiers:
            hits = [f for f in feats if test(f)]
            if hits:
                row["match_tier"] = tier if len(hits) == 1 else f"ambiguous ({tier}: {len(hits)} shapes)"
                row["_cands"] = hits
                row["shapeISO"] = " | ".join(h["properties"].get("shapeISO") or "" for h in hits)
                row["shapeName"] = " | ".join(h["properties"]["shapeName"] for h in hits)
                break
        else:
            row["match_tier"] = "unmatched"
        out.append(row)
    # two MinMod states on one shape -> both ambiguous, none picked
    by_shape = collections.defaultdict(list)
    for r in out:
        if len(r["_cands"]) == 1:
            by_shape[(r["country_code"], r["_cands"][0]["properties"]["shapeID"])].append(r)
    for rows in by_shape.values():
        if len(rows) > 1:
            for r in rows:
                r["match_tier"] = f"ambiguous (shape shared by {len(rows)} states; was {r['match_tier']})"
    return out


def single_point(loc):
    try:
        g = wkt.loads(loc)
    except Exception:
        return None
    if isinstance(g, Point):
        return g
    if isinstance(g, MultiPoint) and len(g.geoms) == 1:
        return g.geoms[0]
    return None


def katanga(states, shapes, iso2to3, cid_cod):
    cod_states = [s for s in states if s["country_code"] == "CD"]
    cod_feats = shapes.get("COD", [])
    union = unary_union([shape(f["geometry"]) for f in cod_feats])
    recs, seen = [], set()
    for path in sorted(glob.glob(str(SITES / "*/*/*.json"))):
        for rec in json.load(open(path, encoding="utf-8")):
            li = rec.get("location_info") or {}
            obs = {(c.get("observed_name") or "").strip() for c in li.get("state_or_province") or []}
            ctry = {(c.get("normalized_uri") or "").rsplit("/", 1)[-1] for c in li.get("country") or []}
            if not obs & {"Katanga", "Katanga Province"} or cid_cod not in ctry:
                continue
            key = (rec["source_id"], rec["record_id"], rec.get("created_by"))
            if key in seen:
                continue
            seen.add(key)
            loc = (li.get("location") or "").strip()
            crs = ((li.get("crs") or {}).get("normalized_uri") or "").rsplit("/", 1)[-1]
            pt = single_point(loc) if loc else None
            norm = sorted({(c.get("normalized_uri") or "").rsplit("/", 1)[-1] for c in li.get("state_or_province") or []
                           if (c.get("observed_name") or "").strip() in ("Katanga", "Katanga Province")})
            group = ("drop list (state -> Q6152 Tanga)" if norm == ["Q6152"] else
                     "state never normalized" if norm == [""] else "state normalized to " + ",".join(norm))
            r = {"group": group, "record_id": rec["record_id"], "source_id": rec["source_id"], "location": loc, "crs": crs}
            if not loc:
                r["status"] = "no location"
            elif crs not in ("", "Q701"):
                r["status"] = f"not WGS84 ({crs})"
            elif pt is None:
                r["status"] = "not a single point"
            elif pt.x == 0 and pt.y == 0:
                r["status"] = "0,0"
            elif (pt.x * 2).is_integer() and (pt.y * 2).is_integer():
                r["status"] = "round placeholder"
            else:
                hit = [f["properties"]["shapeName"] for f in cod_feats if shape(f["geometry"]).contains(pt)]
                r["status"] = "usable"
                r["shape"] = hit[0] if len(hit) == 1 else ("none" if not hit else " | ".join(hit))
                r["inside_cod"] = union.contains(pt)
                if not r["inside_cod"]:
                    flips = {"lat sign": Point(pt.x, -pt.y), "lon sign": Point(-pt.x, pt.y),
                             "both signs": Point(-pt.x, -pt.y), "lat/lon swapped": Point(pt.y, pt.x)}
                    r["flag"] = ", ".join(k for k, p in flips.items() if union.contains(p)) or "no simple flip lands in DRC"
            recs.append(r)
    return cod_states, cod_feats, recs


def main():
    states = load_states()
    countries = list(csv.DictReader(open(ENT / "country.csv", newline="", encoding="utf-8")))
    iso2to3 = {c["iso2"]: c["iso3"] for c in countries}
    meta, shapes = load_shapes()
    rows = match(states, iso2to3, shapes)
    with open(HERE / "state_shape_match.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["minmod_id", "country_code", "name", "match_tier", "shapeISO", "shapeName"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    res = {"states": len(states), "gb_countries": len(meta)}
    res["mojibake_shape_names"] = collections.Counter(
        iso3 for iso3, fs in shapes.items() for f in fs if demojibake(f["properties"]["shapeName"]) != f["properties"]["shapeName"])
    # sanity check of single matches: does the matched shape contain MinMod's own lat/lon for the state?
    by_id = {s["minmod_id"]: s for s in states}
    chk = collections.Counter()
    country_union = {}
    with open(HERE / "centroid_check.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["minmod_id", "country_code", "name", "match_tier", "shapeName", "minmod_lat", "minmod_lon", "inside_matched_shape"])
        for r in rows:
            if r["match_tier"] not in ("iso", "name", "alt name"):
                continue
            s = by_id[r["minmod_id"]]
            try:
                pt = Point(float(s["longitude"]), float(s["latitude"]))
            except ValueError:
                chk["no lat/lon"] += 1
                continue
            g = shape(r["_cands"][0]["geometry"])
            inside = g.contains(pt) or g.distance(pt) < 0.05  # ~5 km slack for simplified coastlines
            if inside:
                chk["inside"] += 1
            else:
                cu = country_union.setdefault(r["country_code"], unary_union(
                    [shape(c["geometry"]) for c in shapes[iso2to3[r["country_code"]]]]))
                chk["outside shape, inside country" if cu.distance(pt) < 0.05 else "outside the country entirely"] += 1
            w.writerow([r["minmod_id"], r["country_code"], r["name"], r["match_tier"], r["shapeName"], s["latitude"], s["longitude"], inside])
    res["centroid_check"] = chk
    res["tiers"] = collections.Counter(r["match_tier"].split(" (")[0] for r in rows)
    res["ambiguous_kinds"] = collections.Counter(r["match_tier"] for r in rows if r["match_tier"].startswith("ambiguous"))
    per = collections.defaultdict(collections.Counter)
    for r in rows:
        per[r["country_code"]][r["match_tier"].split(" (")[0]] += 1
    res["per_country"] = {k: dict(v) for k, v in per.items()}
    res["gb_shape_counts"] = {m["boundaryISO"]: len(shapes[m["boundaryISO"]]) for m in meta}
    res["iso2to3_missing"] = sorted({s["country_code"] for s in states if s["country_code"] not in iso2to3})
    res["no_gb"] = sorted({r["country_code"] for r in rows if r["match_tier"].startswith("no gbOpen")})
    res["licenses"] = collections.Counter(m["boundaryLicense"] for m in meta)
    res["license_by_country"] = {m["boundaryISO"]: m["boundaryLicense"] for m in meta}
    res["release"] = {"build_dates": collections.Counter(m["buildDate"] for m in meta),
                      "commits": collections.Counter(m["simplifiedGeometryGeoJSON"].split("/raw/")[1].split("/")[0] for m in meta)}
    if SITES:
        cid_cod = next(c["minmod_id"] for c in countries if c["iso3"] == "COD")
        cod_states, cod_feats, recs = katanga(states, shapes, iso2to3, cid_cod)
        res["katanga"] = {
            "minmod_cd_states": [(s["minmod_id"], s["name"], s["state_code"]) for s in cod_states],
            "gb_cod_shapes": [(f["properties"].get("shapeISO"), f["properties"]["shapeName"]) for f in cod_feats],
            "records": len(recs),
            "by_group": {g: {"records": sum(1 for r in recs if r["group"] == g),
                             "status": collections.Counter(r["status"] for r in recs if r["group"] == g),
                             "usable_by_shape": collections.Counter(r["shape"] for r in recs if r["group"] == g and r["status"] == "usable")}
                         for g in sorted({r["group"] for r in recs})},
            "status": collections.Counter(r["status"] for r in recs),
            "usable_by_shape": collections.Counter(r["shape"] for r in recs if r["status"] == "usable"),
            "outside_cod": [r for r in recs if r["status"] == "usable" and not r["inside_cod"]],
        }
        with open(HERE / "katanga_points.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["group", "source_id", "record_id", "crs", "location", "status", "shape", "inside_cod", "flag"])
            w.writeheader()
            w.writerows(recs)
    (HERE / "boundary_match_results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({k: res[k] for k in ("states", "gb_countries", "tiers", "no_gb", "iso2to3_missing")}, indent=1))


if __name__ == "__main__":
    main()
