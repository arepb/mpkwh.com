#!/usr/bin/env python3
"""Fetch EIA electricity rate and EPA EV data. Writes data-cache.json.

Runs as a GitHub Action every Sunday so the Monday Claude Code routine
can read local data instead of hitting external URLs directly.

Requires:
  EIA_API_KEY env var — free key from https://www.eia.gov/opendata/register.php
  (if unset, EIA section is skipped and the previous cached value is kept)
"""

import csv
import io
import json
import os
import sys
import zipfile
from datetime import datetime, date, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CACHE_PATH = "data-cache.json"
HEADERS = {"User-Agent": "mpkwh.com EV data updater (github.com/arepb/mpkwh.com)"}


def load_existing_cache():
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _eia_get(url):
    """GET an EIA API URL and return parsed JSON, or raise on error."""
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {exc.code}: {body[:400]}") from exc


def fetch_eia_rate(api_key):
    """Fetch latest US average residential electricity rate from EIA API v2.

    Returns a dict with rate_per_kwh, period, period_label, published_label,
    or None if the fetch fails.
    """
    if not api_key:
        print("  EIA_API_KEY not set — skipping EIA fetch", file=sys.stderr)
        return None

    from urllib.parse import quote as pct_encode
    key = pct_encode(api_key, safe="")

    # Step 1: discover the sectorid value for residential via the facet endpoint
    try:
        facet_data = _eia_get(
            f"https://api.eia.gov/v2/electricity/retail-sales/facet/sectorid/?api_key={key}"
        )
        facets = facet_data.get("response", {}).get("facets", [])
        print(f"  EIA sectorid facets: {facets}", file=sys.stderr)
        sectorid = next(
            (f["id"] for f in facets if "residential" in f.get("description", "").lower()),
            None,
        )
    except Exception as exc:
        print(f"  EIA facet discovery failed: {exc}", file=sys.stderr)
        sectorid = None

    if not sectorid:
        print("  Could not find residential sectorid — aborting EIA fetch", file=sys.stderr)
        return None

    print(f"  Using sectorid={sectorid!r} for residential", file=sys.stderr)

    # Step 2: fetch data with the correct sectorid
    # Brackets in EIA v2 param names must NOT be percent-encoded — build manually
    url = (
        "https://api.eia.gov/v2/electricity/retail-sales/data/"
        f"?api_key={key}"
        "&frequency=monthly"
        "&data[0]=price"
        f"&facets[sectorid][]={pct_encode(sectorid, safe='')}"
        "&facets[stateid][]=US"
        "&sort[0][column]=period"
        "&sort[0][direction]=desc"
        "&length=3"
    )

    try:
        data = _eia_get(url)
    except Exception as exc:
        print(f"  EIA data request failed: {exc}", file=sys.stderr)
        return None

    rows = data.get("response", {}).get("data", [])
    if not rows:
        print(f"  EIA returned no data rows — response: {json.dumps(data)[:600]}", file=sys.stderr)
        return None

    latest = rows[0]
    period = latest["period"]  # e.g. "2026-04"
    year, month = int(period[:4]), int(period[5:7])
    period_label = date(year, month, 1).strftime("%B %Y")

    # EIA publishes the Electric Power Monthly with roughly a 2-month lag
    pub_month, pub_year = month + 2, year
    if pub_month > 12:
        pub_month -= 12
        pub_year += 1
    published_label = date(pub_year, pub_month, 1).strftime("%B %Y")

    rate = round(float(latest["price"]) / 100, 4)  # cents/kWh → $/kWh
    print(f"  EIA rate: ${rate}/kWh ({period_label}, published {published_label})", file=sys.stderr)

    return {
        "rate_per_kwh": rate,
        "period": period,
        "period_label": period_label,
        "published_label": published_label,
    }


def fetch_epa_evs():
    """Download fueleconomy.gov vehicles.csv.zip; return 2026 BEVs sorted by MPGe.

    Returns a list of dicts, or None if the fetch fails.
    """
    url = "https://www.fueleconomy.gov/feg/epadata/vehicles.csv.zip"
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=120) as resp:
            content = resp.read()
    except (URLError, HTTPError) as exc:
        print(f"  EPA request failed: {exc}", file=sys.stderr)
        return None

    try:
        z = zipfile.ZipFile(io.BytesIO(content))
        csv_bytes = z.read("vehicles.csv")
    except Exception as exc:
        print(f"  ZIP extraction failed: {exc}", file=sys.stderr)
        return None

    reader = csv.DictReader(io.StringIO(csv_bytes.decode("latin-1")))
    evs = []
    for row in reader:
        if row.get("year") != "2026":
            continue
        if row.get("fuelType1", "").strip() != "Electricity":
            continue
        if row.get("fuelType2", "").strip():
            continue  # skip PHEVs (have a second fuel type)

        range_str = row.get("range", "").strip()
        mpge_str = row.get("comb08", "").strip()
        if not range_str or not mpge_str:
            continue

        try:
            range_val = int(float(range_str))
            mpge = float(mpge_str)
        except ValueError:
            continue

        kwh_str = row.get("combE", "").strip()
        kwh = round(float(kwh_str), 2) if kwh_str else None

        evs.append({
            "id": row.get("id", "").strip(),
            "make": row.get("make", "").strip(),
            "model": row.get("model", "").strip(),
            "trany": row.get("trany", "").strip(),
            "drive": row.get("drive", "").strip(),
            "range": range_val,
            "mpge": mpge,
            "kwh_per_100mi": kwh,
        })

    evs.sort(key=lambda x: x["mpge"], reverse=True)
    top = evs[0] if evs else {}
    print(
        f"  Found {len(evs)} 2026 BEVs"
        + (f" — top: {top['make']} {top['model']} {top['mpge']} MPGe" if top else ""),
        file=sys.stderr,
    )
    return evs


def main():
    existing = load_existing_cache()
    api_key = os.environ.get("EIA_API_KEY", "").strip()

    print("Fetching EIA electricity rate...", file=sys.stderr)
    eia = fetch_eia_rate(api_key)

    print("Fetching EPA EV data from fueleconomy.gov...", file=sys.stderr)
    evs = fetch_epa_evs()

    cache = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Fall back to previous cached values if a fetch fails
        "eia": eia if eia is not None else existing.get("eia"),
        "epa_evs_2026": evs if evs is not None else existing.get("epa_evs_2026", []),
    }

    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
        f.write("\n")

    # "No API key" is expected and not an error. Actual fetch failures are.
    errors = []
    if api_key and eia is None:
        errors.append("EIA fetch failed despite EIA_API_KEY being set")
    elif not api_key:
        print("NOTE: EIA_API_KEY not set — EIA rate kept from previous cache", file=sys.stderr)
    if evs is None:
        errors.append("EPA fetch failed — fueleconomy.gov unreachable or returned bad data")

    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if errors:
        sys.exit(1)

    print("data-cache.json written successfully.", file=sys.stderr)


if __name__ == "__main__":
    main()
