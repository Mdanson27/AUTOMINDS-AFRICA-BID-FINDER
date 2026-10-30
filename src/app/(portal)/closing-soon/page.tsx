"use client";

import { useEffect, useState } from "react";
import { BidList } from "@/components/bids/BidList";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/components/auth/AuthProvider";
import { useBids } from "@/hooks/useBids";
import { daysUntil } from "@/lib/date";
import { subscribeUserPreferences, type UserPreferences } from "@/lib/userWorkspace";

export default function ClosingSoonPage() {
  const { user } = useAuth();
  const { bids, loading } = useBids();
  const [threshold, setThreshold] = useState<UserPreferences["closingSoonDays"]>(14);

  useEffect(() => {
    if (!user?.uid) return;
    return subscribeUserPreferences(user.uid, (preferences) => setThreshold(preferences.closingSoonDays));
  }, [user?.uid]);

  const closing = bids.filter((bid) => bid.status === "open" && daysUntil(bid.deadlineAt) >= 0 && daysUntil(bid.deadlineAt) <= threshold);
  return <div className="page-stack"><PageHeader eyebrow="Deadlines" title="Closing soon" description={`Open opportunities with deadlines in the next ${threshold} days. Change this window in Settings.`} /><BidList bids={closing} loading={loading} /></div>;
}
