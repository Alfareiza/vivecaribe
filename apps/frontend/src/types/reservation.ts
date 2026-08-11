/** Reservation shapes aligned with API OpenAPI schemas. */

export type BookingProvider =
  | "getyourguide"
  | "viator"
  | "homefans"
  | "propio";

export type ReservaEstado =
  | "en_progreso"
  | "confirmada"
  | "cancelada"
  | "error";

/** Slim row from ``GET /reservas`` (`ReservaShortItem`). */
export type ReservationListItem = {
  id: string;
  booking_provider: BookingProvider | string;
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
  es_hoy: boolean;
};

/** Full detail from ``GET /reservas/{id}`` (`ReservaResponse`). */
export type Reservation = ReservationListItem & {
  source: string;
  reserva_reference: string;
  sender: string;
  estado: ReservaEstado | string;
  subject: string;
  fecha_email_recibido: string;
  notificado_whatsapp: boolean;
  email_message_id: string | null;
  user_id: string | null;
  created_at: string;
  updated_at: string;
};
