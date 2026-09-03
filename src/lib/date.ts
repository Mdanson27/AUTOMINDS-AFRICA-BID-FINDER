export function formatDate(value?: string, includeTime = false) {
  if (!value) return "Not provided";
  const date = new Date(value); if (Number.isNaN(date.getTime())) return "Not provided";
  return new Intl.DateTimeFormat("en-UG", { day: "numeric", month: "short", year: "numeric", ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}) }).format(date);
}
export function daysUntil(value?: string) {
  if (!value) return 9999; const target = new Date(value); if (Number.isNaN(target.getTime())) return 9999;
  return Math.ceil((target.getTime() - Date.now()) / 86_400_000);
}
export function isSameLocalDay(value: string | undefined, compare: Date) {
  if (!value) return false; const date = new Date(value); return date.getFullYear() === compare.getFullYear() && date.getMonth() === compare.getMonth() && date.getDate() === compare.getDate();
}
