/** Partido (match) shapes aligned with API OpenAPI schemas. */

import type { ReservationListItem } from "@/types/reservation";

export type Campeonato =
  | "Colombian Cup"
  | "Colombian League"
  | "Copa Libertadores"
  | "Copa Sudamericana"
  | "Colombian Second Division League";

export const CAMPEONATO_OPTIONS: Campeonato[] = [
  "Colombian Cup",
  "Colombian League",
  "Copa Libertadores",
  "Copa Sudamericana",
  "Colombian Second Division League",
];

export type Estadio = "Jaime Morón" | "Romelio Martínez" | "Metropolitano";

export const ESTADIO_OPTIONS: Estadio[] = [
  "Jaime Morón",
  "Romelio Martínez",
  "Metropolitano",
];

/** Mirrors the backend's ``Ciudad`` enum — add new cities on both sides. */
export type Ciudad = "Barranquilla" | "Cartagena";

export const CIUDAD_OPTIONS: Ciudad[] = ["Barranquilla", "Cartagena"];

/** Slim row from ``GET /partidos`` (`PartidoShortItem`). */
export type PartidoListItem = {
  id: string;
  equipo_local: string;
  equipo_visitante: string;
  nombre_campeonato: Campeonato | string;
  estadio: Estadio | string;
  fecha: string;
  ciudad: Ciudad | string;
};

/** Full detail from ``GET /partidos/{id}`` (`PartidoResponse`). */
export type Partido = PartidoListItem & {
  created_at: string;
  updated_at: string;
  /** Non-deleted reservas linked to this partido; informational only. */
  reservas: ReservationListItem[];
};
