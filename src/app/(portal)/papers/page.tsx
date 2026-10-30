"use client";

import { ExternalLink } from "lucide-react";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const papers = [
  {
    name: "Daily Monitor",
    href: "https://www.monitor.co.ug/uganda/jobs/tenders",
    logo: `${basePath}/dailymonitor.png`,
    theme: "monitor",
  },
  {
    name: "New Vision",
    href: "https://www.newvision.co.ug/opportunities/tenders",
    logo: `${basePath}/newvision.png`,
    theme: "newvision",
  },
] as const;

export default function PapersPage() {
  return (
    <div className="newspaper-page">
      <header className="newspaper-heading">
        <span className="eyebrow">CURRENT PAPERS</span>
        <h1>Newspaper tender pages</h1>
        <p>Select a newspaper to open its latest tender and procurement notices.</p>
      </header>

      <section className="newspaper-grid" aria-label="Uganda newspaper tender pages">
        {papers.map((paper) => (
          <article className={`newspaper-card newspaper-card-${paper.theme}`} key={paper.name}>
            <div className="brand-line" aria-hidden="true" />

            <div className="newspaper-logo-wrap">
              <img className={`newspaper-logo newspaper-logo-${paper.theme}`} src={paper.logo} alt={`${paper.name} logo`} />
            </div>

            <div className="newspaper-card-copy">
              <div>
                <span className="paper-label">NEWSPAPER SOURCE</span>
                <h2>{paper.name}</h2>
              </div>
              <p>Tenders &amp; procurement opportunities</p>
            </div>

            <a
              className="newspaper-open-button"
              href={paper.href}
              target="_blank"
              rel="noreferrer"
              aria-label={`Open ${paper.name} tenders`}
            >
              <span>Open tender page</span>
              <ExternalLink size={17} aria-hidden="true" />
            </a>
          </article>
        ))}
      </section>

      <style jsx>{`
        .newspaper-page {
          width: min(1240px, 100%);
          margin: 0 auto;
          padding: 8px 0 34px;
        }

        .newspaper-heading {
          padding: 8px 0 28px;
          border-bottom: 1px solid rgba(14, 48, 77, 0.09);
        }

        .newspaper-heading h1 {
          margin: 7px 0 8px;
          color: #071d35;
          font-size: clamp(30px, 4vw, 44px);
          line-height: 1.04;
          letter-spacing: -1.4px;
        }

        .newspaper-heading p {
          margin: 0;
          color: #718391;
          font-size: 12px;
          line-height: 1.6;
        }

        .newspaper-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 22px;
          margin-top: 28px;
        }

        .newspaper-card {
          position: relative;
          min-height: 410px;
          padding: 24px;
          display: flex;
          flex-direction: column;
          background: #fff;
          border: 2px solid var(--paper-accent);
          border-radius: 20px;
          box-shadow: 0 14px 36px rgba(7, 29, 53, 0.055);
          overflow: hidden;
          transition: transform 0.18s ease, box-shadow 0.18s ease;
        }

        .newspaper-card-monitor {
          --paper-accent: #cf2027;
          --paper-accent-soft: #fff4f4;
          --paper-accent-hover: #b81920;
        }

        .newspaper-card-newvision {
          --paper-accent: #e21b23;
          --paper-accent-soft: #fff5f5;
          --paper-accent-hover: #c8171e;
        }

        .newspaper-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 20px 46px rgba(7, 29, 53, 0.09);
        }

        .brand-line {
          position: absolute;
          inset: 0 0 auto;
          height: 7px;
          background: var(--paper-accent);
        }

        .newspaper-logo-wrap {
          height: 205px;
          display: grid;
          place-items: center;
          margin-top: 5px;
          padding: 24px 34px;
          border: 1px solid color-mix(in srgb, var(--paper-accent) 18%, transparent);
          border-radius: 15px;
          background: linear-gradient(180deg, #ffffff 0%, var(--paper-accent-soft) 100%);
          overflow: hidden;
        }

        .newspaper-logo {
          display: block;
          max-width: 100%;
          max-height: 150px;
          object-fit: contain;
          object-position: center;
        }

        .newspaper-logo-monitor {
          width: min(100%, 350px);
        }

        .newspaper-logo-newvision {
          width: min(100%, 250px);
        }

        .newspaper-card-copy {
          display: flex;
          align-items: end;
          justify-content: space-between;
          gap: 16px;
          padding: 20px 2px 18px;
        }

        .paper-label {
          display: block;
          margin-bottom: 6px;
          color: var(--paper-accent);
          font-size: 8px;
          font-weight: 900;
          letter-spacing: 1.3px;
        }

        .newspaper-card-copy h2 {
          margin: 0;
          color: #071d35;
          font-size: 22px;
          letter-spacing: -0.5px;
        }

        .newspaper-card-copy p {
          margin: 0 0 2px;
          color: #7d8e9b;
          font-size: 10px;
          white-space: nowrap;
        }

        .newspaper-open-button {
          min-height: 50px;
          margin-top: auto;
          padding: 0 18px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 9px;
          border-radius: 11px;
          background: #071d35;
          color: #fff;
          font-size: 12px;
          font-weight: 850;
          text-decoration: none;
          box-shadow: 0 8px 20px rgba(7, 29, 53, 0.14);
          transition: transform 0.16s ease, background 0.16s ease, box-shadow 0.16s ease;
        }

        .newspaper-open-button:hover {
          background: var(--paper-accent-hover);
          transform: translateY(-1px);
          box-shadow: 0 10px 24px color-mix(in srgb, var(--paper-accent) 26%, transparent);
        }

        @media (max-width: 980px) {
          .newspaper-card-copy {
            align-items: flex-start;
            flex-direction: column;
            gap: 7px;
          }

          .newspaper-card-copy p {
            white-space: normal;
          }
        }

        @media (max-width: 820px) {
          .newspaper-grid {
            grid-template-columns: 1fr;
            gap: 18px;
          }

          .newspaper-card {
            min-height: 390px;
          }

          .newspaper-logo-wrap {
            height: 190px;
          }
        }

        @media (max-width: 520px) {
          .newspaper-page {
            padding-bottom: 22px;
          }

          .newspaper-heading {
            padding-bottom: 20px;
          }

          .newspaper-card {
            min-height: 350px;
            padding: 16px;
            border-radius: 16px;
          }

          .newspaper-logo-wrap {
            height: 165px;
            padding: 18px 24px;
            border-radius: 12px;
          }

          .newspaper-logo {
            max-height: 125px;
          }

          .newspaper-logo-monitor {
            width: min(100%, 290px);
          }

          .newspaper-logo-newvision {
            width: min(100%, 210px);
          }

          .newspaper-card-copy {
            padding: 17px 2px 15px;
          }

          .newspaper-card-copy h2 {
            font-size: 19px;
          }

          .newspaper-open-button {
            min-height: 48px;
          }
        }
      `}</style>
    </div>
  );
}
