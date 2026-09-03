# CPD Finder

CPD Finder is a lightweight discovery site for professional development from awarding bodies, professional organisations and education-sector partners. It prioritises calm browsing: the current three months are shown together, with undated and on-demand learning in a separate **Learn anytime** section.

## Architecture

```text
sources.txt → daily GitHub Action → Python collectors → public/data/opportunities.json → static website
```

There is no database, hosted API or always-running server. GitHub Pages serves the contents of `public/`, and the browser reads the generated JSON using repository-relative URLs so project subpaths work correctly.

The JSON contains `schemaVersion`, `generatedAt`, normalised `opportunities`, and per-source health records. An opportunity has stable `id`, provider, type, concise description, optional ISO dates/times, delivery/location, explicit cost and free-state (unknown remains `null`/`Unknown`), a self-paced flag, source and destination URLs, tags and `lastSeen`.

Collectors live in `collector/adapters/`. Known domains select their own adapter; an unfamiliar domain receives the generic JSON-LD and common-card extractor. Pearson's adapter discovers the public Cvent configuration embedded in its page, reads the calendar feed and resolves every published item to its session-specific registration URL; it does not publish a Pearson card if that direct destination cannot be resolved. ETF currently exposes much of its catalogue through a client-side widget, so its dedicated adapter provides an isolated extension point while safely retaining earlier data if the rendered catalogue is not present in fetched HTML. The IMI adapter reads its server-rendered event cards, NOCN treats genuine course cards as self-paced, and NCFE builds on structured/common markup extraction.

If a fetch fails or returns no credible opportunities, that source is marked as an error and its non-expired last-known-good opportunities remain in the output. Other successful sources still update. Dated opportunities whose final date is before collection day are removed; self-paced opportunities are retained. Deduplication conservatively combines provider, title, occurrence date and canonical URL so recurring sessions remain distinct.

The committed JSON starts with realistic fictional fixture data so a new checkout has a useful visual prototype. Running collection replaces it only through the normal collector output; tests use their own small HTML fixtures and never write to production data.

## Run locally

Python 3.12 and Node 22 are recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
npm run dev
```

Open `http://localhost:4173`. No JavaScript install step is needed because the frontend uses browser-native modules.

Run tests with:

```bash
npm test
```

Run a real collection manually with:

```bash
python -m collector
```

This reads `sources.txt` and updates `public/data/opportunities.json`. Collection is polite: requests identify the app, have bounded timeouts, follow normal redirects, run sequentially with a short delay, and do not attempt to bypass access controls.

## Add another source

1. Open `sources.txt`
2. Add the new URL on a new line
3. Commit the file
4. Run the collector or allow the scheduled job to run

Unknown sources use the generic collector. A site with unusual markup or a client-side catalogue may eventually need a dedicated adapter in `collector/adapters/`.

## GitHub Actions and Pages

`collect.yml` runs at approximately 05:23 UTC every day and also supports **Actions → Collect CPD opportunities → Run workflow**. It installs pinned dependencies, runs the tests, collects all sources and commits the generated JSON only when it changed. Repository **Actions: Read and write permissions** must permit the workflow's `contents: write` token.

`pages.yml` deploys `public/` after pushes to `main`, including automated data refreshes. In repository settings, choose **GitHub Actions** as the Pages source.

## Diagnose a broken source

1. Open the site's **sources checked** control to identify the failing provider and its last successful refresh.
2. In GitHub, open the latest **Collect CPD opportunities** workflow log. The JSON health entry also contains the bounded `error` message.
3. Fetch the provider page locally and compare its current markup with the relevant adapter and the fixtures in `tests/fixtures/`.
4. Add or update a small representative fixture and its unit test before changing extraction logic.
5. Run `npm test`, then `python -m collector`. A failed repair is safe: prior valid items remain available.

Some providers may intentionally restrict automated access or expose data only after interactive authentication. Record that failure and retain old data; do not work around CAPTCHAs, sign-in, or other access controls.
