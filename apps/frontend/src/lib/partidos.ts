import { apiJson } from "@/lib/api";
import type { Partido, PartidoListItem } from "@/types/partido";

export type PartidoListResponse = {
  total: number;
  items: PartidoListItem[];
};

export type FetchPartidosParams = {
  skip?: number;
  limit?: number;
  ciudad?: string;
  fecha_from?: string;
  fecha_to?: string;
  q?: string;
};

export async function fetchPartidos(
  params: FetchPartidosParams = {},
): Promise<PartidoListResponse> {
  const query = new URLSearchParams();
  query.set("skip", String(params.skip ?? 0));
  query.set("limit", String(params.limit ?? 100));
  if (params.ciudad) query.set("ciudad", params.ciudad);
  if (params.fecha_from) query.set("fecha_from", params.fecha_from);
  if (params.fecha_to) query.set("fecha_to", params.fecha_to);
  if (params.q) query.set("q", params.q);
  return apiJson<PartidoListResponse>(`/partidos?${query.toString()}`);
}

export async function fetchPartidoById(id: string): Promise<Partido> {
  return apiJson<Partido>(`/partidos/${id}`);
}

export type PartidoWritePayload = {
  equipo_local: string;
  equipo_visitante: string;
  nombre_campeonato: string;
  estadio: string;
  fecha: string;
  ciudad: string;
};

export async function createPartido(
  payload: PartidoWritePayload,
): Promise<Partido> {
  return apiJson<Partido>("/partidos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export type PartidoUpdatePayload = Partial<PartidoWritePayload>;

export async function updatePartido(
  id: string,
  payload: PartidoUpdatePayload,
): Promise<Partido> {
  return apiJson<Partido>(`/partidos/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deletePartido(id: string): Promise<void> {
  await apiJson<null>(`/partidos/${id}`, { method: "DELETE" });
}
