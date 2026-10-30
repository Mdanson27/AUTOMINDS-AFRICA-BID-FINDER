import { getApp, getApps, initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

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

export const firebaseConfig = {
  apiKey: clean(process.env.NEXT_PUBLIC_FIREBASE_API_KEY) || "AIzaSyDc8Efx9Ad09jORlvqxuD83RhzE2y6mQXE",
  authDomain: clean(process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN) || "spring-ship-456117-u8.firebaseapp.com",
  projectId: clean(process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID) || "spring-ship-456117-u8",
  storageBucket: clean(process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET) || "spring-ship-456117-u8.firebasestorage.app",
  messagingSenderId: clean(process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID) || "462495347260",
  appId: clean(process.env.NEXT_PUBLIC_FIREBASE_APP_ID) || "1:462495347260:web:c40fc26d5822c1fd3c0939",
};

export const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);

export function cleanFirebaseEnv(value: string | undefined) {
  return clean(value);
}
