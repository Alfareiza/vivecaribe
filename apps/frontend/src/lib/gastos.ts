import { apiJson } from "@/lib/api";
import type { Partido } from "@/types/partido";
import type { GastoCategoria } from "@/types/gasto";

/**
 * Set (create or update) the amount for one gasto category on a partido.
 * Returns the full updated partido (reservas' recomputed ``costos`` and
 * ``gastos`` shares included).
 *
 * ``categoria`` travels as a query param, not a path segment — some
 * category labels (e.g. "Comida y/o Snacks") contain a literal "/", which
 * breaks path-segment routing even percent-encoded.
 */
export async function upsertGasto(
  partidoId: string,
  categoria: GastoCategoria,
  monto: string,
): Promise<Partido> {
  const query = new URLSearchParams({ categoria });
  return apiJson<Partido>(`/partidos/${partidoId}/gastos?${query}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ monto }),
  });
}

/** Remove one gasto category's amount from a partido. Returns the updated partido. */
export async function deleteGasto(
  partidoId: string,
  categoria: GastoCategoria,
): Promise<Partido> {
  const query = new URLSearchParams({ categoria });
  return apiJson<Partido>(`/partidos/${partidoId}/gastos?${query}`, {
    method: "DELETE",
  });
}
