"use client";

import { useEffect, useState } from "react";
import { subscribeToSources } from "@/lib/firestore";
import type { BidSource } from "@/lib/types";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export function useSources() {
  const [sources, setSources] = useState<BidSource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    let snapshotSources: BidSource[] = [];
    let liveSources: BidSource[] = [];

    const publish = () => {
      if (!active) return;
      const merged = new Map<string, BidSource>();
      for (const source of snapshotSources) merged.set(source.id, source);
      for (const source of liveSources) merged.set(source.id, source);
      setSources(Array.from(merged.values()));
      setLoading(false);
    };

    void fetch(`${basePath}/data/sources.json`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Source snapshot request failed: ${response.status}`);
        const data = await response.json();
        if (!Array.isArray(data)) throw new Error("Invalid source snapshot");
        snapshotSources = data as BidSource[];
        publish();
      })
      .catch(() => {
        void fetch(`${basePath}/data/egp-meta.json`, { cache: "no-store" })
          .then(async (response) => {
            if (!response.ok) throw new Error(`Fallback source snapshot request failed: ${response.status}`);
            snapshotSources = [(await response.json()) as BidSource];
            publish();
          })
          .catch(() => {
            if (liveSources.length) publish();
          });
      });

    const unsubscribe = subscribeToSources(
      (items) => {
        liveSources = items;
        publish();
      },
      () => {
        if (!snapshotSources.length && active) setLoading(false);
      },
    );

    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  return { sources, loading };
}
