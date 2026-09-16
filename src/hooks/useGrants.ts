"use client";

import { useEffect, useState } from "react";
import type { GrantOpportunity } from "@/lib/types";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export function useGrants() {
  const [grants, setGrants] = useState<GrantOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetch(`${basePath}/data/grants.json?v=${Date.now()}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Grant snapshot request failed: ${response.status}`);
        const data = await response.json();
        if (!Array.isArray(data)) throw new Error("Invalid grants snapshot");
        if (active) setGrants(data as GrantOpportunity[]);
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Grant data unavailable");
      } finally {
        if (active) setLoading(false);
      }
    }

    void load();
    return () => { active = false; };
  }, []);

  return { grants, loading, error };
}
