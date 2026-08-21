"use client";

import React from "react";
import Image from "next/image";
import { formatRawDateTime, getDateState } from "@/components/reservations/reservationUtils";
import type { PartidoListItem } from "@/types/partido";

type PartidoCardProps = {
  partido: PartidoListItem;
  onClick: () => void;
};

export default function PartidoCard({ partido, onClick }: PartidoCardProps) {
  const dateState = getDateState(partido.fecha);
  const reservaCount = partido.reservas_count;
  const participantsCount = partido.participants_count;
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

        @keyframes reservaBadgeShine {
          0% { transform: translateX(-150%) skewX(-20deg); opacity: 0; }
          15% { opacity: 0.7; }
          50% { opacity: 1; }
          85% { opacity: 0.35; }
          100% { transform: translateX(250%) skewX(-20deg); opacity: 0; }
        }

        .reserva-badge-shine {
          position: absolute;
          inset: 0;
          width: 45%;
          background: linear-gradient(120deg, transparent, rgba(255, 255, 255, 0.85), transparent);
          opacity: 0;
          pointer-events: none;
        }

        .group:hover .reserva-badge-shine {
          animation: reservaBadgeShine 1.1s ease-in-out;
        }
      `}</style>

      <button
        type="button"
        onClick={onClick}
        className={`group ${baseCard} ${currentStateClass}`}
      >
        {/* Main content */}
        <div className="w-full">
          {/* Reserva + participants badges: above team names */}
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <ReservaBadge count={reservaCount} />
            <ParticipantsBadge count={participantsCount} />
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

type ReservaTier = "none" | "bronze" | "silver" | "gold";

function getReservaTier(count: number): ReservaTier {
  if (count >= 5) return "gold";
  if (count >= 3) return "silver";
  if (count >= 1) return "bronze";
  return "none";
}

/** Metallic gradient + text/border treatment per tier (light / dark). */
const TIER_CLASSES: Record<ReservaTier, string> = {
  none: "bg-gray-100 text-gray-500 border border-transparent dark:bg-gray-800 dark:text-gray-500",
  bronze:
    "bg-gradient-to-br from-orange-100 via-amber-300 to-orange-400 text-amber-800 shadow-[0_1px_2px_rgba(180,83,9,0.25)] dark:from-amber-950 dark:via-orange-900 dark:to-amber-900 dark:text-amber-300 dark:border-amber-700/50",
  silver:
    "bg-gradient-to-br from-slate-100 via-gray-200 to-slate-300 text-slate-700 shadow-[0_1px_2px_rgba(100,116,139,0.25)] dark:from-slate-700 dark:via-gray-600 dark:to-slate-600 dark:text-slate-100 dark:border-slate-400/40",
  gold: "bg-gradient-to-br from-yellow-50 via-amber-200 to-yellow-300 text-amber-900 shadow-[0_1px_3px_rgba(217,119,6,0.35)] dark:from-yellow-900 dark:via-amber-800 dark:to-yellow-800 dark:text-yellow-200 dark:border-yellow-600/50",
};

/**
 * Reserva badge: displays booking icon + count at top-left of card.
 * Tiered like a medal — muted gray at 0, bronze at 1-2, silver at 3-4,
 * gold at 5+. Non-muted tiers get a diagonal shine sweep on card hover.
 */
function ReservaBadge({ count }: { count: number }) {
  const tier = getReservaTier(count);

  return (
    <div
      className={`relative inline-flex items-center gap-1.5 overflow-hidden rounded-lg px-2 py-1.5 text-xs font-medium transition-colors ${TIER_CLASSES[tier]}`}
    >
      <Image
        src="/images/icons/ticket.svg"
        width={14}
        height={14}
        alt=""
        className="shrink-0"
      />
      <span>
        {count} Reserva{count !== 1 ? "s" : ""}
      </span>
      {tier !== "none" ? <span className="reserva-badge-shine" /> : null}
    </div>
  );
}

/**
 * Participants badge: flat count badge (icon + total headcount across this
 * partido's reservas). Deliberately untiered — unlike reserva counts,
 * headcounts are unbounded sums across bookings, so a medal-tier scale
 * doesn't map cleanly onto them.
 */
function ParticipantsBadge({ count }: { count: number }) {
  return (
    <div className="inline-flex items-center gap-1.5 rounded-lg border border-transparent bg-gray-100 px-2 py-1.5 text-xs font-medium text-gray-500 dark:bg-gray-800 dark:text-gray-400">
      <Image
        src="/images/icons/users.svg"
        width={14}
        height={14}
        alt=""
        className="shrink-0"
      />
      {count > 0 ? (
        <span>
          {count} Persona{count !== 1 ? "s" : ""}
        </span>
      ) : !count ? (
        <span>-</span>
      ) : null}
 
 
    </div>
  );
}
