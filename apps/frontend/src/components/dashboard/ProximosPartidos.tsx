"use client";

import React from "react";
import Link from "next/link";
import { formatRawDateTime } from "@/components/reservations/reservationUtils";
import {
  ParticipantsBadge,
  ReservaBadge,
} from "@/components/partidos/PartidoBadges";
import type { PartidoListItem } from "@/types/partido";

type ProximosPartidosProps = {
  data: PartidoListItem[];
  loading?: boolean;
};

export default function ProximosPartidos({
  data,
  loading = false,
}: ProximosPartidosProps) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            Proximos Partidos
          </h3>
          <p className="mt-1 text-gray-500 text-theme-sm dark:text-gray-400">
            Próximos 5 partidos
          </p>
        </div>
        <Link
          href="/partidos"
          className="text-theme-xs font-medium text-brand-500 hover:underline"
        >
          Ver todos
        </Link>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : data.length === 0 ? (
        <p className="text-sm text-gray-500">No hay partidos próximos</p>
      ) : (
        <div className="flex gap-4 overflow-x-auto snap-x snap-mandatory pb-1 custom-scrollbar">
          {data.map((partido) => (
            <div
              key={partido.id}
              className="w-[min(100%,20rem)] shrink-0 snap-start rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-white/[0.02]"
            >
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <ReservaBadge count={partido.reservas_count} />
                <ParticipantsBadge count={partido.participants_count} />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="min-w-0 truncate text-sm font-semibold text-gray-800 dark:text-white/90">
                  {partido.equipo_local}
                </span>
                <span className="shrink-0 text-theme-xs text-gray-400">vs</span>
                <span className="min-w-0 truncate text-right text-sm font-semibold text-gray-800 dark:text-white/90">
                  {partido.equipo_visitante}
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-2 text-theme-xs text-gray-500 dark:text-gray-400">
                <span className="truncate">{formatRawDateTime(partido.fecha)}</span>
                <span className="truncate">{partido.ciudad}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
