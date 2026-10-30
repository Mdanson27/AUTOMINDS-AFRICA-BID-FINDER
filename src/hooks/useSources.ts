"use client";

import { useEffect, useState } from "react";
import { subscribeToSources } from "@/lib/firestore";
import type { BidSource } from "@/lib/types";
import { SNAPSHOT_REFRESH_EVENT } from "@/hooks/useBids";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

let sourceCache: BidSource[] | null = null;
let sourceSnapshotRequest: Promise<BidSource[]> | null = null;
let liveSources: BidSource[] = [];
let liveStarted = false;
const sourceListeners = new Set<(items: BidSource[]) => void>();

function mergeSources(snapshotSources: BidSource[], live: BidSource[]) {
  const merged = new Map<string, BidSource>();
  for (const source of snapshotSources) merged.set(source.id, source);
  for (const source of live) merged.set(source.id, source);
  return Array.from(merged.values());
}

function publishSources() {
  const items = mergeSources(sourceCache || [], liveSources);
  for (const listener of sourceListeners) listener(items);
}

async function fetchSourceSnapshot(force = false) {
  if (sourceCache && !force) return sourceCache;
  if (sourceSnapshotRequest && !force) return sourceSnapshotRequest;

  const suffix = force ? `?v=${Date.now()}` : "";
  const options: RequestInit = { cache: force ? "no-store" : "default" };
  const task = (async () => {
    try {
      const response = await fetch(`${basePath}/data/sources.json${suffix}`, options);
      if (!response.ok) throw new Error(`Source snapshot request failed: ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error("Invalid source snapshot");
      sourceCache = data as BidSource[];
    } catch {
      try {
        const response = await fetch(`${basePath}/data/egp-meta.json${suffix}`, options);
        if (!response.ok) throw new Error(`Fallback source snapshot request failed: ${response.status}`);
        sourceCache = [(await response.json()) as BidSource];
      } catch {
        sourceCache = sourceCache || [];
      }
    }
    publishSources();
    return sourceCache;
  })();

  sourceSnapshotRequest = task;
  try {
    return await task;
  } finally {
    if (sourceSnapshotRequest === task) sourceSnapshotRequest = null;
  }
}

function startLiveSources() {
  if (liveStarted || typeof window === "undefined") return;
  liveStarted = true;
  subscribeToSources(
    (items) => {
      liveSources = items;
      publishSources();
    },
    () => publishSources(),
  );
}

export function useSources() {
  const [sources, setSources] = useState<BidSource[]>(() => mergeSources(sourceCache || [], liveSources));
  const [loading, setLoading] = useState(() => sourceCache === null && liveSources.length === 0);

  useEffect(() => {
    let active = true;
    const listener = (items: BidSource[]) => {
      if (!active) return;
      setSources(items);
      setLoading(false);
    };

    sourceListeners.add(listener);
    startLiveSources();
    if (sourceCache) listener(mergeSources(sourceCache, liveSources));
    else void fetchSourceSnapshot(false).finally(() => {
      if (active) setLoading(false);
    });

    const refresh = () => void fetchSourceSnapshot(true);
    window.addEventListener(SNAPSHOT_REFRESH_EVENT, refresh);

    return () => {
      active = false;
      sourceListeners.delete(listener);
      window.removeEventListener(SNAPSHOT_REFRESH_EVENT, refresh);
    };
  }, []);

  return { sources, loading };
}
