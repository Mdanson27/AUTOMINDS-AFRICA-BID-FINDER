"use client";

export type MascotMode = "idle" | "email" | "password" | "loading" | "error" | "success";

const copy: Record<MascotMode, { title: string; body: string }> = {
  idle: { title: "Ready when you are.", body: "Let’s find the next opportunity." },
  email: { title: "Typing email? I am watching right here.", body: "I will keep an eye on the details." },
  password: { title: "I will close my eyes.", body: "Your password stays private." },
  loading: { title: "Searching the landscape…", body: "Opening your procurement workspace." },
  error: { title: "That did not work.", body: "Check the details and we will try again." },
  success: { title: "Found you. Welcome back!", body: "Your bid workspace is ready." },
};

export function BidScoutMascot({ mode, emailProgress = 0 }: { mode: MascotMode; emailProgress?: number }) {
  const shift = mode === "email" ? Math.min(8, 2 + emailProgress * 7) : 0;
  const closed = mode === "password";

  return (
    <div className={`suite-mascot suite-mascot-${mode}`}>
      <div className="suite-mascot-float">
        <svg viewBox="0 0 250 220" role="img" aria-label="AutoMinds opportunity scout mascot">
          <defs>
            <radialGradient id="orbBody" cx="35%" cy="22%" r="75%">
              <stop offset="0" stopColor="#ffad55" />
              <stop offset=".45" stopColor="#ff8623" />
              <stop offset="1" stopColor="#df5800" />
            </radialGradient>
            <linearGradient id="orbEar" x1="0" y1="0" x2="1" y2="1">
              <stop stopColor="#ff8b24" />
              <stop offset="1" stopColor="#f05e00" />
            </linearGradient>
            <filter id="orbShadow" x="-30%" y="-30%" width="160%" height="180%">
              <feDropShadow dx="0" dy="8" stdDeviation="7" floodColor="#17344b" floodOpacity=".24" />
            </filter>
          </defs>

          <ellipse className="mascot-floor-shadow" cx="126" cy="193" rx="48" ry="12" fill="#163d5c" opacity=".17" />
          <g filter="url(#orbShadow)" className="mascot-orb-body">
            <path d="M88 48 75 22c-3-7 3-14 10-10l22 17Z" fill="url(#orbEar)" />
            <path d="m160 48 15-25c4-7 11-5 11 3l-2 29Z" fill="url(#orbEar)" />
            <path d="M62 101 31 88c-8-3-13 5-7 11l25 25Z" fill="url(#orbEar)" />
            <path d="m188 101 31-13c8-3 13 5 7 11l-25 25Z" fill="url(#orbEar)" />
            <circle cx="125" cy="108" r="72" fill="url(#orbBody)" />
            <path d="M73 65c29-29 77-31 108-3" fill="none" stroke="#ffbe72" strokeWidth="8" strokeLinecap="round" opacity=".44" />
            <path d="M68 119 45 139c-6 6-3 14 5 12l29-9Z" fill="url(#orbEar)" />
            <path d="m182 119 23 20c6 6 3 14-5 12l-29-9Z" fill="url(#orbEar)" />

            {closed ? (
              <g className="mascot-eyes-closed" fill="none" stroke="#153b59" strokeWidth="5" strokeLinecap="round">
                <path d="M88 97q14 12 27 0" />
                <path d="M136 97q14 12 27 0" />
                <path d="M92 88 86 83" strokeWidth="3" /><path d="m159 88 6-5" strokeWidth="3" />
              </g>
            ) : (
              <g className="mascot-eyes-open">
                <ellipse cx="103" cy="96" rx="16" ry="20" fill="#fff" />
                <ellipse cx="151" cy="96" rx="16" ry="20" fill="#fff" />
                <circle cx={104 + shift} cy="98" r="6" fill="#173d5c" className="mascot-pupil" />
                <circle cx={152 + shift} cy="98" r="6" fill="#173d5c" className="mascot-pupil" />
                <circle cx={102 + shift} cy="95" r="2" fill="#fff" />
                <circle cx={150 + shift} cy="95" r="2" fill="#fff" />
              </g>
            )}

            <path d="M108 130q18 17 38 0" fill="none" stroke="#153b59" strokeWidth="4" strokeLinecap="round" className="mascot-smile" />
            <circle cx="126" cy="118" r="4" fill="#153b59" />
            <g fill="#fff" stroke="#fff" strokeWidth="1.5" opacity=".96">
              <circle cx="82" cy="121" r="3" /><circle cx="92" cy="137" r="3" /><circle cx="107" cy="145" r="3" />
              <circle cx="169" cy="121" r="3" /><circle cx="159" cy="137" r="3" /><circle cx="144" cy="145" r="3" />
              <path d="m82 121 10 16 15 8M169 121l-10 16-15 8M107 145l19-27 18 27" fill="none" />
            </g>
          </g>
        </svg>
      </div>
      <div className="suite-mascot-copy"><strong>{copy[mode].title}</strong><span>{copy[mode].body}</span></div>
    </div>
  );
}
