#!/usr/bin/env python3
"""Fetch EIA energy prices and EPA vehicle data. Writes data-cache.json.

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
import time
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


EIA_TIMEOUT = 60      # seconds per request; EIA has been slow enough to blow past 30
EIA_ATTEMPTS = 3      # total tries per request, with backoff between them


def _eia_get(url):
    """GET an EIA API URL and return parsed JSON, or raise on error.

    Retries timeouts, connection errors and 5xx responses — EIA is
    intermittently slow. A 4xx is the request's own fault (bad key or
    bad params), so it fails immediately.
    """
    req = Request(url, headers=HEADERS)
    for attempt in range(1, EIA_ATTEMPTS + 1):
        try:
            with urlopen(req, timeout=EIA_TIMEOUT) as resp:
                return json.loads(resp.read())
        except HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            problem = f"HTTP {exc.code}: {body[:400]}"
            if exc.code < 500:
                raise RuntimeError(problem) from exc
        except (OSError, json.JSONDecodeError) as exc:
            problem = str(exc) or exc.__class__.__name__

        if attempt == EIA_ATTEMPTS:
            raise RuntimeError(f"{problem} (after {EIA_ATTEMPTS} attempts)")

        wait = 5 * attempt
        print(
            f"  EIA request failed ({problem}) — attempt {attempt}/{EIA_ATTEMPTS},"
            f" retrying in {wait}s",
            file=sys.stderr,
        )
        time.sleep(wait)


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
        sectorid = next(
            (f["id"] for f in facets if "residential" in f.get("name", "").lower()),
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
        print("  EIA returned no data rows", file=sys.stderr)
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


# EIA weekly retail gasoline series (US total, all formulations, $/gal).
# Regional coverage is limited -- national + PADD + a handful of states -- so
# the site exposes a national figure and lets the visitor edit it.
EIA_GAS_SERIES = {
    "regular": "EMM_EPMR_PTE_NUS_DPG",
    "midgrade": "EMM_EPMM_PTE_NUS_DPG",
    "premium": "EMM_EPMP_PTE_NUS_DPG",
}


def fetch_eia_gas_prices(api_key):
    """Fetch latest US average retail gasoline prices by grade from EIA API v2.

    Returns a dict with regular/midgrade/premium in $/gal plus period labels,
    or None if the fetch fails. A single grade failing is not fatal -- the
    caller keeps whatever previous values are cached.
    """
    if not api_key:
        print("  EIA_API_KEY not set -- skipping gasoline fetch", file=sys.stderr)
        return None

    from urllib.parse import quote as pct_encode
    key = pct_encode(api_key, safe="")

    prices = {}
    period = None
    for grade, series in EIA_GAS_SERIES.items():
        url = (
            "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
            f"?api_key={key}"
            "&frequency=weekly"
            "&data[0]=value"
            f"&facets[series][]={series}"
            "&sort[0][column]=period"
            "&sort[0][direction]=desc"
            "&length=1"
        )
        try:
            rows = _eia_get(url).get("response", {}).get("data", [])
        except Exception as exc:
            print(f"  EIA gasoline fetch failed for {grade}: {exc}", file=sys.stderr)
            continue

        if not rows:
            print(f"  EIA returned no gasoline rows for {grade}", file=sys.stderr)
            continue

        try:
            prices[grade] = round(float(rows[0]["value"]), 3)
        except (KeyError, TypeError, ValueError):
            print(f"  EIA gasoline row for {grade} had no usable value", file=sys.stderr)
            continue
        period = period or rows[0].get("period")

    if not prices:
        return None

    if period:
        try:
            as_of = datetime.strptime(period, "%Y-%m-%d").strftime("%B %-d, %Y")
        except ValueError:
            as_of = period
    else:
        as_of = None

    print(
        "  EIA gasoline: "
        + ", ".join(f"{g} ${p}" for g, p in prices.items())
        + (f" (week of {as_of})" if as_of else ""),
        file=sys.stderr,
    )

    prices["period"] = period
    prices["as_of"] = as_of
    return prices


def _download_epa_rows():
    """Download fueleconomy.gov vehicles.csv.zip and return its rows as dicts.

    The full file covers every vehicle EPA has rated, so both the EV list and
    the gasoline comparison set come from this one download.
    Returns None if the fetch or extraction fails.
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

    return list(csv.DictReader(io.StringIO(csv_bytes.decode("latin-1"))))


def fetch_epa_evs(rows):
    """Return 2026 BEVs sorted by MPGe descending."""
    evs = []
    for row in rows:
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


# EPA fuelType1 values mapped to the grades the break-even calculator prices.
# Diesel is deliberately excluded -- it needs its own fuel price series.
GAS_GRADES = {
    "Regular Gasoline": "regular",
    "Midgrade Gasoline": "midgrade",
    "Premium Gasoline": "premium",
}

