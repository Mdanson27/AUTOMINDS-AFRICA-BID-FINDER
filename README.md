<p align="center">
  <img src="assets/github-banner.svg" alt="AutoMinds Bid Finder — Procurement Intelligence" width="100%" />
</p>

<p align="center">
  <strong>Uganda-focused procurement intelligence by AutoMinds Africa.</strong><br/>
  Turning fragmented procurement notices into a verified, searchable operating layer.
</p>

<p align="center">
  <code>Next.js</code> · <code>TypeScript</code> · <code>Firebase Auth</code> · <code>Neon Postgres</code> · <code>Python</code> · <code>GitHub Actions</code>
</p>

---

## What it does

Bid Finder combines a Next.js procurement workspace with a separate Python collection engine monitoring a **30-source procurement network**. Collectors normalize public notices, verify actionable deadlines, reject expired/terminal opportunities from live surfaces, deduplicate repeated notices, preserve source evidence and track procurement changes.

## Production architecture

- Next.js + TypeScript frontend deployed on GitHub Pages
- Firebase Authentication for existing user identity and sign-in
- Neon Postgres as the application database
- Neon Data API for browser-safe HTTPS access
- PostgreSQL row-level security (RLS) using Firebase JWT identity
- User-owned company profiles, preferences, saved bids, saved searches and notifications
- Canonical procurement tables for bids, source evidence, organizations, plans, grants and crawl history
- Python + BeautifulSoup + HTTPX + Playwright collectors
- GitHub Actions for scheduled 30-source collection, validation, Neon synchronization and Pages deployment
- Static JSON snapshots retained as a fast resilience fallback, not as the primary application database

## Security model

The browser never receives a Postgres password or Neon connection string. Firebase ID tokens are presented to the Neon Data API, which maps authenticated requests to PostgreSQL RLS policies.

User-owned rows are restricted to the Firebase UID in the JWT. Normal users cannot promote their own application role. Procurement-table writes are restricted to the dedicated `bidfinder-collector` identity or an application administrator.

The scheduled collector uses the existing `FIREBASE_SERVICE_ACCOUNT_JSON` GitHub Actions secret only to mint a short-lived Firebase token for `bidfinder-collector`; it then writes through the same Data API/RLS boundary as the application. Never commit service-account JSON, private keys, passwords or access tokens.

## Database model

Core Neon tables include:

- `app_users`
- `user_preferences`
- `companies`
- `saved_bids`
- `saved_searches`
- `notifications`
- `bids`
- `bid_sources`
- `bid_changes`
- `sources`
- `organizations`
- `crawl_runs`
- `procurement_plans`
- `grants`
- `bid_match_scores`

The `bids` RLS read policy independently excludes expired and terminal opportunities from normal authenticated users.

## Run locally

```bash
npm install
cp .env.example .env.local
# Fill in Firebase web configuration and NEXT_PUBLIC_NEON_DATA_API_URL.
npm run dev
```

Open `http://localhost:3000`.

## Collector

From the repository root:

```bash
python -m pip install -r collector/requirements.txt
python -m unittest discover -s collector/tests -v
python -m collector.src.export_30_source_snapshot
python -m collector.src.postprocess_snapshot
python -m collector.src.export_grants
```

Production deployment additionally runs:

```bash
python -m collector.src.neon_sync
```

The Neon sync requires `FIREBASE_SERVICE_ACCOUNT_JSON`, `NEXT_PUBLIC_FIREBASE_API_KEY` and `NEON_DATA_API_URL` in the deployment environment.

## Automated workflow

`Deploy to GitHub Pages` performs the production cycle:

1. load persistent procurement history;
2. scan the 30-source network;
3. validate and normalize live opportunities;
4. merge persistence/change history;
5. export grants and procurement plans;
6. synchronize canonical data to Neon;
7. typecheck, lint and build the Next.js static site;
8. deploy the Pages artifact.

## Portal routes

- `/login`
- `/dashboard`
- `/bids`
- `/bids/view?id=...`
- `/grants`
- `/plans`
- `/papers`
- `/closing-soon`
- `/saved`
- `/organizations`
- `/sources`
- `/company`
- `/admin/source-monitor`
- `/admin/bids/new`
- `/settings`

## Data rules

- No fake opportunities are used to pad the product.
- No explicit/credible deadline means no live tender.
- Passed deadlines do not appear in normal live results.
- Terminal states such as closed, evaluation, awarded and cancelled are excluded from the live opportunity surface.
- Repeated notices from several publishers should resolve to one canonical opportunity with source evidence preserved.

## Commands

```bash
npm run dev
npm run typecheck
npm run lint
npm run build
```

The production Neon schema is versioned in [`neon/schema.sql`](neon/schema.sql).

---

<p align="center"><strong>AutoMinds Africa</strong> · Building intelligence around real business workflows.</p>
