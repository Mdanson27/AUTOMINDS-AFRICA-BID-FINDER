"use client";

import { useEffect, useState } from "react";
import type { GrantOpportunity } from "@/lib/types";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

let grantCache: GrantOpportunity[] | null = null;
let grantError = "";
let grantRequest: Promise<GrantOpportunity[]> | null = null;

async function loadGrants() {
  if (grantCache) return grantCache;
  if (grantRequest) return grantRequest;

  grantRequest = (async () => {
    const response = await fetch(`${basePath}/data/grants.json`, { cache: "default" });
    if (!response.ok) throw new Error(`Grant snapshot request failed: ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error("Invalid grants snapshot");
    grantCache = data as GrantOpportunity[];
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
    if (grantCache) {
      setGrants(grantCache);
      setLoading(false);
      return () => { active = false; };
    }

    void loadGrants()
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
