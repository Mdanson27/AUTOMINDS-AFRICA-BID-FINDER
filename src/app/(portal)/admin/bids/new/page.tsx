"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Save } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { addManualBid } from "@/lib/firestore";

export default function NewBidPage() {
  const { profile } = useAuth();
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  if (profile?.role !== "admin") return <EmptyState title="Admin access required" description="Only administrators can write normalized bid records." />;

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setMessage("");
    const data = new FormData(event.currentTarget);
    try {
      const id = await addManualBid({
        title: String(data.get("title") || ""), organization: String(data.get("organization") || ""),
        referenceNumber: String(data.get("referenceNumber") || ""), description: String(data.get("description") || ""),
        category: String(data.get("category") || ""), procurementType: String(data.get("procurementType") || ""),
        publishedAt: String(data.get("publishedAt") || ""), deadlineAt: String(data.get("deadlineAt") || ""),
        sourceName: String(data.get("sourceName") || "Manual test"), sourceUrl: String(data.get("sourceUrl") || ""),
      });
      router.push(`/bids/view?id=${encodeURIComponent(id)}`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not save bid."); setSaving(false); }
  }

  return (
    <div className="page-stack narrow-page">
      <PageHeader eyebrow="Testing utility" title="Add a manual test bid" description="Use this only to validate access, normalized bid fields and dashboard behavior before automated collectors are connected." />
      <form className="panel form-grid" onSubmit={submit}>
        <label className="field full"><span>Bid title *</span><input name="title" required placeholder="e.g. Supply and installation of network equipment" /></label>
        <label className="field"><span>Organization *</span><input name="organization" required /></label>
        <label className="field"><span>Reference number</span><input name="referenceNumber" /></label>
        <label className="field"><span>Category</span><input name="category" placeholder="ICT" /></label>
        <label className="field"><span>Procurement type</span><input name="procurementType" placeholder="Supplies / Services / Works" /></label>
        <label className="field"><span>Published date</span><input type="date" name="publishedAt" /></label>
        <label className="field"><span>Deadline *</span><input type="datetime-local" name="deadlineAt" required /></label>
        <label className="field"><span>Source name</span><input name="sourceName" placeholder="eGP Uganda" /></label>
        <label className="field"><span>Source URL</span><input type="url" name="sourceUrl" placeholder="https://…" /></label>
        <label className="field full"><span>Description</span><textarea name="description" rows={6} /></label>
        {message && <p className="form-error full">{message}</p>}
        <div className="full form-actions"><button className="button primary" disabled={saving}><Save size={16} /> {saving ? "Saving…" : "Save bid"}</button></div>
      </form>
    </div>
  );
}
