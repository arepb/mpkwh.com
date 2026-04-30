# MPkWh.com — Project Instructions

## What this is
mpkwh.com — a static site ranking the most efficient electric cars sold in the US by Mi/kWh (EPA-derived). Single-page HTML, no build step.

- **Repo:** https://github.com/arepb/mpkwh.com
- **Live:** https://mpkwh.com
- **Hosting:** GitHub Pages, served from `main` branch root. Custom domain via `CNAME` file. Pushes to `main` auto-deploy.
- **Working dir:** this folder lives in Dropbox. The `.git` directory is real but Dropbox sometimes drops files (notably `CNAME`) — see "Dropbox gotchas" below.

## Update cadence
**Every Monday.** The footer of the site states "data updates every Monday as new data is published." Commit-message convention is `Weekly EV efficiency update - YYYY-MM-DD`.

If the most recent commit on `main` is older than 7 days, the site is overdue.

## Source of truth
[ev-efficiency-tracker.md](ev-efficiency-tracker.md) is the working data document. Always update it FIRST, then sync the changes into `index.html`. Never edit `index.html` numbers without also reflecting them in the tracker.

## Weekly update workflow

1. **Refresh inputs:**
   - EPA fuel economy ratings for new/changed model years (caranddriver.com is the linked source per vehicle).
   - EIA US average residential electricity rate (published monthly with ~2-month lag). Stored at the top of `ev-efficiency-tracker.md` as `$0.XXXX/kWh`. As of 2026-04-27 it's `$0.1765/kWh` (Feb 2026, published April 2026).

2. **Update `ev-efficiency-tracker.md`:**
   - Header date (`# EV Efficiency Tracker — Updated <Month D, YYYY>`).
   - EIA rate line if it changed.
   - Top-20 table: rank, vehicle, EPA range, Mi/kWh (= MPGe ÷ 33.7), MPGe, Cost/100mi (= 100 ÷ Mi/kWh × rate).
   - Re-sort by Mi/kWh descending; reassign ranks 1–20.

3. **Sync into `index.html`** — every weekly update touches FOUR places:
   - `<span class="updated">Updated <Month D, YYYY></span>` in the header.
   - The main `<table>` rows in `<main>` — rank, vehicle name, range, Mi/kWh, MPGe (hidden on mobile), Cost/100mi.
   - The JSON-LD `ItemList` block in the `<head>` — must list all 20 vehicles with `position`, `name`, `url`, and `description` (Mi/kWh, EPA range, MPGe).
   - Any "rising" badges: if a vehicle's rank improved week-over-week, mark it. Remove badges that no longer apply.

4. **Sanity-check before commit:**
   - Tracker table and `index.html` table show identical numbers in identical order.
   - JSON-LD positions match table ranks.
   - Cost/100mi recomputed if the EIA rate changed (top 3 are visible at a glance — easy to spot-check).
   - View on mobile width (≤480px) — the MPGe column hides via `.hide-mobile`; everything else should still fit.

5. **Commit & push:**
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
- `robots.txt`, `sitemap.xml`, `llms.txt` — standard SEO/AI metadata.

## Mobile responsiveness
Per parent CLAUDE.md: always consider mobile when editing `index.html`. The site uses a single CSS breakpoint via `.hide-mobile` to drop the MPGe column on narrow viewports. Test changes against ≤480px width.
