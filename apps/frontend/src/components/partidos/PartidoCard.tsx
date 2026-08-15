"use client";

import React from "react";
import { formatRawDateTime, getDateState } from "@/components/reservations/reservationUtils";
import type { PartidoListItem } from "@/types/partido";

type PartidoCardProps = {
  partido: PartidoListItem;
  onClick: () => void;
};

export default function PartidoCard({ partido, onClick }: PartidoCardProps) {
  const dateState = getDateState(partido.fecha);
  const reservaCount = partido.reservas_count;
  const isPast = dateState === "past";
  const isToday = dateState === "today";

  // Base card styling
  const baseCard =
    "relative flex w-full flex-col items-start rounded-2xl border p-5 text-left shadow-theme-xs transition-all duration-200";

  // State-specific border and background styling
  const stateClasses = {
    past: "border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-950/40 hover:border-gray-300 hover:shadow-theme-sm dark:hover:border-gray-700",
    today:
      "border-orange-400 bg-white dark:bg-white/[0.03] dark:border-orange-600 shadow-[0_0_12px_rgba(251,146,60,0.2)] hover:border-orange-500 hover:shadow-[0_0_16px_rgba(251,146,60,0.3)] dark:shadow-[0_0_12px_rgba(251,146,60,0.15)] animate-partido-glow-pulse",
    future:
      "border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03] hover:border-brand-300 hover:shadow-theme-sm dark:hover:border-brand-800",
  };

  const currentStateClass = stateClasses[dateState];

  return (
    <>
      <style>{`
        @keyframes partidoGlowPulse {
          0%, 100% {
            box-shadow: 0 0 12px rgba(251, 146, 60, 0.2);
            border-color: rgb(251, 146, 60);
          }
          50% {
            box-shadow: 0 0 20px rgba(251, 146, 60, 0.4);
            border-color: rgb(249, 115, 22);
          }
        }

        .animate-partido-glow-pulse {
          animation: partidoGlowPulse 3.5s ease-in-out infinite;
        }
      `}</style>

      <button
        type="button"
        onClick={onClick}
        className={`${baseCard} ${currentStateClass}`}
      >
        {/* Main content */}
        <div className="w-full">
          {/* Reserva badge: above team names */}
          <div className="mb-3">
            <ReservaBadge count={reservaCount} />
          </div>

          {/* Team matchup */}
          <div className="flex w-full items-center justify-between gap-3">
            <span
              className={`min-w-0 truncate text-base font-semibold ${
                isPast
                  ? "text-gray-600 dark:text-gray-400"
                  : "text-gray-800 dark:text-white/90"
              }`}
            >
              {partido.equipo_local}
            </span>
            <span className="shrink-0 text-theme-xs font-medium text-gray-400 dark:text-gray-500">
              vs
            </span>
            <span
              className={`min-w-0 truncate text-right text-base font-semibold ${
                isPast
                  ? "text-gray-600 dark:text-gray-400"
                  : "text-gray-800 dark:text-white/90"
              }`}
            >
              {partido.equipo_visitante}
            </span>
          </div>

          {/* Date and city */}
          <div
            className={`mt-3 flex w-full items-center justify-between gap-2 text-theme-xs ${
              isPast
                ? "text-gray-500 dark:text-gray-500"
                : "text-gray-500 dark:text-gray-400"
            }`}
          >
            <span className="truncate">{formatRawDateTime(partido.fecha)}</span>
            <span className="truncate">{partido.ciudad}</span>
          </div>
        </div>
      </button>
    </>
  );
}

/**
 * Reserva badge: displays booking icon + count at top-left of card.
 * Muted gray when count is 0, orange-tinted when count > 0.
 */
function ReservaBadge({ count }: { count: number }) {
  const isMuted = count === 0;

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors ${
        isMuted
          ? "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500"
          : "bg-orange-50 text-orange-700 dark:bg-orange-950/50 dark:text-orange-400"
      }`}
    >
      {/* SVG icon: Ticket/Booking */}
      <svg
        width="14"
        height="14"
        viewBox="0 0 16 16"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
      >
        <path
          d="M2 3h12a1 1 0 011 1v8a1 1 0 01-1 1H2a1 1 0 01-1-1V4a1 1 0 011-1z"
          stroke="currentColor"
          strokeWidth="1.2"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M5 8h6"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
      </svg>
      <span>{count} Reserva{count !== 1 ? "s" : ""}</span>
    </div>
  );
}
