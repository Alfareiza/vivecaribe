"use client";

import { ApexOptions } from "apexcharts";
import dynamic from "next/dynamic";
import { formatMonthLabel } from "@/lib/formatMoney";
import type { TemporadaPoint } from "@/lib/reports";

const ReactApexChart = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const CITY_COLORS = ["#465fff", "#FF7A59", "#55A868", "#8172B3"];

type TemporadaChartProps = {
  data: TemporadaPoint[];
  loading?: boolean;
};

export default function TemporadaChart({
  data,
  loading = false,
}: TemporadaChartProps) {
  const months = [...new Set(data.map((point) => point.month))];
  const cities = [...new Set(data.map((point) => point.city))];
  const categories = months.map((month) => formatMonthLabel(month));
  const series = cities.map((city) => ({
    name: city,
    data: months.map((month) => {
      const point = data.find(
        (item) => item.month === month && item.city === city,
      );
      return point?.participants ?? 0;
    }),
  }));

  const options: ApexOptions = {
    colors: CITY_COLORS,
    chart: {
      fontFamily: "Outfit, sans-serif",
      type: "bar",
      height: 220,
      toolbar: { show: false },
    },
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: "48%",
        borderRadius: 5,
        borderRadiusApplication: "end",
      },
    },
    dataLabels: { enabled: false },
    stroke: {
      show: true,
      width: 3,
      colors: ["transparent"],
    },
    xaxis: {
      categories,
      axisBorder: { show: false },
      axisTicks: { show: false },
    },
    yaxis: {
      labels: {
        formatter: (value) => String(Math.round(value)),
      },
    },
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
      fontFamily: "Outfit",
    },
    grid: {
      yaxis: { lines: { show: true } },
    },
    fill: { opacity: 1 },
    tooltip: {
      y: {
        formatter: (val: number) =>
          `${val} participante${val === 1 ? "" : "s"}`,
      },
    },
  };

  return (
    <div className="h-full overflow-hidden rounded-2xl border border-gray-200 bg-white px-5 pt-5 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6 sm:pt-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Temporada
        </h3>
        <p className="mt-1 text-gray-500 text-theme-sm dark:text-gray-400">
          Participantes por mes y ciudad
        </p>
      </div>

      {loading ? (
        <div className="flex h-[220px] items-center justify-center text-sm text-gray-500">
          Cargando…
        </div>
      ) : data.length === 0 ? (
        <div className="flex h-[220px] items-center justify-center text-sm text-gray-500">
          Sin datos
        </div>
      ) : (
        <div className="max-w-full overflow-x-auto custom-scrollbar">
          <div className="-ml-5 min-w-[280px] pl-2 xl:min-w-full">
            <ReactApexChart
              options={options}
              series={series}
              type="bar"
              height={220}
            />
          </div>
        </div>
      )}
    </div>
  );
}
