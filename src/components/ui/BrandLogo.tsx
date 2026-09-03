"use client";

export function BrandLogo({ compact = false, light = false }: { compact?: boolean; light?: boolean }) {
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

  return (
    <div className={`brand-logo ${compact ? "compact" : ""} ${light ? "light" : ""}`}>
      <img src={`${basePath}/logo.jpeg`} alt="AutoMinds Africa" />
    </div>
  );
}
