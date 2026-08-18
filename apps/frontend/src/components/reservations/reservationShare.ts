import type { PartidoListItem } from "@/types/partido";
import type { Reservation } from "@/types/reservation";
import { formatEnglishTime, formatEnglishWeekday } from "./reservationUtils";

/** Digits only for WhatsApp click-to-chat; strips leading + and non-digits. */
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

function localTeamKind(
  equipoLocal: string,
): "junior" | "cartagena" | null {
  const name = equipoLocal.toLowerCase();
  if (name.includes("junior")) return "junior";
  if (name.includes("cartagena")) return "cartagena";
  return null;
}

function welcomeLines(reservation: Reservation): string[] {
  return [
    `Hi ${reservation.customer_name}`,
    ``,
    `Thanks for booking with us through ${reservation.booking_provider}.`,
    `We're excited to have you with us and show you the passion of football in Colombia.`,
    ``,
    `In the coming days, we'll share your match day itinerary.`,
  ];
}

function juniorItineraryLines(partido: PartidoListItem): string[] {
  const weekday = formatEnglishWeekday(partido.fecha);
  const pickup = formatEnglishTime(partido.fecha, -210);
  const preMatch = formatEnglishTime(partido.fecha, -120);
  const toStadium = formatEnglishTime(partido.fecha, -60);
  const kickoff = formatEnglishTime(partido.fecha);

  return [
    `Hi  👋🏻`,
    ``,
    `I am Anderson a huge Junior fan and have followed my club since I was a kid! This ${weekday} we will face _${partido.equipo_visitante}_! Without a doubt we will have great emotions.`,
    ``,
    `💡This is our itinerary:`,
    ``,
    `${pickup} - I will come and pick you up at the place where you are staying and departure to the ${partido.estadio} stadium.`,
    ``,
    `${preMatch} - Estimated arrival time for our pre-match meeting;`,
    ``,
    `${toStadium} - Time to go to the stadium;`,
    ``,
    `${kickoff} - Start of the match;`,
    ``,
    `➡️ In the preview of the game, Junior's fans gather in some streets near the ${partido.estadio} with lots of drinks and lots of music! It's a great time when we get in touch with local fans and exchange experiences with them!`,
    ``,
    `➡️ The authorities do not allow belt to enter the stadium and vape`,
    ``,
    `➡️  It is important then to follow all my guidelines.`,
    ``,
    `➡️ Before the game, if you wish, I can help you get team shirts at an affordable price.`,
  ];
}

function cartagenaItineraryLines(
  reservation: Reservation,
  partido: PartidoListItem,
): string[] {
  const weekday = formatEnglishWeekday(partido.fecha);
  const meetingPoint = reservation.meeting_point || "starting point";
  const startingPointMoment = formatEnglishTime(partido.fecha, -135);
  const preMatch = formatEnglishTime(partido.fecha, -105);
  const toStadium = formatEnglishTime(partido.fecha, -45);
  const kickoff = formatEnglishTime(partido.fecha);
  const isCup = partido.nombre_campeonato.toLowerCase().includes("cup");

  const lines = [
    `Hello!`,
    ``,
    `I'm Anderson, your local host for ${weekday}'s game!`,
    ``,
    `This day  we will face ${partido.equipo_visitante} for the ${partido.nombre_campeonato}!, without a doubt we will have great emotions!`,
    ``,
    `💡This is our itinerary:`,``,
    `📍${startingPointMoment} - We will meet at our starting point at the *"${meetingPoint}"* and departure to the ${partido.estadio} Stadium.`,``,
    
    `🚗 ${preMatch} - Estimated arrival time for our pre-match meeting;`,``,
    `🏟️ ${toStadium} - Time to go to the stadium;`,``,
    `⚽ ${kickoff} - Start of the match;`,``,

    `➡️ In the preview of the game, fans of the ${partido.equipo_local} gather in some streets near the ${partido.estadio} with lots of drinks and lots of music!`,
    `➡️ The authorities do not allow belts to enter the stadium.`,
  ];

  if (isCup) {
    lines.push(
      `➡️ This is a cup match, so emotions are always higher than normal. It is important then to follow all my guidelines.`,
    );
  }

  lines.push(
    `➡️ Before the game, if you wish, I can help you get team jerseys at an affordable price`,
    `➡️ After finishing the game we will take some time and we will also drive back to the place you are staying.`,
  );

  return lines;
}

function itineraryLines(
  reservation: Reservation,
  partido: PartidoListItem,
): string[] | null {
  const kind = localTeamKind(partido.equipo_local);
  if (kind === "junior") return juniorItineraryLines(partido);
  if (kind === "cartagena") return cartagenaItineraryLines(reservation, partido);
  return null;
}

export type WhatsAppShareKind = "welcome" | "itinerary";

export function buildWhatsAppShareUrl(
  reservation: Reservation,
  kind: WhatsAppShareKind,
  partido?: PartidoListItem | null,
): string | null {
  const digits = phoneDigitsForWhatsApp(reservation.phone);
  if (!digits) return null;

  const lines =
    kind === "welcome"
      ? welcomeLines(reservation)
      : partido
        ? itineraryLines(reservation, partido)
        : null;
  if (!lines) return null;

  const text = encodeURIComponent(lines.join("\n"));
  // wa.me redirects through a decoder that replaces 4-byte UTF-8 (emoji)
  // with U+FFFD. api.whatsapp.com/send keeps the encoded text intact.
  return `https://api.whatsapp.com/send?phone=${digits}&text=${text}`;
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
