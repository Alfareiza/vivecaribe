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
