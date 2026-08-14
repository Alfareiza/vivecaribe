"use client";

import React, { useEffect, useState } from "react";
import ReservationsTable from "@/components/reservations/ReservationsTable";
import InlineLoading from "@/components/ui/loading/InlineLoading";
import { ApiError } from "@/lib/api";
import { fetchReservas } from "@/lib/reservas";
import type { ReservationListItem } from "@/types/reservation";

const FETCH_LIMIT = 100;

export default function ReservationsLoader() {
  const [reservations, setReservations] = useState<
    ReservationListItem[] | null
  >(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const all: ReservationListItem[] = [];
        let skip = 0;
        let total = Infinity;
        while (skip < total) {
          const response = await fetchReservas({ skip, limit: FETCH_LIMIT });
          all.push(...response.items);
          total = response.total;
          skip += FETCH_LIMIT;
        }
        if (!cancelled) {
          setReservations(all);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "No se pudieron cargar las reservas",
          );
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <p className="py-8 text-center text-sm text-error-500">{error}</p>;
  }

  if (!reservations) {
    return <InlineLoading label="Cargando reservas…" />;
  }

  return <ReservationsTable reservations={reservations} />;
}
