/** Compact money notation for dashboard display (e.g. 100000 → "100K"). */

export function formatMoney(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1_000_000) {
    const formatted = abs / 1_000_000;
    const rounded =
      formatted >= 10
        ? Math.round(formatted)
        : Math.round(formatted * 10) / 10;
    return `${sign}${rounded}M`;
  }
  if (abs >= 1_000) {
    return `${sign}${Math.round(abs / 1_000)}K`;
  }
  return `${sign}${Math.round(abs)}`;
}

export function parseDecimal(value: string | number): number {
  if (typeof value === "number") return value;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function formatMonthLabel(monthIso: string): string {
  const date = new Date(`${monthIso}T12:00:00`);
  return date.toLocaleDateString("es-CO", { month: "short", year: "2-digit" });
}

export function toYmd(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
