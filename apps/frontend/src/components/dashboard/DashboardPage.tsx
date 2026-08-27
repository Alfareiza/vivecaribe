"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import DemographicCard from "@/components/ecommerce/DemographicCard";
import { EcommerceMetrics } from "@/components/ecommerce/EcommerceMetrics";
import MonthlySalesChart from "@/components/ecommerce/MonthlySalesChart";
import StatisticsChart from "@/components/ecommerce/StatisticsChart";
import DashboardFilters, {
  type DashboardFilterValues,
} from "@/components/dashboard/DashboardFilters";
import ProviderCards from "@/components/dashboard/ProviderCards";
import ProximosPartidos from "@/components/dashboard/ProximosPartidos";
import TopCities from "@/components/dashboard/TopCities";
import TopProviders from "@/components/dashboard/TopProviders";
import { Dropdown } from "@/components/ui/dropdown/Dropdown";
import { DropdownItem } from "@/components/ui/dropdown/DropdownItem";
import { MoreDotIcon } from "@/icons";
import { parseDecimal } from "@/lib/formatMoney";
import {
  fetchReportDemographics,
  fetchReportMonthlySales,
  fetchReportProviders,
  fetchReportProximosPartidos,
  fetchReportStatistics,
  fetchReportSummary,
  fetchReportTopCities,
  fetchReportTopProviders,
  type DemographicItem,
  type MonthlySalesPoint,
  type MonthlyStatisticsPoint,
  type ProviderCardItem,
  type ReportFilters,
  type ReportSummary,
  type TopCityItem,
  type TopProviderItem,
} from "@/lib/reports";
import type { PartidoListItem } from "@/types/partido";

const EMPTY_SUMMARY: ReportSummary = {
  participants: 0,
  reservas: 0,
  profit: "0",
  partidos: 0,
};

export default function DashboardPage() {
  const [filters, setFilters] = useState<DashboardFilterValues>({
    booking_provider: null,
    fecha_from: null,
    fecha_to: null,
  });
  const [shareOpen, setShareOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<ReportSummary>(EMPTY_SUMMARY);
  const [statistics, setStatistics] = useState<MonthlyStatisticsPoint[]>([]);
  const [monthlySales, setMonthlySales] = useState<MonthlySalesPoint[]>([]);
  const [topProviders, setTopProviders] = useState<TopProviderItem[]>([]);
  const [topCities, setTopCities] = useState<TopCityItem[]>([]);
  const [demographics, setDemographics] = useState<DemographicItem[]>([]);
  const [providers, setProviders] = useState<ProviderCardItem[]>([]);
  const [proximosPartidos, setProximosPartidos] = useState<PartidoListItem[]>(
    [],
  );

  function handleFilterChange(patch: Partial<DashboardFilterValues>) {
    setFilters((prev) => ({ ...prev, ...patch }));
  }

  const apiFilters: ReportFilters = useMemo(
    () => ({
      fecha_from: filters.fecha_from ?? undefined,
      fecha_to: filters.fecha_to ?? undefined,
      booking_provider: filters.booking_provider ?? undefined,
    }),
    [filters],
  );

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [
        summaryData,
        statisticsData,
        monthlySalesData,
        topProvidersData,
        topCitiesData,
        demographicsData,
        providersData,
        proximosData,
      ] = await Promise.all([
        fetchReportSummary(apiFilters),
        fetchReportStatistics(apiFilters),
        fetchReportMonthlySales(apiFilters),
        fetchReportTopProviders(apiFilters),
        fetchReportTopCities(apiFilters),
        fetchReportDemographics(apiFilters),
        fetchReportProviders(apiFilters),
        fetchReportProximosPartidos(),
      ]);
      setSummary(summaryData);
      setStatistics(statisticsData);
      setMonthlySales(monthlySalesData);
      setTopProviders(topProvidersData);
      setTopCities(topCitiesData);
      setDemographics(demographicsData);
      setProviders(providersData);
      setProximosPartidos(proximosData);
    } catch {
      setSummary(EMPTY_SUMMARY);
      setStatistics([]);
      setMonthlySales([]);
      setTopProviders([]);
      setTopCities([]);
      setDemographics([]);
      setProviders([]);
      setProximosPartidos([]);
    } finally {
      setLoading(false);
    }
  }, [apiFilters]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  function handleScreenshot() {
    setShareOpen(false);
    window.print();
  }

  return (
    <div id="dashboard-content" className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-end">
        <DashboardFilters values={filters} onChange={handleFilterChange} />
        <div className="relative dashboard-share-btn self-start">
          <button
            type="button"
            onClick={() => setShareOpen((open) => !open)}
            className="dropdown-toggle inline-flex h-11 items-center gap-2 rounded-lg border border-gray-300 px-4 text-sm font-medium text-gray-700 shadow-theme-xs transition-colors hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
          >
            <MoreDotIcon className="size-4" />
            Share
          </button>
          <Dropdown
            isOpen={shareOpen}
            onClose={() => setShareOpen(false)}
            className="w-44 p-2"
          >
            <DropdownItem
              onItemClick={handleScreenshot}
              className="flex w-full rounded-lg px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-white/5"
            >
              Screenshot
            </DropdownItem>
          </Dropdown>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4 md:gap-6">
        <div className="col-span-12">
          <EcommerceMetrics
            participants={summary.participants}
            reservas={summary.reservas}
            profit={parseDecimal(summary.profit)}
            partidos={summary.partidos}
            loading={loading}
          />
        </div>

        <div className="col-span-12">
          <StatisticsChart data={statistics} loading={loading} />
        </div>

        <div className="col-span-12 md:col-span-6 xl:col-span-4">
          <TopProviders data={topProviders} loading={loading} />
        </div>
        <div className="col-span-12 md:col-span-6 xl:col-span-4">
          <TopCities data={topCities} loading={loading} />
        </div>
        <div className="col-span-12 xl:col-span-4">
          <ProximosPartidos data={proximosPartidos} loading={loading} />
        </div>

        <div className="col-span-12 xl:col-span-7">
          <MonthlySalesChart data={monthlySales} loading={loading} />
        </div>
        <div className="col-span-12 xl:col-span-5">
          <DemographicCard data={demographics} loading={loading} />
        </div>

        <ProviderCards data={providers} loading={loading} />
      </div>
    </div>
  );
}
