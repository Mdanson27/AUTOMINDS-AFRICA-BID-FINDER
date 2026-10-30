import { getFirestore } from "firebase/firestore";
import { app, auth, cleanFirebaseEnv } from "./firebaseClient";

export { app, auth };

// Browser-facing workspace data must use a Firestore Native-mode database because
// the Firebase Web SDK does not support MongoDB-compatible data access mode.
export const firestoreDatabaseId = cleanFirebaseEnv(process.env.NEXT_PUBLIC_FIRESTORE_DATABASE_ID) || "bidfinder-native";
export const db = getFirestore(app, firestoreDatabaseId);
