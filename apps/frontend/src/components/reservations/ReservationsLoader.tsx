"use client";

import ReservationsTable from "@/components/reservations/ReservationsTable";
import { fetchAllReservas } from "@/lib/reservas";
import type { Reservation } from "@/types/reservation";
import React, { useEffect, useState } from "react";

export default function ReservationsLoader() {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const items = await fetchAllReservas();
        if (!cancelled) {
          setReservations(items);
          setError(null);
        }
      } catch {
        if (!cancelled) {
          setError("No se pudieron cargar las reservas");
          setReservations([]);
        }
      } finally {
        if (!cancelled) setLoaded(true);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!loaded) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Cargando reservas…
      </p>
    );
  }

  if (error) {
    return <p className="text-sm text-error-500">{error}</p>;
  }

  return <ReservationsTable reservations={reservations} />;
}
