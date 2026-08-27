"use client";

import { ApexOptions } from "apexcharts";
import dynamic from "next/dynamic";
import {
  formatMonthLabel,
  formatMoney,
  parseDecimal,
} from "@/lib/formatMoney";
import type { MonthlySalesPoint } from "@/lib/reports";

const ReactApexChart = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

type MonthlySalesChartProps = {
  data: MonthlySalesPoint[];
  loading?: boolean;
};

export default function MonthlySalesChart({
  data,
  loading = false,
}: MonthlySalesChartProps) {
  const categories = data.map((point) => formatMonthLabel(point.month));
  const profitSeries = data.map((point) => parseDecimal(point.profit));

  const options: ApexOptions = {
    colors: ["#465fff"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      type: "bar",
      height: 180,
      toolbar: { show: false },
    },
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: "39%",
        borderRadius: 5,
        borderRadiusApplication: "end",
      },
    },
    dataLabels: { enabled: false },
    stroke: {
      show: true,
      width: 4,
      colors: ["transparent"],
    },
    xaxis: {
      categories,
      axisBorder: { show: false },
      axisTicks: { show: false },
    },
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
      fontFamily: "Outfit",
    },
    yaxis: {
      labels: {
        formatter: (value) => formatMoney(value),
      },
    },
    grid: {
      yaxis: { lines: { show: true } },
    },
    fill: { opacity: 1 },
    tooltip: {
      y: {
        formatter: (val: number) => formatMoney(val),
      },
    },
  };

  const series = [{ name: "Profit", data: profitSeries }];

  return (
    <div className="h-full overflow-hidden rounded-2xl border border-gray-200 bg-white px-5 pt-5 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6 sm:pt-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Monthly Sales
        </h3>
        <p className="mt-1 text-gray-500 text-theme-sm dark:text-gray-400">
          Profit mensual (reservas confirmadas)
        </p>
      </div>

      {loading ? (
        <div className="flex h-[180px] items-center justify-center text-sm text-gray-500">
          Cargando…
        </div>
      ) : data.length === 0 ? (
        <div className="flex h-[180px] items-center justify-center text-sm text-gray-500">
          Sin datos
        </div>
      ) : (
        <div className="max-w-full overflow-x-auto custom-scrollbar">
          <div className="-ml-5 min-w-[650px] pl-2 xl:min-w-full">
            <ReactApexChart
              options={options}
              series={series}
              type="bar"
              height={180}
            />
          </div>
        </div>
      )}
    </div>
  );
}
