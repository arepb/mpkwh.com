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


def fetch_eia_rate(api_key):
    """Fetch latest US average residential electricity rate from EIA API v2.

    Returns a dict with rate_per_kwh, period, period_label, published_label,
    or None if the fetch fails.
    """
    if not api_key:
        print("  EIA_API_KEY not set — skipping EIA fetch", file=sys.stderr)
        return None

    # Brackets in EIA v2 param names must NOT be percent-encoded — build manually
    from urllib.parse import quote as pct_encode
    url = (
        "https://api.eia.gov/v2/electricity/retail-sales/data/"
        f"?api_key={pct_encode(api_key, safe='')}"
        "&frequency=monthly"
        "&data[0]=price"
        "&facets[sectorid][]=RES"
        "&facets[stateid][]=US"
        "&sort[0][column]=period"
        "&sort[0][direction]=desc"
        "&length=3"
    )

    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        print(f"  EIA request failed: {exc} — body: {body[:500]}", file=sys.stderr)
        return None
    except URLError as exc:
        print(f"  EIA request failed: {exc}", file=sys.stderr)
        return None

    rows = data.get("response", {}).get("data", [])
    if not rows:
        import json as _json
        print(f"  EIA returned no data rows — full response: {_json.dumps(data)[:800]}", file=sys.stderr)
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