# The break-even comparison only gets interesting below roughly 30 MPG, so the
# cache keeps the thirstiest slice rather than every gasoline vehicle rated.
GAS_VEHICLE_LIMIT = 80


def fetch_epa_gas_vehicles(rows):
    """Return the thirstiest 2026 gasoline vehicles, one per make/model.

    Deduplicates on make+model keeping the least efficient configuration --
    that is the one whose fuel spending is most likely to cover an EV payment,
    and it stops a single nameplate filling the table with trim variants.
    """
    best = {}
    for row in rows:
        if row.get("year") != "2026":
            continue
        if row.get("fuelType2", "").strip():
            continue  # PHEVs and flex-fuel: not a clean gasoline comparison

        grade = GAS_GRADES.get(row.get("fuelType1", "").strip())
        if not grade:
            continue

        try:
            mpg = float(row.get("comb08", "").strip())
        except ValueError:
            continue
        if mpg <= 0:
            continue

        make = row.get("make", "").strip()
        model = row.get("model", "").strip()
        if not make or not model:
            continue

        key = (make, model)
        if key not in best or mpg < best[key]["mpg"]:
            best[key] = {
                "id": row.get("id", "").strip(),
                "name": f"2026 {make} {model}",
                "make": make,
                "model": model,
                "drive": row.get("drive", "").strip(),
                "vclass": row.get("VClass", "").strip(),
                "mpg": round(mpg, 1),
                "city_mpg": row.get("city08", "").strip(),
                "highway_mpg": row.get("highway08", "").strip(),
                "grade": grade,
            }

    vehicles = sorted(best.values(), key=lambda v: v["mpg"])[:GAS_VEHICLE_LIMIT]
    if vehicles:
        print(
            f"  Found {len(best)} 2026 gasoline nameplates — keeping the "
            f"{len(vehicles)} thirstiest ({vehicles[0]['name']} at "
            f"{vehicles[0]['mpg']} MPG through {vehicles[-1]['mpg']} MPG)",
            file=sys.stderr,
        )
    else:
        print("  Found no 2026 gasoline vehicles", file=sys.stderr)
    return vehicles


def main():
    existing = load_existing_cache()
    api_key = os.environ.get("EIA_API_KEY", "").strip()

    print("Fetching EIA electricity rate...", file=sys.stderr)
    eia = fetch_eia_rate(api_key)

    print("Fetching EIA gasoline prices...", file=sys.stderr)
    gas = fetch_eia_gas_prices(api_key)

    print("Fetching EPA vehicle data from fueleconomy.gov...", file=sys.stderr)
    rows = _download_epa_rows()
    evs = fetch_epa_evs(rows) if rows is not None else None
    gas_vehicles = fetch_epa_gas_vehicles(rows) if rows is not None else None

    cache = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Fall back to previous cached values if a fetch fails
        "eia": eia if eia is not None else existing.get("eia"),
        "eia_gas": gas if gas is not None else existing.get("eia_gas"),
        "epa_evs_2026": evs if evs is not None else existing.get("epa_evs_2026", []),
        "epa_gas_vehicles_2026": (
            gas_vehicles if gas_vehicles is not None
            else existing.get("epa_gas_vehicles_2026", [])
        ),
    }

    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
        f.write("\n")

    # The EPA list is the whole point of the cache, so losing it is fatal. The EIA
    # rate changes at most once a month and the previous value is carried forward
    # above, so a bad EIA night is only a warning — unless nothing is cached yet.
    errors = []
    if evs is None:
        errors.append("EPA fetch failed — fueleconomy.gov unreachable or returned bad data")

    if not api_key:
        print("NOTE: EIA_API_KEY not set — EIA values kept from previous cache", file=sys.stderr)
    else:
        if eia is None:
            prev_rate = (existing.get("eia") or {}).get("rate_per_kwh")
            if prev_rate is None:
                errors.append("EIA fetch failed and no previous rate is cached")
            else:
                print(
                    f"WARNING: EIA fetch failed — keeping previous cached rate ${prev_rate}/kWh",
                    file=sys.stderr,
                )

        if gas is None:
            if existing.get("eia_gas"):
                print(
                    "WARNING: EIA gasoline fetch failed — keeping previous cached prices",
                    file=sys.stderr,
                )
            else:
                print(
                    "WARNING: EIA gasoline fetch failed and nothing is cached yet — "
                    "the break-even page keeps its placeholder gasoline prices",
                    file=sys.stderr,
                )

    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if errors:
        sys.exit(1)

    print("data-cache.json written successfully.", file=sys.stderr)


if __name__ == "__main__":
    main()
