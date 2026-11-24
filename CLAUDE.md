# MPkWh.com — Project Instructions

## What this is
mpkwh.com — a static site ranking the most efficient electric cars sold in the US by Mi/kWh (EPA range ÷ usable battery capacity). Single-page HTML, no build step.

- **Repo:** https://github.com/arepb/mpkwh.com
- **Live:** https://mpkwh.com
- **Hosting:** GitHub Pages, served from `main` branch root. Custom domain via `CNAME` file. Pushes to `main` auto-deploy.
- **Working dir:** `~/Developer/MPKWH` (moved out of Dropbox 2026-08-25). Cross-project conventions live in `~/.claude/CLAUDE.md`.

## Update cadence
**Every Monday.** The footer of the site states "data updates every Monday as new data is published." Commit-message convention is `Weekly EV efficiency update - YYYY-MM-DD`.

If the most recent commit on `main` is older than 7 days, the site is overdue.

## Source of truth
[ev-efficiency-tracker.md](ev-efficiency-tracker.md) is the working data document. Always update it FIRST, then sync the changes into `index.html`. Never edit `index.html` numbers without also reflecting them in the tracker.

## Data cache

A GitHub Action (`.github/workflows/refresh-ev-data.yml`) runs every Sunday at 2 AM UTC and writes `data-cache.json` to the repo root. The Monday routine reads from this file instead of hitting external URLs directly (which are blocked by the Claude Code egress policy).

`data-cache.json` contains:
- `eia` — latest US average residential electricity rate (`rate_per_kwh`, `period_label`, `published_label`)
- `eia_gas` — latest US average retail gasoline prices by grade (`regular`, `midgrade`, `premium` in $/gal, plus `period` and `as_of`). Feeds the break-even page.
- `epa_evs_2026` — all 2026 battery EVs from fueleconomy.gov, sorted by MPGe descending, each with `make`, `model`, `trany`, `drive`, `range`, `mpge`, `kwh_per_100mi`
- `epa_gas_vehicles_2026` — the 80 thirstiest 2026 gasoline vehicles, deduplicated to one entry per make/model (keeping the least efficient configuration), each with `name`, `mpg`, `grade`, `drive`, `vclass`. Diesels, PHEVs and flex-fuel are excluded. Feeds the break-even comparison table.

