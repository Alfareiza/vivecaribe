import { apiJson } from "@/lib/api";
import type {
  BookingProvider,
  MeetingPoint,
  Reservation,
  ReservationListItem,
  ReservaEstado,
  TipoTour,
} from "@/types/reservation";

export type ReservaListResponse = {
  total: number;
  items: ReservationListItem[];
};

export type FetchReservasParams = {
  skip?: number;
  limit?: number;
  estado?: string;
  booking_provider?: string;
  fecha_evento_from?: string;
  fecha_evento_to?: string;
  ciudad?: string;
  unassigned_only?: boolean;
};

export async function fetchReservas(
  params: FetchReservasParams = {},
): Promise<ReservaListResponse> {
  const query = new URLSearchParams();
  query.set("skip", String(params.skip ?? 0));
  query.set("limit", String(params.limit ?? 20));
  if (params.estado) query.set("estado", params.estado);
  if (params.booking_provider) {
    query.set("booking_provider", params.booking_provider);
  }
  if (params.fecha_evento_from) {
    query.set("fecha_evento_from", params.fecha_evento_from);
  }
  if (params.fecha_evento_to) {
    query.set("fecha_evento_to", params.fecha_evento_to);
  }
  if (params.ciudad) query.set("ciudad", params.ciudad);
  if (params.unassigned_only) query.set("unassigned_only", "true");
  return apiJson<ReservaListResponse>(`/reservas?${query.toString()}`);
}

export async function fetchReservaById(id: string): Promise<Reservation> {
  return apiJson<Reservation>(`/reservas/${id}`);
}

export type ReservaUpdatePayload = Partial<
  Pick<
    Reservation,
    | "estado"
    | "booking_provider"
    | "nombre_experiencia"
    | "ciudad_experiencia"
    | "fecha_evento"
    | "participants"
    | "customer_name"
    | "phone"
    | "pais_del_visitante"
    | "moneda"
    | "price"
    | "income"
    | "notificado_whatsapp"
    | "subject"
    | "notas_cliente"
    | "tipo_tour"
    | "notas_personales"
    | "meeting_point"
    | "lugar_de_recogida"
    | "income_estimado"
    | "trm_estimado"
    | "trm_final"
    | "menores_de_edad"
    | "partido_id"
  >
>;

export async function updateReserva(
  id: string,
  payload: ReservaUpdatePayload,
): Promise<Reservation> {
  return apiJson<Reservation>(`/reservas/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export type ReservaCreatePayload = {
  source: string;
  booking_provider: BookingProvider | string;
  reserva_reference: string;
  sender?: string | null;
  estado: ReservaEstado | string;
  subject?: string | null;
  fecha_email_recibido?: string | null;
  nombre_experiencia: string;
  ciudad_experiencia: string;
  fecha_evento?: string | null;
  participants: number;
  customer_name: string;
  phone?: string;
  pais_del_visitante?: string;
  moneda?: string;
  price: string;
  income: string;
  notificado_whatsapp?: boolean;
  notas_cliente?: string | null;
  tipo_tour?: TipoTour | string | null;
  notas_personales?: string | null;
  meeting_point?: MeetingPoint | string | null;
  lugar_de_recogida?: string | null;
  income_estimado?: string | null;
  trm_estimado?: string | null;
  menores_de_edad?: boolean;
  partido_id?: string | null;
};

export async function createReserva(
  payload: ReservaCreatePayload,
): Promise<Reservation> {
  return apiJson<Reservation>("/reservas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteReserva(id: string): Promise<void> {
  await apiJson<null>(`/reservas/${id}`, { method: "DELETE" });
}

export async function cancelReserva(
  id: string,
  motivo_cancelacion: string,
): Promise<Reservation> {
  return apiJson<Reservation>(`/reservas/${id}/cancelar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ motivo_cancelacion }),
  });
}
