import { auth } from "./firebaseClient";

const DEFAULT_NEON_DATA_API_URL = "https://ep-frosty-bar-b5zf1qa1.apirest.c-7.us-east-2.aws.neon.tech/bidfinder/rest/v1";

export const neonDataApiUrl = (process.env.NEXT_PUBLIC_NEON_DATA_API_URL || DEFAULT_NEON_DATA_API_URL).replace(/\/$/, "");

function messageFromResponse(status: number, body: string) {
  try {
    const parsed = JSON.parse(body) as { message?: string; hint?: string; details?: string };
    return parsed.message || parsed.details || parsed.hint || `Neon request failed (${status})`;
  } catch {
    return body || `Neon request failed (${status})`;
  }
}

async function idToken(forceRefresh = false) {
  const user = auth.currentUser;
  if (!user) throw new Error("Authentication is required.");
  return user.getIdToken(forceRefresh);
}

export async function neonRequest<T>(path: string, init: RequestInit = {}, retryAuth = true): Promise<T> {
  const token = await idToken(false);
  const response = await fetch(`${neonDataApiUrl}/${path.replace(/^\//, "")}`, {
    ...init,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers || {}),
    },
  });

  if (response.status === 401 && retryAuth) {
    const fresh = await idToken(true);
    const retried = await fetch(`${neonDataApiUrl}/${path.replace(/^\//, "")}`, {
      ...init,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${fresh}`,
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(init.headers || {}),
      },
    });
    const retriedText = await retried.text();
    if (!retried.ok) throw new Error(messageFromResponse(retried.status, retriedText));
    return (retriedText ? JSON.parse(retriedText) : undefined) as T;
  }

  const text = await response.text();
  if (!response.ok) throw new Error(messageFromResponse(response.status, text));
  return (text ? JSON.parse(text) : undefined) as T;
}

export function eq(value: string | number | boolean) {
  return `eq.${encodeURIComponent(String(value))}`;
}

export async function neonSelect<T>(table: string, query = "") {
  return neonRequest<T[]>(`${table}${query ? `?${query}` : ""}`, { cache: "no-store" });
}

export async function neonUpsert<T extends Record<string, unknown>>(
  table: string,
  rows: T | T[],
  conflict: string,
) {
  return neonRequest<T[]>(`${table}?on_conflict=${encodeURIComponent(conflict)}`, {
    method: "POST",
    headers: { Prefer: "resolution=merge-duplicates,return=representation" },
    body: JSON.stringify(rows),
  });
}

export async function neonInsert<T extends Record<string, unknown>>(table: string, rows: T | T[]) {
  return neonRequest<T[]>(table, {
    method: "POST",
    headers: { Prefer: "return=representation" },
    body: JSON.stringify(rows),
  });
}

export async function neonPatch<T extends Record<string, unknown>>(table: string, filters: string, values: T) {
  return neonRequest<T[]>(`${table}?${filters}`, {
    method: "PATCH",
    headers: { Prefer: "return=representation" },
    body: JSON.stringify(values),
  });
}

export async function neonDelete(table: string, filters: string) {
  await neonRequest<void>(`${table}?${filters}`, {
    method: "DELETE",
    headers: { Prefer: "return=minimal" },
  });
}

export async function ensureNeonUser() {
  const user = auth.currentUser;
  if (!user) throw new Error("Authentication is required.");
  const now = new Date().toISOString();
  const [record] = await neonUpsert("app_users", {
    firebase_uid: user.uid,
    email: user.email || "",
    display_name: user.displayName || "",
    updated_at: now,
  }, "firebase_uid");
  return record;
}
