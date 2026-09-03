# Firebase setup

The web app is already configured for Firebase project `spring-ship-456117-u8`.

## 1. Authentication
In Firebase Console → Authentication → Sign-in method, enable **Email/Password**.
Create the first user account manually.

## 2. Firestore
Create a Firestore database, then deploy the repository rules and indexes:

```bash
npm install -g firebase-tools
firebase login
firebase use spring-ship-456117-u8
firebase deploy --only firestore:rules,firestore:indexes
```

## 3. Promote the first administrator
After the user signs in once, a `/users/{uid}` document is created with role `viewer`.
In Firestore Console change that user's `role` to `admin`.

Do not loosen the rules to make testing easier. The Firebase Web API key is not a server secret; authorization is enforced by Firebase Auth and Firestore rules.

## 4. Add the logo
Place the official logo at `public/logo.png`. The UI is already wired to `/logo.png` and shows a graceful fallback until the file exists.

## 5. Test
Run `npm run dev`, sign in, open **Source monitor**, then use **Add test bid** to verify Firestore writes and the live dashboard.
