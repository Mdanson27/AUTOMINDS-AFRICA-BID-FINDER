"use client";

import { useEffect, useState } from "react";
import { neonSelect } from "@/lib/neonApi";
import type { ProcurementPlan } from "@/lib/types";
import { SNAPSHOT_REFRESH_EVENT } from "@/hooks/useBids";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

let plansCache: ProcurementPlan[] | null = null;
let plansError = "";
let plansRequest: Promise<ProcurementPlan[]> | null = null;

async function loadSnapshot(force = false) {
  const suffix = force ? `?v=${Date.now()}` : "";
  const response = await fetch(`${basePath}/data/plans.json${suffix}`, {
    cache: force ? "no-store" : "default",
  });
  if (!response.ok) throw new Error(`Plan snapshot request failed: ${response.status}`);
  const data = await response.json();
  if (!Array.isArray(data)) throw new Error("Invalid procurement-plan snapshot");
  return data as ProcurementPlan[];
}

async function fetchPlans(force = false) {
  if (plansCache && !force) return plansCache;
  if (plansRequest && !force) return plansRequest;

  const task = (async () => {
    try {
      const rows = await neonSelect<{ raw_record?: ProcurementPlan }>(
        "procurement_plans",
        "select=raw_record&order=collected_at.desc.nullslast&limit=1000",
      );
      const items = rows.flatMap((row) => row.raw_record ? [row.raw_record] : []);
      if (items.length) {
        plansCache = items;
        plansError = "";
        return plansCache;
      }
    } catch {
      // Static export remains the resilience fallback during API/network outages.
    }

    plansCache = await loadSnapshot(force);
    plansError = "";
    return plansCache;
  })();

  plansRequest = task;
  try {
    return await task;
  } finally {
    if (plansRequest === task) plansRequest = null;
  }
}

export function useProcurementPlans() {
  const [plans, setPlans] = useState<ProcurementPlan[]>(() => plansCache || []);
  const [loading, setLoading] = useState(() => plansCache === null);
  const [error, setError] = useState(() => plansError);

  useEffect(() => {
    let active = true;

    const load = async (force = false) => {
      if (!plansCache) setLoading(true);
      try {
        const items = await fetchPlans(force);
        if (!active) return;
        setPlans(items);
        setError("");
      } catch {
        plansError = "Current procurement plans are temporarily unavailable.";
        if (!active) return;
        setError(plansError);
        if (!plansCache) setPlans([]);
      } finally {
        if (active) setLoading(false);
      }
    };

    void load(false);
    const refresh = () => void load(true);
    window.addEventListener(SNAPSHOT_REFRESH_EVENT, refresh);
    return () => {
      active = false;
      window.removeEventListener(SNAPSHOT_REFRESH_EVENT, refresh);
    };
  }, []);

  return { plans, loading, error };
}
