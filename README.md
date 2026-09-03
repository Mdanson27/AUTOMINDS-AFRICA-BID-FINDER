# AutoMinds Africa Bid Finder

Uganda-focused procurement intelligence platform by **AutoMinds Africa**.

The project combines a Next.js procurement workspace with a separate Python collection engine. The first live source adapter is **eGP Uganda**. It normalizes public bid notices, deduplicates them by procurement reference, tracks changes such as deadline extensions, and writes the resulting records to the application data layer.

## Current stack

- Next.js + TypeScript
- Firebase Authentication
- Cloud Firestore for the MVP data layer
- strict Firestore rules and indexes
- responsive AutoMinds suite design
- Python + BeautifulSoup + HTTPX collector
- Firebase Admin for server-side collector writes
- GitHub Actions for scheduled collection and infrastructure deployment

## Security model

No real Firebase configuration values or service-account credentials are committed to source control.

Production web configuration is injected from GitHub Actions secrets during the Pages build. The server-side collector uses a separate `FIREBASE_SERVICE_ACCOUNT_JSON` Actions secret. Never place a service-account JSON file, private key, password, access token or unrestricted Google API key in this repository.

Firebase web configuration is delivered to browsers by design when the client SDK is used. It must therefore be protected with restricted Google API key settings, Firebase Authentication and strict Firestore rules rather than treated as a server credential.

See [`docs/SECURITY_AND_INGESTION.md`](docs/SECURITY_AND_INGESTION.md).

## Run locally

```bash
npm install
cp .env.example .env.local
# Fill .env.local with your local web configuration.
npm run dev
```

Open `http://localhost:3000`.

## eGP collector

From `collector/`:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.run_egp
```

`python -m src.run_egp` requires the `FIREBASE_SERVICE_ACCOUNT_JSON` environment variable. In production this value is supplied only through GitHub Actions secrets.

The collector records:

- normalized bid data
- source trail
- first/last seen timestamps
- deterministic canonical keys for duplicate prevention
- field-level change history
- deadline-change flags
- source health
- crawl-run statistics
- discovered organizations

## Automated workflows

- `Deploy to GitHub Pages` — builds the frontend using GitHub Actions secrets.
- `Deploy Firestore rules and indexes` — deploys the hardened database rules/indexes.
- `Collect eGP Uganda bids` — runs every two hours and can also be started manually.

## Portal routes

- `/login`
- `/dashboard`
- `/bids`
- `/bids/view?id=...`
- `/closing-soon`
- `/saved`
- `/organizations`
- `/sources`
- `/company`
- `/admin/source-monitor`
- `/admin/bids/new`
- `/settings`

## Data rule

The product is not padded with fake tenders. Search results come from records stored by real source collectors or explicit administrator testing utilities.

## Next sources

After eGP Uganda is stable:

1. GPP / PPDA
2. Daily Monitor
3. New Vision
4. direct procuring-entity websites
5. NGO and development-partner portals

## Commands

```bash
npm run dev
npm run typecheck
npm run lint
npm run build
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the broader application structure.
