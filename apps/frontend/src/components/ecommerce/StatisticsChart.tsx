"use client";

import dynamic from "next/dynamic";
import { ApexOptions } from "apexcharts";
import {
  formatMonthLabel,
  formatMoney,
  parseDecimal,
} from "@/lib/formatMoney";
import type { MonthlyStatisticsPoint } from "@/lib/reports";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type StatisticsChartProps = {
  data: MonthlyStatisticsPoint[];
  loading?: boolean;
};

export default function StatisticsChart({
  data,
  loading = false,
}: StatisticsChartProps) {
  const categories = data.map((point) => formatMonthLabel(point.month));
  const incomeSeries = data.map((point) => parseDecimal(point.income_final));
  const costosSeries = data.map((point) => parseDecimal(point.costos));

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
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Statistics
        </h3>
        <p className="mt-1 text-gray-500 text-theme-sm dark:text-gray-400">
          Ingreso final vs gastos por mes
        </p>
      </div>

      {loading ? (
        <div className="flex h-[310px] items-center justify-center text-sm text-gray-500">
          Cargando…
        </div>
      ) : data.length === 0 ? (
        <div className="flex h-[310px] items-center justify-center text-sm text-gray-500">
          Sin datos para el periodo seleccionado
        </div>
      ) : (
        <div className="max-w-full overflow-x-auto custom-scrollbar">
          <div className="min-w-[700px] xl:min-w-full">
            <Chart options={options} series={series} type="area" height={310} />
          </div>
        </div>
      )}
    </div>
  );
}
