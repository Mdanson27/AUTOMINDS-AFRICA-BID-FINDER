import { getFirestore } from "firebase/firestore";
import { app, auth, cleanFirebaseEnv } from "./firebaseClient";

export { app, auth };

// Keep Firestore initialization out of the global auth bootstrap. Pages that
// actually need procurement/user data import this module and pay the database
// bundle cost only then.
export const firestoreDatabaseId = cleanFirebaseEnv(process.env.NEXT_PUBLIC_FIRESTORE_DATABASE_ID) || "default";
export const db = getFirestore(app, firestoreDatabaseId);
