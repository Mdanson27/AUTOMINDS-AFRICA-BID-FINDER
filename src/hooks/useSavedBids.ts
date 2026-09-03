"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { setSavedBid, subscribeSavedBidIds } from "@/lib/firestore";

export function useSavedBids() {
  const { user } = useAuth(); const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  useEffect(() => { if (!user) { setSavedIds(new Set()); return; } return subscribeSavedBidIds(user.uid, setSavedIds); }, [user]);
  const toggle = useCallback(async (bidId: string) => { if (!user) return; await setSavedBid(user.uid, bidId, !savedIds.has(bidId)); }, [savedIds, user]);
  return { savedIds, toggle };
}
