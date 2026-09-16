"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { ExternalLink, Gift, Linkedin, Search, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { useGrants } from "@/hooks/useGrants";

function deadlineLabel(value?: string) {
  if (!value) return "Deadline not provided";
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) return parsed.toLocaleDateString("en-UG", { day: "numeric", month: "short", year: "numeric" });
  return value;
}

export default function GrantsPage() {
  const { grants, loading, error } = useGrants();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("active");
  const deferredSearch = useDeferredValue(search);

  const filtered = useMemo(() => {
    const needle = deferredSearch.trim().toLowerCase();
    return grants.filter((grant) => {
      if (status === "active" && grant.status === "closed") return false;
      if (status !== "all" && status !== "active" && grant.status !== status) return false;
      if (!needle) return true;
      const text = [grant.title, grant.funder, grant.opportunityNumber, grant.summary, grant.geography, grant.eligibility, grant.sourceName].join(" ").toLowerCase();
      return text.includes(needle);
    });
  }, [deferredSearch, grants, status]);

  return (
    <div className="page-stack suite-find-page">
      <PageHeader
        eyebrow="Funding discovery"
        title="Grants"
        description="Real funding opportunities from grant-making organizations and verified public funding sources. Procurement tenders are intentionally excluded from this section."
      />

      <section className="panel suite-search-console">
        <label className="suite-main-search">
          <Search size={21} />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search grants by funder, programme, geography or opportunity number…" />
          <span>{filtered.length} result{filtered.length === 1 ? "" : "s"}</span>
        </label>
        <div className="suite-filter-bar">
          <button className={status === "active" ? "button primary" : "button secondary"} onClick={() => setStatus("active")}>Active grants</button>
          <button className={status === "forecasted" ? "button primary" : "button secondary"} onClick={() => setStatus("forecasted")}>Forecasted</button>
          <button className={status === "all" ? "button primary" : "button secondary"} onClick={() => setStatus("all")}>All</button>
        </div>
      </section>

      <section className="panel">
        <div className="suite-results-head">
          <div><span className="eyebrow">GRANT SOURCES</span><h2>Funding source network</h2></div>
        </div>
        <div className="suite-advanced-grid">
          <div><strong>Grants.gov</strong><p>Automated public API collection for Uganda/Africa-relevant grant and cooperative-agreement opportunities.</p></div>
          <div><strong>LinkedIn public discovery</strong><p>Public grant posts are a discovery channel only. They must be verified against the funder or application page before appearing as a trusted grant record.</p><a className="button secondary" href="https://www.linkedin.com/search/results/content/?keywords=Uganda%20grant%20funding%20opportunity" target="_blank" rel="noreferrer"><Linkedin size={15} /> Search LinkedIn</a></div>
          <div><strong>Verification rule</strong><p><ShieldCheck size={15} style={{ verticalAlign: "text-bottom" }} /> No procurement notice is converted into a grant. A grant must originate from a funding source or a verified funding call.</p></div>
        </div>
      </section>

      <section className="suite-results-section">
        <div className="suite-results-head"><div><span className="eyebrow">FUNDING OPPORTUNITIES</span><h2>Real grants</h2></div></div>
        {loading && <div className="suite-empty"><strong>Loading grants…</strong><span>Checking the latest funding snapshot.</span></div>}
        {!loading && error && <div className="suite-empty"><strong>Grant data is temporarily unavailable</strong><span>{error}</span></div>}
        {!loading && !error && filtered.length === 0 && <div className="suite-empty"><strong>No matching grants found</strong><span>Try another keyword or wait for the next source refresh.</span></div>}
        {!loading && !error && filtered.map((grant) => (
          <article className="panel" key={grant.id} style={{ marginBottom: 14 }}>
            <div className="suite-results-head">
              <div>
                <span className="eyebrow"><Gift size={13} /> {grant.status.toUpperCase()} · {grant.sourceName}</span>
                <h2 style={{ marginTop: 8 }}>{grant.title}</h2>
                <p><strong>{grant.funder || "Funder not provided"}</strong>{grant.geography ? ` · ${grant.geography}` : ""}</p>
              </div>
              <a className="button primary" href={grant.applicationUrl || grant.sourceUrl} target="_blank" rel="noreferrer">View grant <ExternalLink size={15} /></a>
            </div>
            <div className="suite-advanced-grid">
              <div><span className="eyebrow">Opportunity number</span><p>{grant.opportunityNumber || "Not provided"}</p></div>
              <div><span className="eyebrow">Deadline</span><p>{deadlineLabel(grant.deadlineAt)}</p></div>
              <div><span className="eyebrow">Funding</span><p>{grant.fundingAmount || "See source"}</p></div>
              <div><span className="eyebrow">Eligibility</span><p>{grant.eligibility || "See source"}</p></div>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
