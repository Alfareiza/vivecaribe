"use client";

import React, { useCallback, useEffect, useState } from "react";
import DatePicker from "@/components/form/date-picker";
import Select from "@/components/form/Select";
import Pagination from "@/components/tables/Pagination";
import Button from "@/components/ui/button/Button";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import InlineLoading from "@/components/ui/loading/InlineLoading";
import { useModal } from "@/hooks/useModal";
import { fetchReservas } from "@/lib/reservas";
import { BOOKING_PROVIDER_OPTIONS } from "@/types/reservation";
import type { ReservationListItem } from "@/types/reservation";
import ProviderLogo from "./ProviderLogo";
import ReservationDetailModal from "./ReservationDetailModal";
import { EsHoyStatusDot } from "./StatusDot";
import { formatRawDateTime, formatPrice, PROVIDER_LABELS } from "./reservationUtils";

const PAGE_SIZE = 20;

const ALL = "all";

const estadoOptions = [
  { value: ALL, label: "Todos los estados" },
  { value: "en_progreso", label: "en_progreso" },
  { value: "confirmada", label: "confirmada" },
  { value: "cancelada", label: "cancelada" },
  { value: "error", label: "error" },
];

const providerOptions = [
  { value: ALL, label: "Todos los proveedores" },
  ...BOOKING_PROVIDER_OPTIONS.map((value) => ({
    value,
    label: PROVIDER_LABELS[value] ?? value,
  })),
];

export default function ReservationsTable() {
  const { isOpen, openModal, closeModal } = useModal();
  const [selected, setSelected] = useState<ReservationListItem | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [items, setItems] = useState<ReservationListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [estadoFilter, setEstadoFilter] = useState(ALL);
  const [providerFilter, setProviderFilter] = useState(ALL);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const page = Math.min(currentPage, totalPages);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchReservas({
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
        estado: estadoFilter !== ALL ? estadoFilter : undefined,
        booking_provider:
          providerFilter !== ALL ? providerFilter : undefined,
        fecha_evento_from: dateFrom ?? undefined,
        fecha_evento_to: dateTo ?? undefined,
      });
      setItems(response.items);
      setTotal(response.total);
    } catch {
      setItems([]);
      setTotal(0);
      setError("No se pudieron cargar las reservas");
    } finally {
      setLoading(false);
    }
  }, [page, estadoFilter, providerFilter, dateFrom, dateTo]);

  useEffect(() => {
    void loadPage();
  }, [loadPage]);

  const handleRowClick = (reservation: ReservationListItem) => {
    setSelected(reservation);
    openModal();
  };

  const handleCloseModal = () => {
    if (isCreateOpen) {
      setIsCreateOpen(false);
      return;
    }
    closeModal();
    setSelected(null);
  };

  const resetPage = () => setCurrentPage(1);

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white px-4 pb-3 pt-4 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-end justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
              Reservas
            </h3>
            <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
              {total} resultado{total === 1 ? "" : "s"}
            </p>
          </div>
          <Button size="sm" onClick={() => setIsCreateOpen(true)}>
            Nueva reserva
          </Button>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="w-full sm:w-44">
            <Select
              options={estadoOptions}
              placeholder="Estado"
              defaultValue={ALL}
              onChange={(value) => {
                setEstadoFilter(value || ALL);
                resetPage();
              }}
            />
          </div>
          <div className="w-full sm:w-48">
            <Select
              options={providerOptions}
              placeholder="Proveedor"
              defaultValue={ALL}
              onChange={(value) => {
                setProviderFilter(value || ALL);
                resetPage();
              }}
            />
          </div>
          <div className="w-full sm:w-56">
            <DatePicker
              id="reservas-fecha-evento-range"
              mode="range"
              label="Fecha evento"
              placeholder="Desde — Hasta"
              onChange={(selectedDates) => {
                const from = selectedDates[0]
                  ? toYmd(selectedDates[0])
                  : null;
                const to = selectedDates[1]
                  ? toYmd(selectedDates[1])
                  : selectedDates[0]
                    ? toYmd(selectedDates[0])
                    : null;
                setDateFrom(from);
                setDateTo(to);
                resetPage();
              }}
            />
          </div>
        </div>
      </div>

      {loading ? (
        <InlineLoading label="Cargando reservas…" />
      ) : error ? (
        <p className="py-8 text-center text-sm text-error-500">{error}</p>
      ) : (
        <>
          <div className="max-w-full overflow-x-auto">
            <div className="min-w-[1102px]">
              <Table>
                <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
                  <TableRow>
                    {[
                      "Experiencia",
                      "Cliente",
                      "Fecha evento",
                      "Pax",
                      "Precio",
                    ].map((header) => (
                      <TableCell
                        key={header}
                        isHeader
                        className="px-5 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400"
                      >
                        {header}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHeader>

                <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
                  {items.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        className="px-5 py-8 text-center text-theme-sm text-gray-500 dark:text-gray-400"
                      >
                        No hay reservas que coincidan con los filtros.
                      </TableCell>
                    </TableRow>
                  ) : (
                    items.map((reservation) => (
                      <TableRow
                        key={reservation.id}
                        className="cursor-pointer hover:bg-gray-50 dark:hover:bg-white/[0.02]"
                        onClick={() => handleRowClick(reservation)}
                      >
                        <TableCell className="px-4 py-3 text-start">
                          <div className="flex flex-col items-center gap-3 xl:flex-row xl:items-center">
                            <ProviderLogo
                              provider={reservation.booking_provider}
                              size={28}
                            />
                            <div className="order-3 flex min-w-0 items-center gap-2 xl:order-2">
                              <span className="block font-medium text-theme-sm text-gray-800 dark:text-white/90">
                                {reservation.nombre_experiencia}
                              </span>
                              <EsHoyStatusDot
                                esHoy={reservation.es_hoy}
                                tooltipSide="right"
                              />
                            </div>
                          </div>
                          <span className="mt-1 block text-theme-xs text-gray-500 dark:text-gray-400 xl:pl-10">
                            {reservation.ciudad_experiencia}
                          </span>
                        </TableCell>
                        <TableCell className="px-4 py-3 text-start">
                          <span className="block font-medium text-theme-sm text-gray-800 dark:text-white/90">
                            {reservation.customer_name}
                          </span>
                          <span className="block text-theme-xs text-gray-500 dark:text-gray-400">
                            {[reservation.phone, reservation.pais_del_visitante]
                              .filter(Boolean)
                              .join(" · ") || "—"}
                          </span>
                        </TableCell>
                        <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                          {formatRawDateTime(reservation.fecha_evento)}
                        </TableCell>
                        <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                          {reservation.participants}
                        </TableCell>
                        <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                          {formatPrice(reservation.income, reservation.moneda)}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={setCurrentPage}
            />
          </div>
        </>
      )}

      <ReservationDetailModal
        reservation={isCreateOpen ? null : selected}
        isOpen={isOpen || isCreateOpen}
        createMode={isCreateOpen}
        onClose={handleCloseModal}
        onSaved={() => void loadPage()}
        onDeleted={() => void loadPage()}
      />
    </div>
  );
}

function toYmd(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
