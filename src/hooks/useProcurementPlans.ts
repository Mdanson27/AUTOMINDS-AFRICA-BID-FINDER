"use client";

import { useEffect, useState } from "react";
import type { ProcurementPlan } from "@/lib/types";
import { SNAPSHOT_REFRESH_EVENT } from "@/hooks/useBids";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export function useProcurementPlans() {
  const [plans, setPlans] = useState<ProcurementPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const response = await fetch(basePath + "/data/plans.json?v=" + Date.now(), { cache: "no-store" });
        if (!response.ok) throw new Error("Plan snapshot request failed: " + response.status);
        const data = await response.json();
        if (!Array.isArray(data)) throw new Error("Invalid procurement-plan snapshot");
        if (!active) return;
        setPlans(data as ProcurementPlan[]);
        setError("");
      } catch {
        if (!active) return;
        setPlans([]);
        setError("Current procurement plans are temporarily unavailable.");
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    window.addEventListener(SNAPSHOT_REFRESH_EVENT, load);
    return () => {
      active = false;
      window.removeEventListener(SNAPSHOT_REFRESH_EVENT, load);
    };
  }, []);

  return { plans, loading, error };
}
