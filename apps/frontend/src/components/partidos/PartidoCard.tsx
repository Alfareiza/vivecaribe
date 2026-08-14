"use client";

import React from "react";
import { formatRawDateTime } from "@/components/reservations/reservationUtils";
import type { PartidoListItem } from "@/types/partido";

type PartidoCardProps = {
  partido: PartidoListItem;
  onClick: () => void;
};

export default function PartidoCard({ partido, onClick }: PartidoCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full flex-col items-start rounded-2xl border border-gray-200 bg-white p-5 text-left shadow-theme-xs transition hover:border-brand-300 hover:shadow-theme-sm dark:border-gray-800 dark:bg-white/[0.03] dark:hover:border-brand-800"
    >
      <div className="flex w-full items-center justify-between gap-3">
        <span className="min-w-0 truncate text-base font-semibold text-gray-800 dark:text-white/90">
          {partido.equipo_local}
        </span>
        <span className="shrink-0 text-theme-xs font-medium text-gray-400 dark:text-gray-500">
          vs
        </span>
        <span className="min-w-0 truncate text-right text-base font-semibold text-gray-800 dark:text-white/90">
          {partido.equipo_visitante}
        </span>
      </div>

      <div className="mt-3 flex w-full items-center justify-between gap-2 text-theme-xs text-gray-500 dark:text-gray-400">
        <span className="truncate">{formatRawDateTime(partido.fecha)}</span>
        <span className="truncate">{partido.ciudad}</span>
      </div>
    </button>
  );
}
