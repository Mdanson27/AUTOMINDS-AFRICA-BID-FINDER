// Firebase remains Bid Finder's identity provider during the Neon migration.
// Application data no longer initializes or depends on Cloud Firestore.
export { app, auth } from "./firebaseClient";
