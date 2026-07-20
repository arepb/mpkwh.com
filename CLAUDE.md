# MPkWh.com — Project Instructions

## What this is
mpkwh.com — a static site ranking the most efficient electric cars sold in the US by Mi/kWh (EPA range ÷ usable battery capacity). Single-page HTML, no build step.

- **Repo:** https://github.com/arepb/mpkwh.com
- **Live:** https://mpkwh.com
- **Hosting:** GitHub Pages, served from `main` branch root. Custom domain via `CNAME` file. Pushes to `main` auto-deploy.
- **Working dir:** this folder lives in Dropbox. The `.git` directory is real but Dropbox sometimes drops files (notably `CNAME`) — see "Dropbox gotchas" below.

## Update cadence
**Every Monday.** The footer of the site states "data updates every Monday as new data is published." Commit-message convention is `Weekly EV efficiency update - YYYY-MM-DD`.

If the most recent commit on `main` is older than 7 days, the site is overdue.

## Source of truth
[ev-efficiency-tracker.md](ev-efficiency-tracker.md) is the working data document. Always update it FIRST, then sync the changes into `index.html`. Never edit `index.html` numbers without also reflecting them in the tracker.

## Data cache

A GitHub Action (`.github/workflows/refresh-ev-data.yml`) runs every Sunday at 2 AM UTC and writes `data-cache.json` to the repo root. The Monday routine reads from this file instead of hitting external URLs directly (which are blocked by the Claude Code egress policy).

`data-cache.json` contains:
- `eia` — latest US average residential electricity rate (`rate_per_kwh`, `period_label`, `published_label`)
- `epa_evs_2026` — all 2026 battery EVs from fueleconomy.gov, sorted by MPGe descending, each with `make`, `model`, `trany`, `drive`, `range`, `mpge`, `kwh_per_100mi`

The Action requires an `EIA_API_KEY` secret (free key from https://www.eia.gov/opendata/register.php). If the key is missing, `eia` is preserved from the previous cache run. `epa_evs_2026` requires no key — it downloads from fueleconomy.gov's public CSV.

If `data-cache.json` is missing or `epa_evs_2026` is empty (Action hasn't run yet), fall back to Car and Driver links in index.html for each vehicle.

## Weekly update workflow

1. **Refresh inputs from `data-cache.json`:**
   - Read `data-cache.json` first. Compare `eia.rate_per_kwh` to the current value in `ev-efficiency-tracker.md`. If different, use the new rate and update `period_label`/`published_label` references.
   - For each vehicle in the current top-20, find the matching entry in `epa_evs_2026` by make/model/trim. If `range` differs from the tracker, note it.
   - Check the top entries of `epa_evs_2026` for any vehicle with high enough range that, divided by its usable kWh (from the Pack Size Sources table in the tracker), would exceed the current rank-20 threshold (~4.09 Mi/kWh). Flag any new entrant.
   - Usable kWh is **not** in the cache — it is manually maintained in the tracker from ev-database.org and manufacturer specs.

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

5. **Update `sitemap.xml`:** bump `<lastmod>` to today's date (YYYY-MM-DD).

6. **Sanity-check before commit:**
   - Tracker, index.html table, and llms.txt list show identical 20 vehicles in identical order.
   - Both JSON-LD blocks (WebPage/ItemList and FAQPage) parse as valid JSON. The ItemList positions match table ranks.
   - Cost/100mi recomputed if the EIA rate changed (top 3 are visible at a glance — easy to spot-check).
   - sitemap.xml `<lastmod>` is today's date.
   - View on mobile width (≤480px) — the Pack kWh and Usable kWh columns hide via `.hide-mobile`; everything else should still fit.

7. **Commit & push:**
   - One commit, message: `Weekly EV efficiency update - YYYY-MM-DD`.
   - Author: `arepb <reillybrennan@gmail.com>` (configured in this repo's `.git/config`).
   - Push to `main` — GitHub Pages auto-deploys within ~1 minute.
   - Verify at https://mpkwh.com that the "Updated" date matches.

## Feature changes (not weekly data)
Use focused, separate commits — see existing history for tone (`Add rising badge feature; apply to Model Y LR`, `Move rising indicator to rank column`, `Clarify EIA footnote date label`). Don't bundle feature work into the weekly data commit.

## Dropbox gotchas
This repo lives inside a Dropbox-synced folder. Two recurring issues:

- **`CNAME` can disappear.** It went missing once (lost the custom domain when pushed, would have broken `mpkwh.com`). Before any commit, run `git status` — if `CNAME` shows as deleted, restore it: `git checkout origin/main -- CNAME`. Never commit a deletion of `CNAME`.
- **`.DS_Store` files appear.** Already gitignored.

## Files
- `index.html` — the entire site (single page, inline CSS).
- `ev-efficiency-tracker.md` — source-of-truth data doc (this is what you edit first each week).
- `CNAME` — `mpkwh.com` (do not delete; do not modify).
- `favicon.svg`, `preview.png`, `preview.svg` — icons / og:image. Per parent CLAUDE.md: og:image must be raster (PNG), not SVG, for iOS/iMessage preview compatibility.
- `robots.txt` — AI crawlers (GPTBot, ClaudeBot, PerplexityBot, anthropic-ai, GoogleOther) explicitly welcomed.
- `sitemap.xml` — single URL; `<lastmod>` is bumped to the current date by every weekly update.
- `llms.txt` — AI-citable plain-text summary of the site. Mirrors the top-20 list and is regenerated each weekly update so AI search engines (ChatGPT, Claude, Perplexity) cite current rankings, not stale data.
- `data-cache.json` — pre-fetched EIA rate and EPA EV data, written each Sunday by the GitHub Action. Read by the Monday routine instead of hitting external URLs. Commit this file; do not gitignore it.
- `.github/workflows/refresh-ev-data.yml` — the GitHub Action that populates `data-cache.json`.
- `.github/scripts/fetch-ev-data.py` — the fetch script called by the Action.

## SEO / GEO
- index.html includes two JSON-LD blocks: `WebPage` (with `ItemList` of all 20 ranked vehicles) and `FAQPage` (stable Q&As about Mi/kWh, calculation, update cadence, data sources). Both must remain valid JSON after every weekly update — validate before committing.
- All OG/Twitter meta tags are static and don't need weekly updates. og:image is the 1200×630 PNG `/preview.png` (raster, iOS/iMessage compatible).
- The FAQPage answers are deliberately stable — they describe the methodology, not the rankings. Don't add weekly-changing answers (like "what's the most efficient EV today") because they'd go stale between commits.

## Mobile responsiveness
Per parent CLAUDE.md: always consider mobile when editing `index.html`. The site uses a single CSS breakpoint via `.hide-mobile` to hide the Pack kWh and Usable kWh columns on narrow viewports. Test changes against ≤480px width.
