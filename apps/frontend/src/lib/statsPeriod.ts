/** Date-range helpers for the Statistics chart, in America/Bogota. */

const BOGOTA = "America/Bogota";

const MONTHS_TITLE = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
] as const;

const MONTHS_LOWER = MONTHS_TITLE.map((name) => name.toLowerCase());

export type StatsPreset =
  | "this_year"
  | "this_month"
  | "last_semester"
  | "last_year"
  | "custom";

export type DateRange = { from: string; to: string };

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

export function bogotaYmd(now = new Date()): string {
  return now.toLocaleDateString("en-CA", { timeZone: BOGOTA });
}

function bogotaParts(now = new Date()): {
  year: number;
  month: number;
  day: number;
} {
  const [year, month, day] = bogotaYmd(now).split("-").map(Number);
  return { year, month, day };
}

export function rangeForPreset(
  preset: Exclude<StatsPreset, "custom">,
  now = new Date(),
): DateRange {
  const { year, month, day } = bogotaParts(now);
  const today = `${year}-${pad(month)}-${pad(day)}`;
  switch (preset) {
    case "this_year":
      return { from: `${year}-01-01`, to: today };
    case "this_month":
      return { from: `${year}-${pad(month)}-01`, to: today };
    case "last_semester":
      if (month <= 6) {
        return { from: `${year - 1}-07-01`, to: `${year - 1}-12-31` };
      }
      return { from: `${year}-01-01`, to: `${year}-06-30` };
    case "last_year":
      return { from: `${year - 1}-01-01`, to: `${year - 1}-12-31` };
  }
}

/** First-of-month ISO dates from ``from`` through the month of ``to`` inclusive. */
export function monthsInRange(from: string, to: string): string[] {
  const [fromYear, fromMonth] = from.split("-").map(Number);
  const [toYear, toMonth] = to.split("-").map(Number);
  if (!fromYear || !fromMonth || !toYear || !toMonth) return [];

  const months: string[] = [];
  let year = fromYear;
  let month = fromMonth;
  while (year < toYear || (year === toYear && month <= toMonth)) {
    months.push(`${year}-${pad(month)}-01`);
    month += 1;
    if (month > 12) {
      month = 1;
      year += 1;
    }
  }
  return months;
}

function formatSlash(ymd: string): string {
  const [year, month] = ymd.split("-");
  return `${MONTHS_TITLE[Number(month) - 1]}/${year.slice(2)}`;
}

export function statsFilterPhrase(
  preset: StatsPreset,
  range: DateRange,
): string {
  const year = Number(range.from.slice(0, 4));
  switch (preset) {
    case "this_year":
      return `Información de lo que va del ${year}`;
    case "this_month": {
      const month = Number(range.from.slice(5, 7));
      return `Información de lo que va de ${MONTHS_LOWER[month - 1]} ${year}`;
    }
    case "last_semester":
      return `Información de ${formatSlash(range.from)} a ${formatSlash(range.to)}`;
    case "last_year":
      return `Información del ${year}`;
    case "custom":
      if (range.from === range.to) {
        return `Información de ${formatSlash(range.from)}`;
      }
      return `Información de ${formatSlash(range.from)} a ${formatSlash(range.to)}`;
  }
}
