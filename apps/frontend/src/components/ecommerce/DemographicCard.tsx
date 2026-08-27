"use client";

import CountryMap from "./CountryMap";
import type { DemographicItem } from "@/lib/reports";

type DemographicCardProps = {
  data: DemographicItem[];
  loading?: boolean;
};

export default function DemographicCard({
  data,
  loading = false,
}: DemographicCardProps) {
  const maxParticipants = Math.max(
    ...data.map((item) => item.participants),
    1,
  );

  return (
    <div className="h-full rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] sm:p-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Customers Demographic
        </h3>
        <p className="mt-1 text-gray-500 text-theme-sm dark:text-gray-400">
          Participantes por país de origen
        </p>
      </div>

      <div className="my-6 overflow-hidden rounded-2xl border border-gray-200 bg-gray-50 px-4 py-6 dark:border-gray-800 dark:bg-gray-900 sm:px-6">
        <div className="mapOne map-btn -mx-4 -my-6 h-[212px] w-full sm:-mx-6">
          <CountryMap />
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : data.length === 0 ? (
        <p className="text-sm text-gray-500">Sin datos</p>
      ) : (
        <div className="space-y-5">
          {data.map((item) => {
            const percentage = Math.round(
              (item.participants / maxParticipants) * 100,
            );
            return (
              <div
                key={item.country}
                className="flex items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-gray-800 text-theme-sm dark:text-white/90">
                    {item.country || "Desconocido"}
                  </p>
                  <span className="block text-gray-500 text-theme-xs dark:text-gray-400">
                    {item.participants.toLocaleString("es-CO")} participantes ·{" "}
                    {item.reservas} reservas
                  </span>
                </div>
                <div className="flex w-full max-w-[140px] items-center gap-3">
                  <div className="relative block h-2 w-full max-w-[100px] rounded-sm bg-gray-200 dark:bg-gray-800">
                    <div
                      className="absolute left-0 top-0 flex h-full items-center justify-center rounded-sm bg-brand-500"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <p className="font-medium text-gray-800 text-theme-sm dark:text-white/90">
                    {percentage}%
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
