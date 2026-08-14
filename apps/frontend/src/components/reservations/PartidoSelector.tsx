"use client";

import React, { useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import { updateReserva } from "@/lib/reservas";
import { fetchPartidoById, fetchPartidos } from "@/lib/partidos";
import type { PartidoListItem } from "@/types/partido";
import { formatDisplayDateTime } from "./reservationUtils";

type PartidoSelectorProps = {
  reservationId: string;
  ciudadExperiencia: string;
  fechaEvento: string | null;
  partidoId: string | null;
  onChanged: (partidoId: string | null) => void;
};

function partidoLabel(partido: PartidoListItem): string {
  return `${partido.equipo_local} vs ${partido.equipo_visitante} — ${partido.ciudad} (${formatDisplayDateTime(partido.fecha)})`;
}

/** Same calendar day as ``fechaEvento``'s raw Y-M-D, as a UTC day window. */
function dayWindow(fechaEvento: string): { from: string; to: string } | null {
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(fechaEvento);
  if (!match) return null;
  const day = match[1];
  return { from: `${day}T00:00:00Z`, to: `${day}T23:59:59Z` };
}

const selectClasses =
  "h-11 w-full appearance-none rounded-lg border border-gray-300 bg-transparent px-3 py-2.5 pr-9 text-theme-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800";

/**
 * Options are limited to partidos on the reserva's own event day + city —
 * same-day fixture counts are small enough that a full-text search fallback
 * isn't needed.
 */
export default function PartidoSelector({
  reservationId,
  ciudadExperiencia,
  fechaEvento,
  partidoId,
  onChanged,
}: PartidoSelectorProps) {
  const [suggested, setSuggested] = useState<PartidoListItem[]>([]);
  const [linked, setLinked] = useState<PartidoListItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const window = fechaEvento ? dayWindow(fechaEvento) : null;
        const response = await fetchPartidos({
          ciudad: ciudadExperiencia || undefined,
          fecha_from: window?.from,
          fecha_to: window?.to,
          limit: 20,
        });
        if (!cancelled) setSuggested(response.items);
      } catch {
        if (!cancelled) setSuggested([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ciudadExperiencia, fechaEvento]);

  useEffect(() => {
    let cancelled = false;
    if (!partidoId) {
      setLinked(null);
      return;
    }
    void (async () => {
      try {
        const fresh = await fetchPartidoById(partidoId);
        if (!cancelled) setLinked(fresh);
      } catch {
        if (!cancelled) setLinked(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [partidoId]);

  const options = useMemo(() => {
    const byId = new Map<string, PartidoListItem>();
    for (const item of suggested) byId.set(item.id, item);
    if (linked) byId.set(linked.id, linked);
    return Array.from(byId.values());
  }, [suggested, linked]);

  async function handleSelect(nextId: string) {
    const previous = partidoId;
    const next = nextId || null;
    if (next === previous) return;
    onChanged(next);
    setError(null);
    setSaving(true);
    try {
      await updateReserva(reservationId, { partido_id: next });
    } catch (err) {
      onChanged(previous);
      setError(
        err instanceof ApiError ? err.message : "No se pudo guardar el partido",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-2">
      <select
        className={selectClasses}
        value={partidoId ?? ""}
        disabled={saving}
        onChange={(e) => void handleSelect(e.target.value)}
      >
        <option value="">Sin partido asociado</option>
        {options.map((partido) => (
          <option key={partido.id} value={partido.id}>
            {partidoLabel(partido)}
          </option>
        ))}
      </select>

      {error ? (
        <p className="text-theme-xs text-error-600 dark:text-error-400">
          {error}
        </p>
      ) : null}
    </div>
  );
}
