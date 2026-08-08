import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ReservationsTable from "@/components/reservations/ReservationsTable";
import { mockReservations } from "@/data/mockReservations";
import type { Metadata } from "next";
import React from "react";

export const metadata: Metadata = {
  title: "Reservas | ViveCaribe",
  description: "Listado de reservas de experiencias ViveCaribe",
};

export default function ReservasPage() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Reservas" />
      <ReservationsTable reservations={mockReservations} />
    </div>
  );
}
