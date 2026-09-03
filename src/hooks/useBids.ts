"use client";

import { useEffect, useState } from "react";
import { subscribeToBids } from "@/lib/firestore";
import type { Bid } from "@/lib/types";

export function useBids() {
  const [bids, setBids] = useState<Bid[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => subscribeToBids((items) => { setBids(items); setLoading(false); }, (reason) => { setError(reason); setLoading(false); }), []);
  return { bids, loading, error };
}
