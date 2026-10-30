// Compatibility module retained so existing imports keep working during the
// Firestore -> Neon migration. All runtime persistence now lives in Neon.
export * from "./neonStore";
