"use client";

export type MascotMode = "idle" | "email" | "password" | "loading";

const copy: Record<MascotMode, { title: string; body: string }> = {
  idle: { title: "Looking for bids, I see.", body: "Sign in and let’s see what we have today." },
  email: { title: "I see you checking in.", body: "That email is getting my attention." },
  password: { title: "Privacy mode: ON.", body: "I won’t peek. Your password stays yours." },
  loading: { title: "Scanning the landscape…", body: "Opening your procurement workspace." },
};

export function BidScoutMascot({ mode, emailProgress = 0 }: { mode: MascotMode; emailProgress?: number }) {
  const pupilShift = mode === "email" ? 3 + emailProgress * 4 : 0;
  return (
    <div className={`mascot mascot-${mode}`}>
      <div className="mascot-bubble"><strong>{copy[mode].title}</strong><span>{copy[mode].body}</span></div>
      <svg viewBox="0 0 220 170" role="img" aria-label="AutoMinds Bid Scout mascot">
        <defs><linearGradient id="helmet" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ff982f" /><stop offset="1" stopColor="#f36d00" /></linearGradient></defs>
        <path d="M54 92c0-38 25-66 56-66s56 28 56 66v25H54V92Z" fill="url(#helmet)" />
        <path d="M67 76c6-26 22-39 43-39 22 0 38 13 44 39" fill="none" stroke="#0a426a" strokeWidth="8" strokeLinecap="round" />
        <rect x="65" y="62" width="90" height="72" rx="28" fill="#f8fbfd" stroke="#0a426a" strokeWidth="6" />
        <circle cx="91" cy="94" r="11" fill="#dceaf3" /><circle cx="129" cy="94" r="11" fill="#dceaf3" />
        <circle cx={91 + pupilShift} cy="94" r="4.5" fill="#0a426a" className="mascot-pupil" /><circle cx={129 + pupilShift} cy="94" r="4.5" fill="#0a426a" className="mascot-pupil" />
        <path d="M94 117c10 6 22 6 32 0" fill="none" stroke="#0a426a" strokeWidth="4" strokeLinecap="round" />
        <path d="M110 24V13" stroke="#0a426a" strokeWidth="5" strokeLinecap="round" /><circle cx="110" cy="9" r="6" fill="#ff7a00" stroke="#0a426a" strokeWidth="3" />
        <path d="M63 83 43 69 29 80 48 96" fill="none" stroke="#0a426a" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="27" cy="80" r="7" fill="#ff7a00" stroke="#0a426a" strokeWidth="4" />
        <g className="mascot-hands">
          <path d="M42 150c5-26 24-49 48-56" fill="none" stroke="#0a426a" strokeWidth="12" strokeLinecap="round" />
          <path d="M178 150c-5-26-24-49-48-56" fill="none" stroke="#0a426a" strokeWidth="12" strokeLinecap="round" />
          <circle cx="90" cy="94" r="14" fill="#ff7a00" stroke="#0a426a" strokeWidth="4" /><circle cx="130" cy="94" r="14" fill="#ff7a00" stroke="#0a426a" strokeWidth="4" />
        </g>
        <path d="M75 134h70l-8 26H83l-8-26Z" fill="#0a426a" /><path d="M100 141h20" stroke="#ff7a00" strokeWidth="5" strokeLinecap="round" />
      </svg>
    </div>
  );
}
