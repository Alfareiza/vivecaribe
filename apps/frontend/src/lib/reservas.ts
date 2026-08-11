import { apiJson } from "@/lib/api";
import type { Reservation, ReservationListItem } from "@/types/reservation";

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
  return apiJson<ReservaListResponse>(`/reservas?${query.toString()}`);
}

export async function fetchReservaById(id: string): Promise<Reservation> {
  return apiJson<Reservation>(`/reservas/${id}`);
}
