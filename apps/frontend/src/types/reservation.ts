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

export type TipoTour = "football tour" | "city tour";

export type MeetingPoint = "old shoes monument" | "Door-to-Door";

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
  partido_id: string | null;
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
  notas_cliente: string | null;
  tipo_tour: TipoTour | string | null;
  notas_personales: string | null;
  costos: string | null;
  meeting_point: MeetingPoint | string | null;
  lugar_de_recogida: string | null;
  income_estimado: string | null;
  profit: string | null;
  percentage_profit: string | null;
  menores_de_edad: boolean;
  paid_at: string | null;
};
