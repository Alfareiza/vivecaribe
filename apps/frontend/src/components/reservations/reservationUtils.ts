import type { BadgeColor } from "@/components/ui/badge/Badge";
import type { ReservationListItem } from "@/types/reservation";

/** Kept for future estado badges; not used in the current list/modal UI. */
export function getEstadoBadgeColor(estado: string): BadgeColor {
  switch (estado.trim().toLowerCase()) {
    case "confirmada":
      return "success";
    case "en_progreso":
      return "warning";
    case "cancelada":
    case "error":
      return "error";
    default:
      return "light";
  }
}

/** Title-case Spanish label for operator-facing estado display. */
export function formatEstadoLabel(estado: string): string {
  switch (estado.trim().toLowerCase()) {
    case "confirmada":
      return "Confirmada";
    case "en_progreso":
      return "En progreso";
    case "cancelada":
      return "Cancelada";
    case "error":
      return "Error";
    default:
      return estado;
  }
}

export function formatDisplayDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("es-CO", {
    timeZone: "America/Bogota",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

/**
 * Same "es-CO" medium/short shape as formatDisplayDateTime, but reads the
 * Y-M-D H:M straight off the ISO string and ignores any offset/"Z" suffix —
 * for values stored as naive wall-clock time that a DB round trip mislabels
 * with a UTC offset (fecha_evento). Not for genuinely timezone-aware values.
 */
export function formatRawDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso);
  if (!match) return iso;
  const [, year, month, day, hour, minute] = match;
  const asUtc = new Date(
    Date.UTC(
      Number(year),
      Number(month) - 1,
      Number(day),
      Number(hour),
      Number(minute),
    ),
  );
  return new Intl.DateTimeFormat("es-CO", {
    timeZone: "UTC",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(asUtc);
}

/** "2 de agosto" — day + full Spanish month name, no time, no year. */
export function formatPaidAtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("es-CO", {
    timeZone: "America/Bogota",
    day: "numeric",
    month: "long",
  }).format(date);
}

export function formatPrice(price: string, moneda: string): string {
  return `${moneda} ${price}`;
}

/** Temporary fixed TRM (COP per USD) until a real rate source is wired up. */
export const TRM_COP_PLACEHOLDER = 4000;

export function formatCOP(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(amount)) return "—";
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatNumberCO(value: number): string {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 }).format(
    value,
  );
}

/** income x TRM placeholder — computed client-side, not a real conversion. */
export function estimateIncomeCOP(
  income: string | null | undefined,
): number | null {
  if (!income) return null;
  const amount = Number(income);
  if (Number.isNaN(amount)) return null;
  return amount * TRM_COP_PLACEHOLDER;
}

export function truncateText(
  value: string | null | undefined,
  maxLength = 20,
): { display: string; truncated: boolean } {
  if (!value) return { display: "—", truncated: false };
  if (value.length <= maxLength) return { display: value, truncated: false };
  return { display: `${value.slice(0, maxLength)}…`, truncated: true };
}

export const TIPO_TOUR_LABELS: Record<string, string> = {
  "football tour": "Tour de fútbol",
  "city tour": "City tour",
};

export const MEETING_POINT_LABELS: Record<string, string> = {
  "old shoes monument": "Monumento zapatos viejos",
  "Door-to-Door": "Puerta a puerta",
};

export const PROVIDER_LABELS: Record<string, string> = {
  getyourguide: "GetYourGuide",
  viator: "Viator",
  homefans: "Homefans",
  propio: "Propio",
  vayara: "Vayara",
  otro: "Otro",
  airbnb: "Airbnb",
};

/** "2026-09-01T20:00:00Z" -> "2026-09-01T20:00" for a datetime-local input. */
export function toDatetimeLocal(iso: string): string {
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})/.exec(iso);
  return match ? match[1] : "";
}

/** "2026-09-01T20:00" -> "2026-09-01T20:00:00Z" for the API payload. */
export function toIsoUtc(datetimeLocal: string): string {
  return `${datetimeLocal}:00Z`;
}

/** "2026-09-01T20:00:00Z" -> "2026-09-01" (raw calendar day, no timezone shift). */
export function rawDateOnly(iso: string): string {
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(iso);
  return match ? match[1] : iso;
}

/** Local calendar YYYY-MM-DD for inclusive range checks. */
export function toLocalDateKey(iso: string): string {
  const date = new Date(iso);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export type DateRangeFilter = {
  from: string | null;
  to: string | null;
};

export function reservationInDateRange(
  reservation: Pick<ReservationListItem, "fecha_evento">,
  range: DateRangeFilter
): boolean {
  const { from, to } = range;
  if (!from && !to) return true;
  if (!reservation.fecha_evento) return false;

  const key = toLocalDateKey(reservation.fecha_evento);
  if (from && key < from) return false;
  if (to && key > to) return false;
  return true;
}

/** Get today's date in Bogota timezone as YYYY-MM-DD string. */
function getTodayInBogota(): string {
  const now = new Date();
  const bogotaFormatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Bogota",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return bogotaFormatter.format(now);
}

/**
 * Determine if an ISO datetime (naive wall-clock time) is in the past, today, or future.
 * Compares YYYY-MM-DD portion with today in America/Bogota timezone.
 */
export type DateState = "past" | "today" | "future";

export function getDateState(iso: string | null | undefined): DateState {
  if (!iso) return "future";
  const dateKey = toLocalDateKey(iso);
  const today = getTodayInBogota();

  if (dateKey < today) return "past";
  if (dateKey === today) return "today";
  return "future";
}
