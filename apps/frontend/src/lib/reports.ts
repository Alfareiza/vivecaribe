import { apiJson } from "@/lib/api";
import type { BookingProvider } from "@/types/reservation";
import type { PartidoListItem } from "@/types/partido";

export type ReportFilters = {
  fecha_from?: string;
  fecha_to?: string;
  booking_provider?: string;
};

export type ReportSummary = {
  participants: number;
  reservas: number;
  profit: string;
  partidos: number;
};

export type MonthlyStatisticsPoint = {
  month: string;
  income_final: string;
  costos: string;
};

export type MonthlySalesPoint = {
  month: string;
  profit: string;
};

export type TopProviderItem = {
  provider: BookingProvider | string;
  profit: string;
  reservas: number;
  participants: number;
};

export type TopCityItem = {
  city: string;
  profit: string;
  reservas: number;
};

export type TemporadaPoint = {
  month: string;
  city: string;
  participants: number;
};

export type DemographicItem = {
  country: string;
  reservas: number;
  participants: number;
};

export type ProviderCardItem = {
  provider: BookingProvider | string;
  profit: string;
  reservas: number;
  participants: number;
};

function buildReportQuery(filters: ReportFilters = {}): string {
  const query = new URLSearchParams();
  if (filters.fecha_from) query.set("fecha_from", filters.fecha_from);
  if (filters.fecha_to) query.set("fecha_to", filters.fecha_to);
  if (filters.booking_provider) {
    query.set("booking_provider", filters.booking_provider);
  }
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

export async function fetchReportSummary(
  filters: ReportFilters = {},
): Promise<ReportSummary> {
  return apiJson<ReportSummary>(`/reports/summary${buildReportQuery(filters)}`);
}

export async function fetchReportStatistics(
  filters: ReportFilters = {},
): Promise<MonthlyStatisticsPoint[]> {
  return apiJson<MonthlyStatisticsPoint[]>(
    `/reports/statistics${buildReportQuery(filters)}`,
  );
}

export async function fetchReportMonthlySales(
  filters: ReportFilters = {},
): Promise<MonthlySalesPoint[]> {
  return apiJson<MonthlySalesPoint[]>(
    `/reports/monthly-sales${buildReportQuery(filters)}`,
  );
}

export async function fetchReportTopProviders(
  filters: ReportFilters = {},
): Promise<TopProviderItem[]> {
  return apiJson<TopProviderItem[]>(
    `/reports/top-providers${buildReportQuery(filters)}`,
  );
}

export async function fetchReportTopCities(
  filters: ReportFilters = {},
): Promise<TopCityItem[]> {
  return apiJson<TopCityItem[]>(
    `/reports/top-cities${buildReportQuery(filters)}`,
  );
}

export async function fetchReportTemporada(
  filters: ReportFilters = {},
): Promise<TemporadaPoint[]> {
  return apiJson<TemporadaPoint[]>(
    `/reports/temporada${buildReportQuery(filters)}`,
  );
}

export async function fetchReportDemographics(
  filters: ReportFilters = {},
): Promise<DemographicItem[]> {
  return apiJson<DemographicItem[]>(
    `/reports/demographics${buildReportQuery(filters)}`,
  );
}

export async function fetchReportProviders(
  filters: ReportFilters = {},
): Promise<ProviderCardItem[]> {
  return apiJson<ProviderCardItem[]>(
    `/reports/providers${buildReportQuery(filters)}`,
  );
}

export async function fetchReportProximosPartidos(): Promise<PartidoListItem[]> {
  return apiJson<PartidoListItem[]>("/reports/proximos-partidos");
}
