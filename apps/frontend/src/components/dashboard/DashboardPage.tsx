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
import TemporadaChart from "@/components/dashboard/TemporadaChart";
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
  fetchReportTemporada,
  fetchReportTopCities,
  fetchReportTopProviders,
  type DemographicItem,
  type MonthlySalesPoint,
  type MonthlyStatisticsPoint,
  type ProviderCardItem,
  type ReportFilters,
  type ReportSummary,
  type TemporadaPoint,
  type TopCityItem,
  type TopProviderItem,
} from "@/lib/reports";
import {
  rangeForPreset,
  statsFilterPhrase,
  type DateRange,
  type StatsPreset,
} from "@/lib/statsPeriod";
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
  const [statsLoading, setStatsLoading] = useState(true);
  const [summary, setSummary] = useState<ReportSummary>(EMPTY_SUMMARY);
  const [statistics, setStatistics] = useState<MonthlyStatisticsPoint[]>([]);
  const [monthlySales, setMonthlySales] = useState<MonthlySalesPoint[]>([]);
  const [topProviders, setTopProviders] = useState<TopProviderItem[]>([]);
  const [topCities, setTopCities] = useState<TopCityItem[]>([]);
  const [temporada, setTemporada] = useState<TemporadaPoint[]>([]);
  const [demographics, setDemographics] = useState<DemographicItem[]>([]);
  const [providers, setProviders] = useState<ProviderCardItem[]>([]);
  const [proximosPartidos, setProximosPartidos] = useState<PartidoListItem[]>(
    [],
  );
  const [statsPreset, setStatsPreset] = useState<StatsPreset>("this_year");
  const [statsRange, setStatsRange] = useState<DateRange>(() =>
    rangeForPreset("this_year"),
  );
  const [statsDatePickerKey, setStatsDatePickerKey] = useState(0);

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
        monthlySalesData,
        topProvidersData,
        topCitiesData,
        temporadaData,
        demographicsData,
        providersData,
        proximosData,
      ] = await Promise.all([
        fetchReportSummary(apiFilters),
        fetchReportMonthlySales(apiFilters),
        fetchReportTopProviders(apiFilters),
        fetchReportTopCities(apiFilters),
        fetchReportTemporada(apiFilters),
        fetchReportDemographics(apiFilters),
        fetchReportProviders(apiFilters),
        fetchReportProximosPartidos(),
      ]);
      setSummary(summaryData);
      setMonthlySales(monthlySalesData);
      setTopProviders(topProvidersData);
      setTopCities(topCitiesData);
      setTemporada(temporadaData);
      setDemographics(demographicsData);
      setProviders(providersData);
      setProximosPartidos(proximosData);
    } catch {
      setSummary(EMPTY_SUMMARY);
      setMonthlySales([]);
      setTopProviders([]);
      setTopCities([]);
      setTemporada([]);
      setDemographics([]);
      setProviders([]);
      setProximosPartidos([]);
    } finally {
      setLoading(false);
    }
  }, [apiFilters]);

  const loadStatistics = useCallback(async () => {
    setStatsLoading(true);
    try {
      const statisticsData = await fetchReportStatistics({
        fecha_from: statsRange.from,
        fecha_to: statsRange.to,
      });
      setStatistics(statisticsData);
    } catch {
      setStatistics([]);
    } finally {
      setStatsLoading(false);
    }
  }, [statsRange]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    void loadStatistics();
  }, [loadStatistics]);

  function handleStatsPreset(preset: Exclude<StatsPreset, "custom">) {
    setStatsPreset(preset);
    setStatsRange(rangeForPreset(preset));
    setStatsDatePickerKey((key) => key + 1);
  }

  const handleStatsCustomRange = useCallback((range: DateRange) => {
    setStatsPreset("custom");
    setStatsRange(range);
  }, []);

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
          <StatisticsChart
            data={statistics}
            loading={statsLoading}
            phrase={statsFilterPhrase(statsPreset, statsRange)}
            preset={statsPreset}
            dateRange={statsRange}
            datePickerKey={statsDatePickerKey}
            onPreset={handleStatsPreset}
            onCustomRange={handleStatsCustomRange}
          />
        </div>

        <div className="col-span-12 grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 xl:grid-cols-[3fr_2fr_5fr]">
          <div className="min-w-0">
            <TopProviders data={topProviders} loading={loading} />
          </div>
          <div className="min-w-0">
            <TopCities data={topCities} loading={loading} />
          </div>
          <div className="min-w-0 md:col-span-2 xl:col-span-1">
            <TemporadaChart data={temporada} loading={loading} />
          </div>
        </div>

        <div className="col-span-12">
          <ProximosPartidos data={proximosPartidos} loading={loading} />
        </div>

        <div className="col-span-12 grid grid-cols-1 gap-4 md:gap-6 xl:grid-cols-[minmax(0,7fr)_minmax(0,3fr)]">
          <div className="flex min-w-0 flex-col gap-4 md:gap-6">
            <MonthlySalesChart data={monthlySales} loading={loading} />
            <ProviderCards data={providers} loading={loading} />
          </div>
          <div className="min-w-0 xl:h-full">
            <DemographicCard data={demographics} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  );
}
