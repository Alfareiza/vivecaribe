import type { Reservation } from "@/types/reservation";

const BOGOTA_TZ = "America/Bogota";

/** Digits only for wa.me; strips leading + and non-digits. */
export function phoneDigitsForWhatsApp(phone: string): string {
  return phone.replace(/\D/g, "");
}

function formatBogotaDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("es-CO", {
    timeZone: BOGOTA_TZ,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

/** Calendar YYYY-MM-DD in America/Bogota. */
export function bogotaDateKey(iso: string): string | null {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: BOGOTA_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const y = parts.find((p) => p.type === "year")?.value;
  const m = parts.find((p) => p.type === "month")?.value;
  const d = parts.find((p) => p.type === "day")?.value;
  if (!y || !m || !d) return null;
  return `${y}-${m}-${d}`;
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
    ? formatBogotaDateTime(reservation.fecha_evento)
    : "Sin fecha";

  const lines = [
    `Reserva ${reservation.reserva_reference}`,
    `Experiencia: ${reservation.nombre_experiencia}`,
    `Fecha: ${fecha}`,
    `Cliente: ${reservation.customer_name}`,
    `Teléfono: ${reservation.phone}`,
    `Ciudad: ${reservation.ciudad_experiencia}`,
    `Participantes: ${reservation.participants}`,
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
