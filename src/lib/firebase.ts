import { getApp, getApps, initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

/**
 * Browser configuration is intentionally resilient to GitHub environment
 * variables that were entered with surrounding quotes/whitespace. The values
 * below are public web-app identifiers (not service-account credentials), so a
 * safe fallback keeps the deployed client bootable while still allowing later
 * overrides from the build environment.
 */
function clean(value: string | undefined): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1).trim();
  }
  return trimmed;
}

const firebaseConfig = {
  apiKey: clean(process.env.NEXT_PUBLIC_FIREBASE_API_KEY) || "AIzaSyDc8Efx9Ad09jORlvqxuD83RhzE2y6mQXE",
  authDomain: clean(process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN) || "spring-ship-456117-u8.firebaseapp.com",
  projectId: clean(process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID) || "spring-ship-456117-u8",
  storageBucket: clean(process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET) || "spring-ship-456117-u8.firebasestorage.app",
  messagingSenderId: clean(process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID) || "462495347260",
  appId: clean(process.env.NEXT_PUBLIC_FIREBASE_APP_ID) || "1:462495347260:web:c40fc26d5822c1fd3c0939",
};

export const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);

// This project currently points the Bid Finder workspace at the named database
// used during the MVP. The database identifier remains configurable so we can
// switch to the final production data store without touching UI code.
export const firestoreDatabaseId = clean(process.env.NEXT_PUBLIC_FIRESTORE_DATABASE_ID) || "default";
export const db = getFirestore(app, firestoreDatabaseId);
