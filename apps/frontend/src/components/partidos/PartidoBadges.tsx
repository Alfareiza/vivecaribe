"use client";

import Image from "next/image";
import React from "react";

type ReservaTier = "none" | "bronze" | "silver" | "gold";

function getReservaTier(count: number): ReservaTier {
  if (count >= 5) return "gold";
  if (count >= 3) return "silver";
  if (count >= 1) return "bronze";
  return "none";
}

function getParticipantsTier(count: number): ReservaTier {
  if (count >= 7) return "gold";
  if (count >= 4) return "silver";
  if (count >= 1) return "bronze";
  return "none";
}

const TIER_CLASSES: Record<ReservaTier, string> = {
  none: "bg-gray-100 text-gray-500 border border-transparent dark:bg-gray-800 dark:text-gray-500",
  bronze:
    "bg-gradient-to-br from-orange-100 via-amber-300 to-orange-400 text-amber-800 shadow-[0_1px_2px_rgba(180,83,9,0.25)] dark:from-amber-950 dark:via-orange-900 dark:to-amber-900 dark:text-amber-300 dark:border-amber-700/50",
  silver:
    "bg-gradient-to-br from-slate-100 via-gray-200 to-slate-300 text-slate-700 shadow-[0_1px_2px_rgba(100,116,139,0.25)] dark:from-slate-700 dark:via-gray-600 dark:to-slate-600 dark:text-slate-100 dark:border-slate-400/40",
  gold: "bg-gradient-to-br from-yellow-50 via-amber-200 to-yellow-300 text-amber-900 shadow-[0_1px_3px_rgba(217,119,6,0.35)] dark:from-yellow-900 dark:via-amber-800 dark:to-yellow-800 dark:text-yellow-200 dark:border-yellow-600/50",
};

export function ReservaBadge({ count }: { count: number }) {
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

export function ParticipantsBadge({ count }: { count: number }) {
  const tier = getParticipantsTier(count);

  return (
    <div
      className={`relative inline-flex items-center gap-1.5 overflow-hidden rounded-lg px-2 py-1.5 text-xs font-medium transition-colors ${TIER_CLASSES[tier]}`}
    >
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
      ) : (
        <span>-</span>
      )}
      {tier !== "none" ? <span className="reserva-badge-shine" /> : null}
    </div>
  );
}
