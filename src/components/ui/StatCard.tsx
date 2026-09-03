export function StatCard({ label, value, icon, hint }: { label: string; value: React.ReactNode; icon: React.ReactNode; hint: string }) {
  return <article className="stat-card"><div className="stat-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{hint}</small></div></article>;
}
