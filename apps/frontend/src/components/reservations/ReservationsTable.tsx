"use client";

import React, { useMemo, useState } from "react";
import Image from 'next/image';
import DatePicker from "@/components/form/date-picker";
import Select from "@/components/form/Select";
import Pagination from "@/components/tables/Pagination";
import Badge from "@/components/ui/badge/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useModal } from "@/hooks/useModal";
import type { ReservationListItem } from "@/types/reservation";
import ReservationDetailModal from "./ReservationDetailModal";
import {
  formatDisplayDateTime,
  formatPrice,
  getEstadoBadgeColor,
  reservationInDateRange,
} from "./reservationUtils";

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
  { value: "getyourguide", label: "getyourguide" },
  { value: "viator", label: "viator" },
  { value: "homefans", label: "homefans" },
  { value: "propio", label: "propio" },
];

type ReservationsTableProps = {
  reservations: ReservationListItem[];
};

export default function ReservationsTable({
  reservations,
}: ReservationsTableProps) {
  const { isOpen, openModal, closeModal } = useModal();
  const [selected, setSelected] = useState<ReservationListItem | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [estadoFilter, setEstadoFilter] = useState(ALL);
  const [providerFilter, setProviderFilter] = useState(ALL);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return reservations
      .filter((r) => {
        if (estadoFilter !== ALL && r.estado !== estadoFilter) return false;
        if (providerFilter !== ALL && r.booking_provider !== providerFilter) {
          return false;
        }
        return reservationInDateRange(r, { from: dateFrom, to: dateTo });
      })
      .sort((a, b) => {
        // Descending by event date; nulls last
        if (!a.fecha_evento && !b.fecha_evento) return 0;
        if (!a.fecha_evento) return 1;
        if (!b.fecha_evento) return -1;
        return (
          new Date(b.fecha_evento).getTime() -
          new Date(a.fecha_evento).getTime()
        );
      });
  }, [reservations, estadoFilter, providerFilter, dateFrom, dateTo]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const page = Math.min(currentPage, totalPages);
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleRowClick = (reservation: ReservationListItem) => {
    setSelected(reservation);
    openModal();
  };

  const handleCloseModal = () => {
    closeModal();
    setSelected(null);
  };

  const resetPage = () => setCurrentPage(1);

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white px-4 pb-3 pt-4 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            Reservas
          </h3>
          <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
            {filtered.length} resultado{filtered.length === 1 ? "" : "s"}
          </p>
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

      <div className="max-w-full overflow-x-auto">
        <div className="min-w-[1102px]">
          <Table>
            <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
              <TableRow>
                {[
                  // "Ref",
                  "Fuente",
                  "Estado",
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
              {pageItems.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={8}
                    className="px-5 py-8 text-center text-theme-sm text-gray-500 dark:text-gray-400"
                  >
                    No hay reservas que coincidan con los filtros.
                  </TableCell>
                </TableRow>
              ) : (
                pageItems.map((reservation) => (
                  <TableRow
                    key={reservation.id}
                    className="cursor-pointer hover:bg-gray-50 dark:hover:bg-white/[0.02]"
                    onClick={() => handleRowClick(reservation)}
                  >
                    {/* <TableCell className="px-5 py-4 text-start">
                      <span className="font-medium text-theme-sm text-gray-800 dark:text-white/90">
                        {reservation.reserva_reference}
                      </span>
                    </TableCell> */}
                    <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                      {reservation.booking_provider}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-start">
                      <Badge
                        size="sm"
                        color={getEstadoBadgeColor(reservation.estado)}
                      >
                        {reservation.estado}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-start">
                      <Image
                        width={44}
                        height={44}
                        src="/images/user/owner.jpg"
                        alt="User"
                      />
                      <span className="block font-medium text-theme-sm text-gray-800 dark:text-white/90">
                        {reservation.nombre_experiencia}
                      </span>
                      <span className="block text-theme-xs text-gray-500 dark:text-gray-400">
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
                      {formatDisplayDateTime(reservation.fecha_evento)}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                      {reservation.participants}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-start text-theme-sm text-gray-500 dark:text-gray-400">
                      {formatPrice(reservation.price, reservation.moneda)}
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

      <ReservationDetailModal
        reservation={selected}
        isOpen={isOpen}
        onClose={handleCloseModal}
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
