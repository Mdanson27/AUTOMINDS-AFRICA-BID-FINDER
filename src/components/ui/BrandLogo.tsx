"use client";

import { useState } from "react";

export function BrandLogo({ compact = false, light = false }: { compact?: boolean; light?: boolean }) {
  const [failed, setFailed] = useState(false);
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

  return (
    <div className={`brand-logo ${compact ? "compact" : ""} ${light ? "light" : ""}`}>
      {!failed ? (
        <img src={`${basePath}/logo.jpeg`} alt="AutoMinds Africa" onError={() => setFailed(true)} />
      ) : (
        <>
          <span className="brand-mark">A</span>
          {!compact && <span className="brand-words"><strong>AutoMinds</strong><small>AFRICA</small></span>}
        </>
      )}
    </div>
  );
}