The Action requires an `EIA_API_KEY` secret (free key from https://www.eia.gov/opendata/register.php). If the key is missing, `eia` is preserved from the previous cache run. `epa_evs_2026` requires no key — it downloads from fueleconomy.gov's public CSV.

If `data-cache.json` is missing or `epa_evs_2026` is empty (Action hasn't run yet), fall back to Car and Driver links in index.html for each vehicle.

## Weekly update workflow

1. **Refresh inputs from `data-cache.json`:**
   - Read `data-cache.json` first. Compare `eia.rate_per_kwh` to the current value in `ev-efficiency-tracker.md`. If different, use the new rate and update `period_label`/`published_label` references.
   - For each vehicle in the current top-20, find the matching entry in `epa_evs_2026` by make/model/trim. If `range` differs from the tracker, note it.
   - Check the top entries of `epa_evs_2026` for any vehicle with high enough range that, divided by its usable kWh (from the Pack Size Sources table in the tracker), would exceed the current rank-20 threshold (currently ~4.16 Mi/kWh — always check the tracker for the live figure; it shifts when new entrants push the cutoff up).
   - Usable kWh is **not** in the cache — it is manually maintained in the tracker from ev-database.org and manufacturer specs.
   - **For new entrants with no confirmed pack spec:** estimate usable kWh from the EPA energy calc: `range × (kwh_per_100mi / 100) × charging_efficiency`. Effective charging efficiency varies by manufacturer — calibrated from known pack specs: Tesla ~89%, Toyota/Lexus ~89–90%, Lucid ~86–87%. For Lucid, always prefer the confirmed spec from EVKX or UltimateSpecs over the EPA calc — Lucid's real efficiency is lower than the 0.89 default, so the EPA calc significantly overshoots. Document estimated values in Pack Size Sources with a note that manufacturer spec is unconfirmed. Update the entry as soon as the confirmed spec becomes available (ev-database.org usually has it within a few weeks of EPA rating).

2. **Update `ev-efficiency-tracker.md`:**
   - Header date (`# EV Efficiency Tracker — Updated <Month D, YYYY>`).
   - EIA rate line if it changed.
   - Top-20 table: rank, vehicle, EPA range, Gross kWh, Usable kWh, Mi/kWh (= EPA range ÷ Usable kWh), Cost/100mi (= 100 ÷ Mi/kWh × rate).
   - Re-sort by Mi/kWh descending; reassign ranks 1–20.

3. **Sync into `index.html`** — every weekly update touches FOUR places:
   - `<span class="updated">Updated <Month D, YYYY></span>` in the header.
   - The main `<table>` rows in `<main>` — rank, vehicle name, range, Pack kWh (hidden on mobile), Usable kWh (hidden on mobile), Mi/kWh, Cost/100mi.
   - The JSON-LD `ItemList` block in the `<head>` — must list all 20 vehicles with `position`, `name`, `url`, and `description` (Mi/kWh, EPA range, usable kWh). Format: `"5.35 Mi/kWh — 321 mi EPA range — 60 kWh usable"`.
   - **NEW badges (2-week lifetime):** vehicles get `<span class="badge-new" data-since="YYYY-MM-DD">NEW</span>` appended after their `</a>` link. The `data-since` is the date the vehicle first appeared on the list. The badge stays visible for 14 days from `data-since`, then is removed by the routine. Each weekly run does two things:
     1. Read every existing `<span class="badge-new" data-since="...">` from the previous commit's index.html. If `today - data-since >= 14 days`, drop the badge from this week's HTML. Otherwise carry it forward (preserve the same `data-since`).
     2. Diff this week's top-20 vehicle names vs the previous commit's. Any vehicle that's new (or returning after absence) gets a freshly-stamped `<span class="badge-new" data-since="<today>">NEW</span>`.
   There are no rising/falling rank arrows — the previous `.rank-up` system was removed because rank shifts caused by new entrants don't reflect actual efficiency changes.

4. **Update `llms.txt`** (AI-citable summary):
   - Bump the "Updated <Month YYYY>" header to today's date.
   - Replace the numbered top-20 list with this week's rankings, formatted as `N. <Vehicle> — <Mi/kWh> Mi/kWh — <range> mi range — <usable kWh> kWh usable`.
   - If the EIA rate changed, update the rate line in Notes.
   - Keep the "What is Mi/kWh?" section, FAQ-style notes, and Pages link unchanged.

5. **Sync `break-even/index.html`** — the calculator page carries its own inline copies of the data, because the site has no build step. Four things to check:
   - `PRICES.electricity` — update `rate`, `period_label` and `published_label` if the EIA rate changed.
   - `PRICES.gas` — copy `regular`, `midgrade`, `premium` and `as_of` from `data-cache.json` → `eia_gas`. While `as_of` is `null` the page tells visitors the gasoline figures are placeholders, so setting it is what switches on the sourced label.
   - `EVS` — only when the leaderboard's top 20 changed. Keep it in the same order as the tracker, and keep each `id` stable, because `lease-offers.json` keys off it.
   - `GAS_VEHICLES` — copy from `data-cache.json` → `epa_gas_vehicles_2026`. The comparison section hides itself while the array is empty.
   - Also bump `<span class="updated">` and the `Updated` date in the header.
   - After editing, re-check that the hard-coded default result in the HTML (the hero figures and the "Show the math" rows) still matches what the JS computes from the new defaults. That static state is what crawlers and no-JS visitors see, so it must not drift.

6. **Verify tracked lease offers** — see "Lease offer tracking" below.

7. **Update `sitemap.xml`:** bump `<lastmod>` to today's date (YYYY-MM-DD) on both URLs.

8. **Sanity-check before commit:**
   - Tracker, index.html table, and llms.txt list show identical 20 vehicles in identical order.
   - Both JSON-LD blocks (WebPage/ItemList and FAQPage) parse as valid JSON. The ItemList positions match table ranks.
   - Cost/100mi recomputed if the EIA rate changed (top 3 are visible at a glance — easy to spot-check).
   - sitemap.xml `<lastmod>` is today's date on both URLs.
   - `break-even/index.html`: both JSON-LD blocks parse, the inline JS parses, and the static default hero figures match the computed ones.
   - View on mobile width (≤480px) — the Pack kWh and Usable kWh columns hide via `.hide-mobile`; everything else should still fit.

9. **Commit & push:**
   - One commit, message: `Weekly EV efficiency update - YYYY-MM-DD`.
   - Author: `arepb <reillybrennan@gmail.com>` (configured in this repo's `.git/config`).
   - Push to `main` — GitHub Pages auto-deploys within ~1 minute.
   - Verify at https://mpkwh.com that the "Updated" date matches.

## Lease offer tracking

`lease-offers.json` holds manually verified EV payment offers for the break-even
calculator. This is the least durable data on the site and the only thing here
that is not machine-refreshed, so it has its own rules.

**An offer is never published without both `source_url` and `verified_at`.** The
calculator ignores any entry missing either field, or missing `monthly_payment`,
and falls back to a user-entered payment with a note saying no offer is tracked.
That fallback is a perfectly good state — an empty offer file is better than a
wrong one.

Fields: `monthly_payment`, `term_months`, `due_at_signing`, `acquisition_fee`,
`other_required_upfront`, `annual_mileage_allowance`, `overage_fee_per_mile`,
`source_url`, `verified_at` (YYYY-MM-DD), `market`, `notes`. The `id` must match
an `id` in the `EVS` array in `break-even/index.html`.

**Freshness.** The page flags any offer more than 14 days past `verified_at` with
"Offer may have changed. Verify current pricing." It does not hide it. Weekly:
re-check each offer against its `source_url`, update the figures, and bump
`verified_at`. If an offer has expired, null out `monthly_payment` rather than
deleting the entry — the vehicle keeps its slot and the page reverts to the
user-entered payment.

**Offers are advertised national figures, not quotes.** They vary by credit tier,
geography, inventory, trim, loyalty and conquest incentives. The page says so, and
every field is user-overridable. Do not add taxes or location-specific fees.

**After editing `lease-offers.json`, mirror it into the `OFFERS` object in
`break-even/index.html`** — the page has no build step and reads its own inline
copy.

## Feature changes (not weekly data)
Use focused, separate commits — see existing history for tone (`Add rising badge feature; apply to Model Y LR`, `Move rising indicator to rank column`, `Clarify EIA footnote date label`). Don't bundle feature work into the weekly data commit.

## Before any commit
Run `git status` and confirm `CNAME` is neither deleted nor modified — a push without it drops the `mpkwh.com` custom domain. Restore with `git checkout origin/main -- CNAME`.

## Files
- `index.html` — the leaderboard (single page, inline CSS).
- `break-even/index.html` — the break-even calculator at `/break-even/`. Single page, inline CSS and JS, no build step. Answers "which gas cars can pay for this EV?" Leads with the share of the payment that avoided fuel spending covers, with break-even MPG as the secondary metric. Its default state is rendered in HTML so it is meaningful to crawlers and without JS; the JS only recalculates.
- `lease-offers.json` — manually verified EV payment offers. See "Lease offer tracking".
- `ev-efficiency-tracker.md` — source-of-truth data doc (this is what you edit first each week).
- `CNAME` — `mpkwh.com` (do not delete; do not modify).
- `favicon.svg`, `preview.png`, `preview.svg` — icons / og:image. og:image must be raster (PNG), not SVG, for iOS/iMessage preview compatibility (`~/.claude/CLAUDE.md`).
- `robots.txt` — AI crawlers (GPTBot, ClaudeBot, PerplexityBot, anthropic-ai, GoogleOther) explicitly welcomed.
- `sitemap.xml` — two URLs (`/` and `/break-even/`); `<lastmod>` is bumped to the current date by every weekly update.
- `llms.txt` — AI-citable plain-text summary of the site. Mirrors the top-20 list and is regenerated each weekly update so AI search engines (ChatGPT, Claude, Perplexity) cite current rankings, not stale data. Also carries the break-even MPG definition and formula, which are stable and do not need weekly edits.
- `data-cache.json` — pre-fetched EIA rate and EPA EV data, written each Sunday by the GitHub Action. Read by the Monday routine instead of hitting external URLs. Commit this file; do not gitignore it.
- `.github/workflows/refresh-ev-data.yml` — the GitHub Action that populates `data-cache.json`.
- `.github/scripts/fetch-ev-data.py` — the fetch script called by the Action.

## SEO / GEO
- index.html includes two JSON-LD blocks: `WebPage` (with `ItemList` of all 20 ranked vehicles) and `FAQPage` (stable Q&As about Mi/kWh, calculation, update cadence, data sources). Both must remain valid JSON after every weekly update — validate before committing.
- All OG/Twitter meta tags are static and don't need weekly updates. og:image is the 1200×630 PNG `/preview.png` (raster, iOS/iMessage compatible).
- The FAQPage answers are deliberately stable — they describe the methodology, not the rankings. Don't add weekly-changing answers (like "what's the most efficient EV today") because they'd go stale between commits.
- `break-even/index.html` has its own `WebPage` and `FAQPage` blocks. Same rule: the FAQ describes the calculation, never a specific result, because results change with every input.
- If share URLs with query strings (`/break-even/?miles=1200`) are ever added, they must canonicalise to `/break-even/` — an unbounded crawlable query space is the trap that hit colortable.org (see `~/.claude/CLAUDE.md`).

## Mobile responsiveness
Consider mobile when editing `index.html`. The site uses a single CSS breakpoint via `.hide-mobile` to hide the Pack kWh and Usable kWh columns on narrow viewports. Test changes against ≤480px width.
