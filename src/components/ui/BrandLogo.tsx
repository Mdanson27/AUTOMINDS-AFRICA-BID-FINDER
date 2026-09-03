"use client";

import { useState } from "react";

const logoCandidates = ["/logo.png", "/logo.jpeg"];

export function BrandLogo({ compact = false, light = false }: { compact?: boolean; light?: boolean }) {
  const [candidate, setCandidate] = useState(0);
  const failed = candidate >= logoCandidates.length;

  return (
    <div className={`brand-logo ${compact ? "compact" : ""} ${light ? "light" : ""}`}>
      {!failed && (
        <img
          src={logoCandidates[candidate]}
          alt="AutoMinds Africa"
          onError={() => setCandidate((current) => current + 1)}
        />
      )}
      {failed && <><span className="brand-mark">A</span>{!compact && <span className="brand-words"><strong>AutoMinds</strong><small>AFRICA</small></span>}</>}
    </div>
  );
}
