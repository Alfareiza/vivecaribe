/** Reservation shapes aligned with API OpenAPI schemas. */

import type { GastoShareItem } from "@/types/gasto";

export type BookingProvider =
  | "getyourguide"
  | "viator"
  | "homefans"
  | "propio"
  | "vayara"
  | "otro"
  | "airbnb";

export const BOOKING_PROVIDER_OPTIONS: BookingProvider[] = [
  "getyourguide",
  "viator",
  "homefans",
  "propio",
  "vayara",
  "otro",
  "airbnb",
];

export type ReservaEstado =
  | "en_progreso"
  | "confirmada"
  | "cancelada"
  | "error";

export type TipoTour = "football tour" | "city tour";

export type MeetingPoint = "old shoes monument" | "Door-to-Door";

/** Slim row from ``GET /reservas`` (`ReservaShortItem`). */
export type ReservationListItem = {
  id: string;
  booking_provider: BookingProvider | string;
  estado: ReservaEstado | string;
  ciudad_experiencia: string;
  nombre_experiencia: string;
  participants: number;
  pais_del_visitante: string;
  phone: string;
  fecha_evento: string | null;
  customer_name: string;
  moneda: string;
  price: string;
  income: string;
  partido_id: string | null;
  es_hoy: boolean;
};

/** Full detail from ``GET /reservas/{id}`` (`ReservaResponse`). */
export type Reservation = ReservationListItem & {
  source: string;
  reserva_reference: string;
  sender: string | null;
  motivo_cancelacion: string | null;
  subject: string | null;
  fecha_email_recibido: string | null;
  notificado_whatsapp: boolean;
  email_message_id: string | null;
  user_id: string | null;
  created_at: string;
  updated_at: string;
  notas_cliente: string | null;
  tipo_tour: TipoTour | string | null;
  notas_personales: string | null;
  /** Derived from this reserva's share of its partido's gastos; not operator-editable. */
  costos: string | null;
  meeting_point: MeetingPoint | string | null;
  lugar_de_recogida: string | null;
  income_estimado: string | null;
  trm_estimado: string | null;
  trm_final: string | null;
  income_final: string | null;
  profit: string | null;
  percentage_profit: string | null;
  menores_de_edad: boolean;
  paid_at: string | null;
  /** This reserva's computed share of each of its partido's registered gasto categories. */
  gastos: GastoShareItem[];
  /** Sum of this reserva's share across all gasto categories. */
  gastos_total: string;
};
