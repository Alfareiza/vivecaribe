"use client";

import React, { useCallback, useState } from "react";
import DatePicker from "@/components/form/date-picker";
import Select from "@/components/form/Select";
import { Dropdown } from "@/components/ui/dropdown/Dropdown";
import { toYmd } from "@/lib/formatMoney";
import { BOOKING_PROVIDER_OPTIONS } from "@/types/reservation";
import { PROVIDER_LABELS } from "@/components/reservations/reservationUtils";
import { FilterIcon } from "@/icons";

const ALL = "all";

const providerOptions = [
  { value: ALL, label: "Todos los proveedores" },
  ...BOOKING_PROVIDER_OPTIONS.map((value) => ({
    value,
    label: PROVIDER_LABELS[value] ?? value,
  })),
];

export type DashboardFilterValues = {
  booking_provider: string | null;
  fecha_from: string | null;
  fecha_to: string | null;
};

type DashboardFiltersProps = {
  values: DashboardFilterValues;
  onChange: (patch: Partial<DashboardFilterValues>) => void;
};

export default function DashboardFilters({
  values,
  onChange,
}: DashboardFiltersProps) {
  const [filterMenuOpen, setFilterMenuOpen] = useState(false);
  const [filterResetToken, setFilterResetToken] = useState(0);

  const activeFilterCount =
    (values.booking_provider ? 1 : 0) + (values.fecha_from || values.fecha_to ? 1 : 0);

  const clearFilters = () => {
    setFilterResetToken((token) => token + 1);
    onChange({
      booking_provider: null,
      fecha_from: null,
      fecha_to: null,
    });
  };

  const handleFechaEventoRangeClose = useCallback(
    (selectedDates: Date[]) => {
      const from = selectedDates[0] ? toYmd(selectedDates[0]) : null;
      const to = selectedDates[1]
        ? toYmd(selectedDates[1])
        : selectedDates[0]
          ? toYmd(selectedDates[0])
          : null;
      onChange({
        fecha_from: from,
        fecha_to: to,
      });
    },
    [onChange],
  );

  return (
    <div className="relative inline-block self-start">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={filterMenuOpen}
        onClick={() => setFilterMenuOpen((open) => !open)}
        className="dropdown-toggle inline-flex h-11 items-center gap-2 rounded-lg border border-gray-300 px-4 text-sm font-medium text-gray-700 shadow-theme-xs transition-colors hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
      >
        <FilterIcon className="size-4" />
        {/* Filtros */}
        {activeFilterCount > 0 ? (
          <span className="inline-flex size-5 items-center justify-center rounded-full bg-brand-500 text-xs font-semibold text-white">
            {activeFilterCount}
          </span>
        ) : null}
      </button>
      <Dropdown
        isOpen={filterMenuOpen}
        onClose={() => setFilterMenuOpen(false)}
        className="w-72 p-4"
      >
        <div className="space-y-3">
          <Select
            key={`provider-${filterResetToken}`}
            options={providerOptions}
            placeholder="Proveedor"
            defaultValue={values.booking_provider ?? ALL}
            onChange={(value) => {
              onChange({
                booking_provider: !value || value === ALL ? null : value,
              });
            }}
          />
          <div>
            <p className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400">
              Fecha evento
            </p>
            <DatePicker
              key={`fecha-${filterResetToken}`}
              id="dashboard-fecha-evento-range"
              mode="range"
              placeholder="Desde — Hasta"
              onClose={handleFechaEventoRangeClose}
            />
          </div>
          {activeFilterCount > 0 ? (
            <button
              type="button"
              onClick={clearFilters}
              className="text-theme-xs font-medium text-brand-500 hover:underline"
            >
              Limpiar filtros
            </button>
          ) : null}
        </div>
      </Dropdown>
    </div>
  );
}
