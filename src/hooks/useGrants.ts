"use client";

import { useEffect, useState } from "react";
import { neonSelect } from "@/lib/neonApi";
import type { GrantOpportunity } from "@/lib/types";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

let grantCache: GrantOpportunity[] | null = null;
let grantError = "";
let grantRequest: Promise<GrantOpportunity[]> | null = null;

async function loadSnapshot() {
  const response = await fetch(`${basePath}/data/grants.json`, { cache: "default" });
  if (!response.ok) throw new Error(`Grant snapshot request failed: ${response.status}`);
  const data = await response.json();
  if (!Array.isArray(data)) throw new Error("Invalid grants snapshot");
  return data as GrantOpportunity[];
}

async function loadGrants(force = false) {
  if (grantCache && !force) return grantCache;
  if (grantRequest && !force) return grantRequest;

  grantRequest = (async () => {
    try {
      const rows = await neonSelect<{ raw_record?: GrantOpportunity }>(
        "grants",
        "select=raw_record&order=deadline_at.asc&limit=1000",
      );
      const items = rows.flatMap((row) => row.raw_record ? [row.raw_record] : []);
      if (items.length) {
        grantCache = items;
        grantError = "";
        return grantCache;
      }
    } catch {
      // Static export remains a fast resilience fallback.
    }

    grantCache = await loadSnapshot();
    grantError = "";
    return grantCache;
  })();

  try {
    return await grantRequest;
  } finally {
    grantRequest = null;
  }
}

export function useGrants() {
  const [grants, setGrants] = useState<GrantOpportunity[]>(() => grantCache || []);
  const [loading, setLoading] = useState(() => grantCache === null);
  const [error, setError] = useState(() => grantError);

  useEffect(() => {
    let active = true;
    void loadGrants(false)
      .then((items) => {
        if (!active) return;
        setGrants(items);
        setError("");
      })
      .catch((reason) => {
        grantError = reason instanceof Error ? reason.message : "Grant data unavailable";
        if (active) setError(grantError);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, []);

  return { grants, loading, error };
}
