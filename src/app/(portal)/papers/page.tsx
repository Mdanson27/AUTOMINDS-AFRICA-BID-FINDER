import { ExternalLink } from "lucide-react";

const papers = [
  {
    name: "Daily Monitor",
    href: "https://www.monitor.co.ug/uganda/jobs/tenders",
    logo: "https://www.thecitizen.co.tz/resource/image/2710224/landscape_ratio3x2/1620/1080/18926b999ccec70c91c7a4b87efa7d58/xj/monitor.jpg",
    logoClassName: "monitor-logo",
  },
  {
    name: "New Vision",
    href: "https://www.newvision.co.ug/opportunities/tenders",
    logo: "https://assets.kreatio.net/new_vision/images/small_logo1.jpg",
    logoClassName: "newvision-logo",
  },
] as const;

export default function PapersPage() {
  return (
    <div className="newspaper-page">
      <header className="newspaper-heading">
        <span className="eyebrow">CURRENT PAPERS</span>
        <h1>Newspaper tender pages</h1>
        <p>Choose a newspaper to open its tender and procurement notices.</p>
      </header>

      <section className="newspaper-grid" aria-label="Uganda newspaper tender pages">
        {papers.map((paper) => (
          <article className="newspaper-card" key={paper.name}>
            <div className="newspaper-logo-wrap">
              <img
                className={`newspaper-logo ${paper.logoClassName}`}
                src={paper.logo}
                alt={`${paper.name} logo`}
              />
            </div>

            <div className="newspaper-card-copy">
              <h2>{paper.name}</h2>
              <span>Tenders &amp; procurement opportunities</span>
            </div>

            <a
              className="newspaper-open-button"
              href={paper.href}
              target="_blank"
              rel="noreferrer"
              aria-label={`Open ${paper.name} tenders`}
            >
              Open tender page
              <ExternalLink size={17} aria-hidden="true" />
            </a>
          </article>
        ))}
      </section>

      <style jsx>{`
        .newspaper-page {
          width: min(1240px, 100%);
          margin: 0 auto;
          padding: 8px 0 30px;
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
          gap: 20px;
          margin-top: 28px;
        }

        .newspaper-card {
          min-height: 440px;
          padding: 28px;
          display: flex;
          flex-direction: column;
          align-items: stretch;
          background: #fff;
          border: 1px solid rgba(14, 48, 77, 0.1);
          border-radius: 20px;
          box-shadow: 0 12px 34px rgba(7, 29, 53, 0.05);
          overflow: hidden;
          transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }

        .newspaper-card:hover {
          transform: translateY(-2px);
          border-color: rgba(14, 48, 77, 0.17);
          box-shadow: 0 18px 42px rgba(7, 29, 53, 0.08);
        }

        .newspaper-logo-wrap {
          min-height: 235px;
          display: grid;
          place-items: center;
          padding: 24px;
          border-radius: 15px;
          background: #f7f8fa;
          overflow: hidden;
        }

        .newspaper-logo {
          display: block;
          width: min(100%, 420px);
          max-height: 180px;
          object-fit: contain;
        }

        .monitor-logo {
          border-radius: 8px;
        }

        .newvision-logo {
          width: min(100%, 300px);
        }

        .newspaper-card-copy {
          padding: 22px 2px 19px;
        }

        .newspaper-card-copy h2 {
          margin: 0;
          color: #071d35;
          font-size: 22px;
          letter-spacing: -0.5px;
        }

        .newspaper-card-copy span {
          display: block;
          margin-top: 6px;
          color: #7d8e9b;
          font-size: 11px;
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
          transition: transform 0.16s ease, background 0.16s ease;
        }

        .newspaper-open-button:hover {
          background: #0c3158;
          transform: translateY(-1px);
        }

        @media (max-width: 820px) {
          .newspaper-grid {
            grid-template-columns: 1fr;
          }

          .newspaper-card {
            min-height: 390px;
          }

          .newspaper-logo-wrap {
            min-height: 200px;
          }
        }

        @media (max-width: 520px) {
          .newspaper-card {
            padding: 18px;
            border-radius: 16px;
          }

          .newspaper-logo-wrap {
            min-height: 170px;
            padding: 18px;
          }

          .newspaper-card-copy h2 {
            font-size: 19px;
          }
        }
      `}</style>
    </div>
  );
}
