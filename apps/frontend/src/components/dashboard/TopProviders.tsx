"use client";

import React from "react";
import ProviderLogo from "@/components/reservations/ProviderLogo";
import { PROVIDER_LABELS } from "@/components/reservations/reservationUtils";
import { formatMoney, parseDecimal } from "@/lib/formatMoney";
import type { TopProviderItem } from "@/lib/reports";

type TopProvidersProps = {
  data: TopProviderItem[];
  loading?: boolean;
};

export default function TopProviders({ data, loading = false }: TopProvidersProps) {
  const maxProfit = Math.max(...data.map((item) => parseDecimal(item.profit)), 1);

  return (
    <div className="h-full rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] sm:p-6">
      <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
        Top Providers
      </h3>
      <p className="mt-1 text-gray-500 text-theme-sm dark:text-gray-400">
        Proveedores por profit
      </p>

      {loading ? (
        <p className="mt-6 text-sm text-gray-500">Cargando…</p>
      ) : data.length === 0 ? (
        <p className="mt-6 text-sm text-gray-500">Sin datos</p>
      ) : (
        <div className="mt-6 space-y-5">
          {data.map((item, index) => {
            const profit = parseDecimal(item.profit);
            const width = Math.max(8, Math.round((profit / maxProfit) * 100));
            const label = PROVIDER_LABELS[item.provider] ?? item.provider;
            return (
              <div key={item.provider} className="flex items-center gap-3">
                <span className="w-5 shrink-0 text-sm font-medium text-gray-500">
                  {index + 1}
                </span>
                <ProviderLogo provider={item.provider} size={32} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate font-medium text-gray-800 text-theme-sm dark:text-white/90">
                      {label}
                    </p>
                    <span className="shrink-0 font-semibold text-gray-800 text-theme-sm dark:text-white/90">
                      {formatMoney(profit)}
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-800">
                    <div
                      className="h-1.5 rounded-full bg-brand-500"
                      style={{ width: `${width}%` }}
                    />
                  </div>
                  <p className="mt-1 text-gray-500 text-theme-xs dark:text-gray-400">
                    {item.reservas} reservas · {item.participants} participantes
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
