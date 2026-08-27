"use client";

import { useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import { ApexOptions } from "apexcharts";
import DatePicker from "@/components/form/date-picker";
import {
  formatMonthLabel,
  formatMoney,
  parseDecimal,
  toYmd,
} from "@/lib/formatMoney";
import type { MonthlyStatisticsPoint } from "@/lib/reports";
import { monthsInRange, type DateRange, type StatsPreset } from "@/lib/statsPeriod";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

const PRESET_BUTTONS: { id: Exclude<StatsPreset, "custom">; label: string }[] = [
  { id: "this_year", label: "Este año" },
  { id: "this_month", label: "Este mes" },
  { id: "last_semester", label: "Último semestre" },
  { id: "last_year", label: "Año pasado" },
];

type StatisticsChartProps = {
  data: MonthlyStatisticsPoint[];
  loading?: boolean;
  phrase: string;
  preset: StatsPreset;
  dateRange: DateRange;
  datePickerKey: number;
  onPreset: (preset: Exclude<StatsPreset, "custom">) => void;
  onCustomRange: (range: DateRange) => void;
};

export default function StatisticsChart({
  data,
  loading = false,
  phrase,
  preset,
  dateRange,
  datePickerKey,
  onPreset,
  onCustomRange,
}: StatisticsChartProps) {
  const handleDateClose = useCallback(
    (selectedDates: Date[]) => {
      const from = selectedDates[0] ? toYmd(selectedDates[0]) : null;
      const to = selectedDates[1] ? toYmd(selectedDates[1]) : from;
      if (from && to) onCustomRange({ from, to });
    },
    [onCustomRange],
  );
  const defaultDate = useMemo(
    () => [dateRange.from, dateRange.to],
    [dateRange.from, dateRange.to],
  );

  const filled = useMemo(() => {
    const byMonth = new Map(
      data.map((point) => [point.month.slice(0, 7), point]),
    );
    return monthsInRange(dateRange.from, dateRange.to).map((month) => {
      const point = byMonth.get(month.slice(0, 7));
      return {
        month,
        income_final: point?.income_final ?? "0",
        costos: point?.costos ?? "0",
      };
    });
  }, [data, dateRange.from, dateRange.to]);

  const categories = filled.map((point) => formatMonthLabel(point.month));
  const incomeSeries = filled.map((point) => parseDecimal(point.income_final));
  const costosSeries = filled.map((point) => parseDecimal(point.costos));

  const options: ApexOptions = {
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
    },
    colors: ["#465FFF", "#9CB9FF"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      height: 310,
      type: "line",
      toolbar: { show: false },
    },
    stroke: {
      curve: "straight",
      width: [2, 2],
    },
    fill: {
      type: "gradient",
      gradient: {
        opacityFrom: 0.55,
        opacityTo: 0,
      },
    },
    markers: {
      size: 0,
      strokeColors: "#fff",
      strokeWidth: 2,
      hover: { size: 6 },
    },
    grid: {
      xaxis: { lines: { show: false } },
      yaxis: { lines: { show: true } },
    },
    dataLabels: { enabled: false },
    tooltip: { enabled: true },
    xaxis: {
      type: "category",
      categories,
      axisBorder: { show: false },
      axisTicks: { show: false },
      labels: {
        hideOverlappingLabels: false,
        rotate: 0,
        trim: false,
      },
    },
    yaxis: {
      labels: {
        formatter: (value) => formatMoney(value),
        style: {
          fontSize: "12px",
          colors: ["#6B7280"],
        },
      },
    },
  };

  const series = [
    { name: "Ingreso final", data: incomeSeries },
    { name: "Gastos", data: costosSeries },
  ];

  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-5 pb-5 pt-5 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6 sm:pt-6">
      <div className="mb-6 flex flex-col gap-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            Statistics
          </h3>
          <p className="mt-1 text-gray-500 text-theme-sm dark:text-gray-400">
            Ingreso final vs gastos por mes. {phrase}
          </p>
        </div>
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
          <div className="flex flex-wrap items-center gap-2">
            {PRESET_BUTTONS.map((button) => {
              const active = preset === button.id;
              return (
                <button
                  key={button.id}
                  type="button"
                  onClick={() => onPreset(button.id)}
                  className={
                    active
                      ? "inline-flex h-11 items-center rounded-lg bg-brand-500 px-3 text-sm font-medium text-white"
                      : "inline-flex h-11 items-center rounded-lg border border-gray-300 px-3 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
                  }
                >
                  {button.label}
                </button>
              );
            })}
          </div>
          <div className="w-full lg:w-64">
            <DatePicker
              key={`stats-fecha-${datePickerKey}`}
              id="statistics-fecha-range"
              mode="range"
              placeholder="Desde — Hasta"
              defaultDate={defaultDate}
              onClose={handleDateClose}
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex h-[310px] items-center justify-center text-sm text-gray-500">
          Cargando…
        </div>
      ) : filled.length === 0 ? (
        <div className="flex h-[310px] items-center justify-center text-sm text-gray-500">
          Sin datos para el periodo seleccionado
        </div>
      ) : (
        <div className="max-w-full overflow-x-auto custom-scrollbar">
          <div className="min-w-[700px] xl:min-w-full">
            <Chart
              key={`${dateRange.from}-${dateRange.to}`}
              options={options}
              series={series}
              type="area"
              height={310}
            />
          </div>
        </div>
      )}
    </div>
  );
}
