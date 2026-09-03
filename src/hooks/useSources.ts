"use client";

import { useEffect, useState } from "react";
import { subscribeToSources } from "@/lib/firestore";
import type { BidSource } from "@/lib/types";

export function useSources() {
  const [sources, setSources] = useState<BidSource[]>([]); const [loading, setLoading] = useState(true);
  useEffect(() => subscribeToSources((items) => { setSources(items); setLoading(false); }, () => setLoading(false)), []);
  return { sources, loading };
}
