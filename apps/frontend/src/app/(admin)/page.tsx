import type { Metadata } from "next";
import DashboardPage from "@/components/dashboard/DashboardPage";

export const metadata: Metadata = {
  title: "Grupo vive caribe | Football tours and travel",
  description:
    "Bienvenido a vive caribe, football tours and travel around Colombia",
};

export default function HomePage() {
  return <DashboardPage />;
}
