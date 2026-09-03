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
    let snapshotSource: BidSource | null = null;
    let liveSources: BidSource[] = [];

    const publish = () => {
      if (!active) return;
      const merged = new Map<string, BidSource>();
      if (snapshotSource) merged.set(snapshotSource.id, snapshotSource);
      for (const source of liveSources) merged.set(source.id, source);
      setSources(Array.from(merged.values()));
      setLoading(false);
    };

    void fetch(`${basePath}/data/egp-meta.json`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Source snapshot request failed: ${response.status}`);
        snapshotSource = (await response.json()) as BidSource;
        publish();
      })
      .catch(() => {
        if (liveSources.length) publish();
      });

    const unsubscribe = subscribeToSources(
      (items) => {
        liveSources = items;
        publish();
      },
      () => {
        if (!snapshotSource && active) setLoading(false);
      },
    );

    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  return { sources, loading };
}
