import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import PartidosLoader from "@/components/partidos/PartidosLoader";
import type { Metadata } from "next";
import React from "react";

export const metadata: Metadata = {
  title: "Partidos | ViveCaribe",
  description: "Listado de partidos de fútbol asociados a reservas",
};

export default function PartidosPage() {
  return (
    <div>
      <PageBreadcrumb pageTitle="Partidos" />
      <PartidosLoader />
    </div>
  );
}
