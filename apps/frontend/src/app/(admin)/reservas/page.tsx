import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ReservationsLoader from "@/components/reservations/ReservationsLoader";
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
      <ReservationsLoader />
    </div>
  );
}
