"use client";

import { useMemo, useState } from "react";
import { Building2, CalendarRange, ExternalLink, FileDown, Layers3, Search, TrendingUp } from "lucide-react";
import { useProcurementPlans } from "@/hooks/useProcurementPlans";

function amountNumber(value: string) {
  const parsed = Number((value || "").replace(/[^0-9.-]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function compactAmount(value: string) {
  const amount = amountNumber(value);
  if (!amount) return value ? "UGX " + value : "Not published";
  return "UGX " + new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(amount);
}

function fullAmount(value: string) {
  const amount = amountNumber(value);
  if (!amount) return value ? "UGX " + value : "Not published";
  return "UGX " + new Intl.NumberFormat("en-UG", {
    maximumFractionDigits: 2,
  }).format(amount);
}

export default function ProcurementPlansPage() {
  const { plans, loading, error } = useProcurementPlans();
  const [search, setSearch] = useState("");

  const needle = search.trim().toLowerCase();
  const filtered = useMemo(() => {
    if (!needle) return plans;
    return plans.filter((plan) =>
      [plan.name, plan.organization, plan.financialYear, ...plan.items.map((item) => item.category)]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [needle, plans]);

  const totalCategories = useMemo(() => plans.reduce((sum, plan) => sum + plan.items.length, 0), [plans]);
  const totalValue = useMemo(
    () => plans.reduce((sum, plan) => sum + amountNumber(plan.totalEstimatedAmountUGX), 0),
    [plans],
  );

  if (loading) {
    return (
      <div className="premium-loading">
        <div className="premium-loading-head" />
        <div className="premium-loading-toolbar" />
        <div className="premium-loading-grid"><div className="premium-loading-card" /><div className="premium-loading-card" /></div>
      </div>
    );
  }

  return (
    <div className="plans-page">
      <section className="plans-hero">
        <div>
          <span className="eyebrow">FORWARD PROCUREMENT INTELLIGENCE</span>
          <h1>Procurement plans</h1>
          <p>
            See what public entities intend to procure before the tender is advertised. These are current FY 2026/27
            plans from eGP and are kept separate from active bid invitations.
          </p>
        </div>
        <div className="plans-hero-chip"><CalendarRange size={17} /><span>Financial year</span><strong>2026 / 2027</strong></div>
      </section>

      <section className="plans-stats">
        <article><Building2 size={18} /><div><strong>{plans.length}</strong><span>organization plans</span></div></article>
        <article><Layers3 size={18} /><div><strong>{totalCategories}</strong><span>planned categories</span></div></article>
        <article><TrendingUp size={18} /><div><strong>{compactAmount(String(totalValue))}</strong><span>published estimated value</span></div></article>
      </section>

      <label className="plans-search">
        <Search size={18} />
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search organization, software, ICT, construction, stationery…" />
        <span>{filtered.length} plan{filtered.length === 1 ? "" : "s"}</span>
      </label>

      {error ? <div className="suite-empty"><strong>Plans temporarily unavailable</strong><span>{error}</span></div> : null}

      <div className="plans-list">
        {filtered.map((plan) => {
          const matchingItems = needle
            ? plan.items.filter((item) => item.category.toLowerCase().includes(needle))
            : plan.items;
          const previewItems = matchingItems.slice(0, 6);

          return (
            <article className="plan-card" key={plan.id}>
              <div className="plan-card-head">
                <div>
                  <span className="plan-fy">{plan.financialYear}</span>
                  <h2>{plan.organization}</h2>
                  <p>{plan.items.length} planned procurement categor{plan.items.length === 1 ? "y" : "ies"}</p>
                </div>
                <div className="plan-value">
                  <span>Published plan value</span>
                  <strong>{compactAmount(plan.totalEstimatedAmountUGX)}</strong>
                  <small>{plan.totalEstimatedAmountUGX ? fullAmount(plan.totalEstimatedAmountUGX) : "Total not shown"}</small>
                </div>
              </div>

              <div className="plan-item-list">
                {previewItems.length ? previewItems.map((item) => (
                  <div className="plan-item-row" key={plan.id + "-" + item.number}>
                    <span>{item.category}</span>
                    <strong>{fullAmount(item.estimatedAmountUGX)}</strong>
                  </div>
                )) : <div className="plan-no-match">No matching category was parsed inside this plan.</div>}
              </div>

              {matchingItems.length > 6 ? (
                <details className="plan-more">
                  <summary>View all {matchingItems.length} matching planned categories</summary>
                  <div>
                    {matchingItems.slice(6).map((item) => (
                      <div className="plan-item-row" key={plan.id + "-more-" + item.number}>
                        <span>{item.category}</span>
                        <strong>{fullAmount(item.estimatedAmountUGX)}</strong>
                      </div>
                    ))}
                  </div>
                </details>
              ) : null}

              <footer className="plan-actions">
                {plan.pdfUrl ? <a href={plan.pdfUrl} target="_blank" rel="noreferrer"><FileDown size={15} /> PDF</a> : null}
                {plan.excelUrl ? <a href={plan.excelUrl} target="_blank" rel="noreferrer"><FileDown size={15} /> Excel</a> : null}
                <a href={plan.sourceUrl} target="_blank" rel="noreferrer" className="plan-source-link">Open eGP plan <ExternalLink size={14} /></a>
              </footer>
            </article>
          );
        })}
      </div>

      {!filtered.length && !error ? (
        <div className="suite-empty"><Layers3 size={24} /><strong>No procurement plan matches this search</strong><span>Try a broader category or organization name.</span></div>
      ) : null}
    </div>
  );
}
