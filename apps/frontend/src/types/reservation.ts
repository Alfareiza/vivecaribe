/** Reservation shape aligned with API `ReservaResponse` (OpenAPI). */

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

export type Reservation = {
  id: string;
  source: string;
  booking_provider: BookingProvider | string;
  reserva_reference: string;
  sender: string;
  estado: ReservaEstado | string;
  subject: string;
  fecha_email_recibido: string;
  nombre_experiencia: string;
  ciudad_experiencia: string;
  fecha_evento: string | null;
  participants: number;
  customer_name: string;
  phone: string;
  pais_del_visitante: string;
  moneda: string;
  price: string;
  income: string;
  notificado_whatsapp: boolean;
  email_message_id: string | null;
  user_id: string | null;
  created_at: string;
  updated_at: string;
};
