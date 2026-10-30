"use client";

import { useEffect, useState } from "react";
import type { ProcurementPlan } from "@/lib/types";
import { SNAPSHOT_REFRESH_EVENT } from "@/hooks/useBids";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

let plansCache: ProcurementPlan[] | null = null;
let plansError = "";
let plansRequest: Promise<ProcurementPlan[]> | null = null;

async function fetchPlans(force = false) {
  if (plansCache && !force) return plansCache;
  if (plansRequest && !force) return plansRequest;

  const suffix = force ? `?v=${Date.now()}` : "";
  const task = (async () => {
    const response = await fetch(`${basePath}/data/plans.json${suffix}`, {
      cache: force ? "no-store" : "default",
    });
    if (!response.ok) throw new Error(`Plan snapshot request failed: ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error("Invalid procurement-plan snapshot");
    plansCache = data as ProcurementPlan[];
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
