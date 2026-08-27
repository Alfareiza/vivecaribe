"use client";

import React from "react";
import ProviderLogo from "@/components/reservations/ProviderLogo";
import { PROVIDER_LABELS } from "@/components/reservations/reservationUtils";
import { formatMoney, parseDecimal } from "@/lib/formatMoney";
import type { ProviderCardItem } from "@/lib/reports";

type ProviderCardsProps = {
  data: ProviderCardItem[];
  loading?: boolean;
};

export default function ProviderCards({
  data,
  loading = false,
}: ProviderCardsProps) {
  if (loading) {
    return (
      <p className="col-span-12 text-sm text-gray-500">Cargando proveedores…</p>
    );
  }

  if (data.length === 0) {
    return (
      <p className="col-span-12 text-sm text-gray-500">
        Sin proveedores con reservas en el periodo
      </p>
    );
  }

  return (
    <>
      {data.map((item) => {
        const profit = parseDecimal(item.profit);
        const label = PROVIDER_LABELS[item.provider] ?? item.provider;
        return (
          <div
            key={item.provider}
            className="col-span-12 sm:col-span-6 xl:col-span-3"
          >
            <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
              <div className="flex items-center gap-3">
                <ProviderLogo provider={item.provider} size={48} />
                <div className="min-w-0">
                  <p className="truncate font-semibold text-gray-800 dark:text-white/90">
                    {label}
                  </p>
                  {/* <p className="text-theme-xs text-gray-500 dark:text-gray-400"> */}
                    {/* {item.provider} */}
                  {/* </p> */}
                </div>
              </div>
              <div className="mt-5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-theme-sm text-gray-500 dark:text-gray-400">
                    Profit
                  </span>
                  <span className="font-bold text-gray-800 text-title-sm dark:text-white/90">
                    {formatMoney(profit)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-theme-sm">
                  <span className="text-gray-500 dark:text-gray-400">
                    Participantes
                  </span>
                  <span className="font-medium text-gray-800 dark:text-white/90">
                    {item.participants.toLocaleString("es-CO")}
                  </span>
                </div>
                <div className="flex items-center justify-between text-theme-sm">
                  <span className="text-gray-500 dark:text-gray-400">
                    Reservas
                  </span>
                  <span className="font-medium text-gray-800 dark:text-white/90">
                    {item.reservas.toLocaleString("es-CO")}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
}
