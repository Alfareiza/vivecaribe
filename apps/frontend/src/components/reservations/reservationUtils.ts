import type { BadgeColor } from "@/components/ui/badge/Badge";
import type { PartidoListItem } from "@/types/partido";
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

export type RawDateTime = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
};

/** Wall-clock Y-M-D H:M from the ISO digits; ignores any offset/"Z" suffix. */
export function parseRawDateTime(iso: string): RawDateTime | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso);
  if (!match) return null;
  return {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
    hour: Number(match[4]),
    minute: Number(match[5]),
  };
}

function asUtcDate(parts: RawDateTime): Date {
  return new Date(
    Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute),
  );
}

/**
 * Same "es-CO" medium/short shape as formatDisplayDateTime, but reads the
 * Y-M-D H:M straight off the ISO string and ignores any offset/"Z" suffix —
 * for values stored as naive wall-clock time that a DB round trip mislabels
 * with a UTC offset (fecha_evento). Not for genuinely timezone-aware values.
 */
export function formatRawDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const parts = parseRawDateTime(iso);
  if (!parts) return iso;
  return new Intl.DateTimeFormat("es-CO", {
    timeZone: "UTC",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(asUtcDate(parts));
}

/** English "5:35 p.m." from naive ISO, optionally shifted by minutes. */
export function formatEnglishTime(iso: string, offsetMinutes = 0): string {
  const parts = parseRawDateTime(iso);
  if (!parts) return "—";
  const date = asUtcDate(parts);
  date.setUTCMinutes(date.getUTCMinutes() + offsetMinutes);
  const hour24 = date.getUTCHours();
  const minute = String(date.getUTCMinutes()).padStart(2, "0");
  const period = hour24 >= 12 ? "p.m." : "a.m.";
  const hour12 = hour24 % 12 || 12;
  return `${hour12}:${minute} ${period}`;
}

/** English weekday ("Monday") from the naive ISO calendar day. */
export function formatEnglishWeekday(iso: string): string {
  const parts = parseRawDateTime(iso);
  if (!parts) return "";
  const date = new Date(Date.UTC(parts.year, parts.month - 1, parts.day));
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    timeZone: "UTC",
  }).format(date);
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

/**
 * Strips everything but digits and a decimal point from a numeric-only
 * input (rates, costs, gastos) as the operator types, keeping only the
 * first "." if they type more than one — so a plain-decimal field can
 * never end up holding letters or symbols.
 */
export function sanitizeDecimalInput(value: string): string {
  const digitsAndDots = value.replace(/[^\d.]/g, "");
  const firstDot = digitsAndDots.indexOf(".");
  if (firstDot === -1) return digitsAndDots;
  return (
    digitsAndDots.slice(0, firstDot + 1) +
    digitsAndDots.slice(firstDot + 1).replace(/\./g, "")
  );
}

/** "544252161.08" -> "544.252.161,08" — es-CO thousands/decimal separators, no currency symbol, for editable amount inputs. Returns the raw string unchanged if it isn't a plain number. */
export function formatPlainNumberCO(value: string): string {
  if (!value.trim()) return value;
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  return new Intl.NumberFormat("es-CO", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/** Strips everything but digits — for whole-peso amount inputs (e.g. gastos) that don't take cents. */
export function sanitizeIntegerInput(value: string): string {
  return value.replace(/[^\d]/g, "");
}

/** "544252161" -> "544.252.161" — es-CO thousands separator, no decimals, no currency symbol. Returns the raw string unchanged if it isn't a plain number. */
export function formatIntegerCO(value: string): string {
  if (!value.trim()) return value;
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  return new Intl.NumberFormat("es-CO", {
    maximumFractionDigits: 0,
  }).format(amount);
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
  propio: "ViveCaribe",
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

/** Same calendar day as `fechaEvento`'s raw Y-M-D, as a UTC day window. */
export function dayWindow(
  fechaEvento: string,
): { from: string; to: string } | null {
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(fechaEvento);
  if (!match) return null;
  const day = match[1];
  return { from: `${day}T00:00:00Z`, to: `${day}T23:59:59Z` };
}

export function partidoLabel(partido: PartidoListItem): string {
  return `${partido.equipo_local} vs ${partido.equipo_visitante} — ${partido.ciudad} (${formatRawDateTime(partido.fecha)})`;
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
