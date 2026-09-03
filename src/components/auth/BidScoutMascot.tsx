"use client";

export type MascotMode = "idle" | "email" | "password" | "loading" | "error" | "success";

const copy: Record<MascotMode, string> = {
  idle: "Ready when you are.",
  email: "Typing email? I am watching right here.",
  password: "I will close my eyes.",
  loading: "Looking for today’s opportunities…",
  error: "Let’s check those details again.",
  success: "Welcome back! I found you.",
};

export function BidScoutMascot({ mode, emailProgress = 0 }: { mode: MascotMode; emailProgress?: number }) {
  const watching = mode === "email";
  const closed = mode === "password";
  const error = mode === "error";
  const pupilX = watching ? Math.min(6.2, 2.4 + emailProgress * 4.2) : 0;
  const pupilY = watching ? 2 : 0;

  return (
    <div className={`suite-mascot suite-mascot-${mode}`} aria-live="polite">
      <div className="suite-mascot-float">
        <svg viewBox="0 0 260 205" role="img" aria-label="AutoMinds Bid Finder mascot">
          <defs>
            <radialGradient id="bodyGlow" cx="31%" cy="22%" r="82%">
              <stop offset="0" stopColor="#ffae58" />
              <stop offset=".38" stopColor="#ff8a28" />
              <stop offset=".73" stopColor="#f56b09" />
              <stop offset="1" stopColor="#bd4d20" />
            </radialGradient>
            <linearGradient id="finGlow" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#ff8a27" />
              <stop offset="1" stopColor="#e85a09" />
            </linearGradient>
            <linearGradient id="faceShade" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#ffffff" stopOpacity=".18" />
              <stop offset=".55" stopColor="#ffffff" stopOpacity="0" />
              <stop offset="1" stopColor="#6f2516" stopOpacity=".28" />
            </linearGradient>
            <filter id="softOrbShadow" x="-40%" y="-40%" width="180%" height="200%">
              <feDropShadow dx="0" dy="9" stdDeviation="8" floodColor="#173a58" floodOpacity=".22" />
            </filter>
            <filter id="floorBlur" x="-40%" y="-80%" width="180%" height="260%">
              <feGaussianBlur stdDeviation="2.2" />
            </filter>
          </defs>

          <ellipse className="mascot-floor-shadow" cx="130" cy="184" rx="49" ry="11" fill="#9aa5ad" opacity=".42" filter="url(#floorBlur)" />

          <g className="mascot-orb-body" filter="url(#softOrbShadow)">
            {/* ears / fins */}
            <path d="M88 50 79 19c-2-8 6-12 12-6l21 23Z" fill="url(#finGlow)" />
            <path d="m169 49 12-29c3-8 12-7 13 1l-2 34Z" fill="url(#finGlow)" />
            <path d="M66 87 35 68c-8-5-15 2-10 10l25 30Z" fill="url(#finGlow)" />
            <path d="m193 88 31-20c8-5 15 3 10 10l-25 30Z" fill="url(#finGlow)" />
            <path d="M68 124 42 145c-7 6-3 14 6 12l33-10Z" fill="url(#finGlow)" />
            <path d="m191 124 27 21c7 6 3 14-6 12l-33-10Z" fill="url(#finGlow)" />

            {/* orb */}
            <circle cx="130" cy="105" r="70" fill="url(#bodyGlow)" />
            <circle cx="130" cy="105" r="70" fill="url(#faceShade)" opacity=".82" />
            <path d="M82 61c24-21 65-28 98-11" fill="none" stroke="#ffc179" strokeWidth="8" strokeLinecap="round" opacity=".55" />
            <path d="M84 52c21-14 46-19 72-14" fill="none" stroke="#ffb25d" strokeWidth="4" strokeLinecap="round" opacity=".38" />

            {/* eyes */}
            {closed ? (
              <g className="mascot-eyes-closed" fill="none" stroke="#153d5c" strokeLinecap="round">
                <path d="M91 95q14 11 27 0" strokeWidth="5" />
                <path d="M143 95q14 11 27 0" strokeWidth="5" />
                <path d="m95 86-5-4M114 85l4-5M147 85l-4-5M166 86l5-4" strokeWidth="2.8" />
              </g>
            ) : (
              <g className="mascot-eyes-open">
                <ellipse cx="105" cy="94" rx="16" ry="20" fill="#fff" />
                <ellipse cx="157" cy="94" rx="16" ry="20" fill="#fff" />
                <circle cx={106 + pupilX} cy={96 + pupilY} r="6.4" fill="#173f60" className="mascot-pupil mascot-pupil-left" />
                <circle cx={158 + pupilX} cy={96 + pupilY} r="6.4" fill="#173f60" className="mascot-pupil mascot-pupil-right" />
                <circle cx={104 + pupilX} cy={93 + pupilY} r="2" fill="#fff" />
                <circle cx={156 + pupilX} cy={93 + pupilY} r="2" fill="#fff" />
              </g>
            )}

            {/* nose + expression */}
            <circle cx="131" cy="117" r="3.6" fill="#173f60" />
            {error ? (
              <path d="M111 139q20-13 40 0" fill="none" stroke="#173f60" strokeWidth="4" strokeLinecap="round" className="mascot-mouth" />
            ) : (
              <path d="M111 132q20 18 40 0" fill="none" stroke="#173f60" strokeWidth="4" strokeLinecap="round" className="mascot-mouth" />
            )}

            {/* AutoMinds node smile */}
            <g className="mascot-node-smile" stroke="#fff" strokeWidth="2" fill="#fff" opacity=".98">
              <circle cx="87" cy="122" r="3.2" />
              <circle cx="96" cy="138" r="3.2" />
              <circle cx="111" cy="146" r="3.2" />
              <circle cx="174" cy="122" r="3.2" />
              <circle cx="165" cy="138" r="3.2" />
              <circle cx="150" cy="146" r="3.2" />
              <path d="m87 122 9 16 15 8 20-28 19 28 15-8 9-16" fill="none" />
            </g>
          </g>
        </svg>
      </div>
      <div className="suite-mascot-copy"><strong>{copy[mode]}</strong></div>
    </div>
  );
}
