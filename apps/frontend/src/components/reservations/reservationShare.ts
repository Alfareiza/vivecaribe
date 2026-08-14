import type { Reservation } from "@/types/reservation";
import { formatRawDateTime } from "./reservationUtils";

/** Digits only for wa.me; strips leading + and non-digits. */
export function phoneDigitsForWhatsApp(phone: string): string {
  return phone.replace(/\D/g, "");
}

/**
 * Calendar YYYY-MM-DD read straight off the ISO string's own digits, ignoring
 * any offset/"Z" suffix — see formatRawDateTime in reservationUtils for why
 * fecha_evento can't be treated as a real UTC instant.
 */
export function bogotaDateKey(iso: string): string | null {
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(iso);
  return match ? match[1] : null;
}

function nextDayKey(yyyyMmDd: string): string {
  const [y, m, d] = yyyyMmDd.split("-").map(Number);
  const utc = new Date(Date.UTC(y, m - 1, d));
  utc.setUTCDate(utc.getUTCDate() + 1);
  const yy = utc.getUTCFullYear();
  const mm = String(utc.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(utc.getUTCDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}`;
}

function compactDate(yyyyMmDd: string): string {
  return yyyyMmDd.replace(/-/g, "");
}

export function buildWhatsAppShareUrl(reservation: Reservation): string | null {
  const digits = phoneDigitsForWhatsApp(reservation.phone);
  if (!digits) return null;

  const fecha = reservation.fecha_evento
    ? formatRawDateTime(reservation.fecha_evento)
    : "Sin fecha";

  const lines = [
    `Hi ${reservation.customer_name}, today is the day. Let's enjoy the experience of ${reservation.nombre_experiencia}`,
    // `----`,
    // `Fecha: ${fecha}`,
    // `Cliente: ${reservation.customer_name}`,
    // `Teléfono: ${reservation.phone}`,
    // `Ciudad: ${reservation.ciudad_experiencia}`,
    // `Participantes: ${reservation.participants}`,
  ];

  const text = encodeURIComponent(lines.join("\n"));
  return `https://wa.me/${digits}?text=${text}`;
}

/** Google Calendar all-day TEMPLATE URL; null when fecha_evento missing/invalid. */
export function buildGoogleCalendarUrl(reservation: Reservation): string | null {
  if (!reservation.fecha_evento) return null;
  const startKey = bogotaDateKey(reservation.fecha_evento);
  if (!startKey) return null;
  const endKey = nextDayKey(startKey);

  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: reservation.nombre_experiencia,
    dates: `${compactDate(startKey)}/${compactDate(endKey)}`,
    details: [
      `Referencia: ${reservation.reserva_reference}`,
      `Cliente: ${reservation.customer_name}`,
      `Ciudad: ${reservation.ciudad_experiencia}`,
      `Participantes: ${reservation.participants}`,
    ].join("\n"),
    location: reservation.ciudad_experiencia,
  });

  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}
