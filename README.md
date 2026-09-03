# AutoMinds Africa Bid Finder

Uganda-focused procurement intelligence platform by **AutoMinds Africa**.

The repository now contains a production-minded MVP foundation: Firebase Authentication, Firestore data access, a branded responsive portal, bid search, saved bids, deadline views, organization discovery, a source monitor, an admin testing utility, and an isolated Python collector workspace for the real Uganda source adapters.

## Brand asset

Add the official AutoMinds Africa logo as:

```text
public/logo.png
```

Every logo location already points to `/logo.png`. Until it is added, the interface falls back to an AutoMinds text mark instead of showing a broken image.

## Login mascot

The login screen includes **Bid Scout**, an original AutoMinds-colored procurement mascot:
- idle: “Looking for bids, I see.”
- email focus: the eyes follow the email interaction and the message changes
- password focus: the mascot covers its eyes
- sign-in: the mascot switches to scanning/loading mode

## Current stack

- Next.js + TypeScript
- Firebase Authentication
- Cloud Firestore (MVP/testing data layer)
- Firebase Analytics
- strict Firestore rules
- responsive AutoMinds blue/orange design system
- isolated Python collector scaffold

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

The Firebase web configuration supplied for `spring-ship-456117-u8` is already used as a fallback, so `.env.local` is optional for the initial test project.

## Firebase first-time setup

1. Enable **Email/Password** in Firebase Authentication.
2. Create Firestore for project `spring-ship-456117-u8`.
3. Deploy `firestore.rules` and `firestore.indexes.json`.
4. Create a Firebase Auth user and sign in once.
5. Change that user's Firestore `/users/{uid}.role` from `viewer` to `admin`.
6. Open `/admin/bids/new` and add one test bid to validate the complete Firestore → dashboard flow.

Full steps: [`docs/FIREBASE_SETUP.md`](docs/FIREBASE_SETUP.md).

## Portal routes

- `/login`
- `/dashboard`
- `/bids`
- `/bids/[id]`
- `/closing-soon`
- `/saved`
- `/organizations`
- `/sources`
- `/admin/source-monitor`
- `/admin/bids/new`
- `/settings`

The sidebar is collapsible on desktop, becomes a drawer on mobile, and sign-out is always available both in the sidebar and top bar.

## Data rule

The product should never be padded with fake tenders. Empty states are intentional until real Uganda bid records are ingested.

## Collector roadmap

The Python collector workspace is ready for source adapters. Start in this order:

1. eGP Uganda
2. GPP / PPDA
3. Daily Monitor
4. New Vision
5. direct procuring-entity sites
6. NGO/development organization portals

See [`docs/CODEX_NEXT.md`](docs/CODEX_NEXT.md) for the exact next implementation sequence.

## Commands

```bash
npm run dev
npm run typecheck
npm run lint
npm run build
```

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
