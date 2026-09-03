"use client";

import { useEffect, useState } from "react";
import { subscribeToBids } from "@/lib/firestore";
import type { Bid } from "@/lib/types";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

function mergeBids(snapshotBids: Bid[], liveBids: Bid[]) {
  const merged = new Map<string, Bid>();
  for (const bid of snapshotBids) merged.set(bid.id, bid);
  for (const bid of liveBids) merged.set(bid.id, bid);
  return Array.from(merged.values());
}

export function useBids() {
  const [bids, setBids] = useState<Bid[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let snapshotBids: Bid[] = [];
    let liveBids: Bid[] = [];

    const publish = () => {
      if (!active) return;
      const merged = mergeBids(snapshotBids, liveBids);
      setBids(merged);
      if (merged.length) setError("");
      setLoading(false);
    };

    void fetch(`${basePath}/data/egp-bids.json`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Snapshot request failed: ${response.status}`);
        const data = await response.json();
        if (!Array.isArray(data)) throw new Error("Invalid opportunity snapshot");
        snapshotBids = data as Bid[];
        publish();
      })
      .catch(() => {
        if (liveBids.length) publish();
      });

    const unsubscribe = subscribeToBids(
      (items) => {
        liveBids = items;
        publish();
      },
      (reason) => {
        if (!snapshotBids.length && active) {
          setError(reason);
          setLoading(false);
        }
      },
    );

    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  return { bids, loading, error };
}
