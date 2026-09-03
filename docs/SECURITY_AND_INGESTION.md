# Security and eGP ingestion setup

## Important: rotate the key that was committed previously

A Google API key was previously committed to repository history and GitHub correctly raised a secret-scanning alert.

Removing it from the current files does **not** erase it from Git history. Treat the old key as exposed:

1. In Google Cloud Console, open **APIs & Services → Credentials** for the Firebase/Google Cloud project.
2. Create a replacement browser key or rotate the exposed key.
3. Restrict the replacement key to the Firebase/Google APIs the web app actually uses.
4. Add HTTP referrer restrictions for the production domains, including the GitHub Pages domain while it is used.
5. Update the GitHub Actions secret `NEXT_PUBLIC_FIREBASE_API_KEY` with the replacement value.
6. After the application is confirmed working with the replacement, revoke/delete the exposed key.
7. Close the GitHub secret-scanning alert as revoked/remediated.

Firebase web configuration is visible in browser JavaScript by design. The goal is to keep it out of source control and restrict the key. **Never** expose service-account private keys or other server credentials.

## GitHub Actions secrets required for the frontend

Repository → **Settings → Secrets and variables → Actions → New repository secret**

Create:

- `NEXT_PUBLIC_FIREBASE_API_KEY`
- `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
- `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
- `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`
- `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID`
- `NEXT_PUBLIC_FIREBASE_APP_ID`
- `NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID`

The Pages workflow validates the required values before it builds.

## Server-side collector credential

The eGP collector does not use the browser credential for writes. It uses a Firebase Admin service account stored only as a GitHub Actions secret.

Create a dedicated service account for the collector where possible, with only the permissions required to write the Firestore collections used by Bid Finder.

Then store the **entire JSON document** as one repository Actions secret named:

- `FIREBASE_SERVICE_ACCOUNT_JSON`

Do not commit the JSON file. Do not paste it into issues, pull requests, logs, screenshots, chat messages or source code.

## Firestore deployment

After `FIREBASE_SERVICE_ACCOUNT_JSON` is configured, run the workflow:

**Actions → Deploy Firestore rules and indexes → Run workflow**

It deploys:

- `firestore.rules`
- `firestore.indexes.json`

The same workflow runs automatically when those files change on `main`.

## First live eGP ingestion

After the credential and Firestore rules are ready:

1. Open **Actions → Collect eGP Uganda bids**.
2. Choose **Run workflow**.
3. The collector fetches the public eGP bid-notices page.
4. It refuses to write if the parser unexpectedly returns zero notices.
5. It normalizes the records and writes them to `bids`.
6. It creates/updates `sources/egp-uganda` and a `crawlRuns` record.
7. The signed-in Bid Finder frontend receives the new records through its existing live Firestore subscription.

The workflow then runs every two hours.

## Duplicate prevention

The collector creates a canonical key from the procurement reference when one exists. A SHA-256 digest of that canonical key becomes the stable Firestore bid document ID.

This means the same procurement reference found again is updated instead of inserted as another bid. Later source adapters can use the same canonical-key strategy so a bid found on eGP, a newspaper and an entity website can converge on the same record.

## Deadline-change detection

Every ingestion compares important fields with the existing record. When a value changes, a document is added under:

`bids/{bidId}/changes/{changeId}`

For deadline changes the parent bid also receives:

- `deadlineChanged: true`
- `deadlineChangedAt`

The Find Bids UI displays a deadline-updated warning on those opportunities.

## Collections used

Core ingestion collections:

- `bids`
- `bids/{bidId}/sources`
- `bids/{bidId}/changes`
- `sources`
- `crawlRuns`
- `organizations`

User workspace collections:

- `users`
- `savedBids`
- `savedSearches`
- `userPreferences`
- `companyProfiles`
- `notifications`

## What is and is not public

The GitHub repository must contain no real server secrets.

The browser bundle will necessarily contain the Firebase **web** configuration while the app uses the Firebase client SDK. That configuration does not grant Firestore access on its own. Access is enforced by Firebase Authentication, Firestore Security Rules and the restrictions on the browser API key.

The service-account credential used by the collector is a true server secret and must remain only in GitHub Actions secrets or another server-side secret manager.
