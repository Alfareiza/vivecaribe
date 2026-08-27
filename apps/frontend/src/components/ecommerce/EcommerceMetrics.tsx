"use client";

import React from "react";
import Image from "next/image";
import { DollarLineIcon, GroupIcon, ShootingStarIcon } from "@/icons";
import { formatMoney } from "@/lib/formatMoney";

type EcommerceMetricsProps = {
  participants: number;
  reservas: number;
  profit: number;
  partidos: number;
  loading?: boolean;
};

export function EcommerceMetrics({
  participants,
  reservas,
  profit,
  partidos,
  loading = false,
}: EcommerceMetricsProps) {
  const cards = [
    {
      label: "Customers",
      value: loading ? "—" : participants.toLocaleString("es-CO"),
      icon: <GroupIcon className="size-6 text-gray-800 dark:text-white/90" />,
    },
    {
      label: "Reservas",
      value: loading ? "—" : reservas.toLocaleString("es-CO"),
      icon: (
        <Image
          src="/images/icons/ticket.svg"
          width={24}
          height={24}
          alt=""
          className="text-gray-800 dark:text-white/90"
        />
      ),
    },
    {
      label: "Profit",
      value: loading ? "—" : formatMoney(profit),
      icon: <DollarLineIcon className="size-6 text-gray-800 dark:text-white/90" />,
    },
    {
      label: "Reservas vs Partidos",
      value: loading ? "—" : `${reservas}/${partidos}`,
      icon: <ShootingStarIcon className="size-6 text-gray-800 dark:text-white/90" />,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 md:gap-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800">
            {card.icon}
          </div>
          <div className="mt-5">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {card.label}
            </span>
            <h4 className="mt-2 font-bold text-gray-800 text-title-sm dark:text-white/90">
              {card.value}
            </h4>
          </div>
          {/* Badges commented out per dashboard spec
          <Badge color="success">
            <ArrowUpIcon />
            11.01%
          </Badge>
          */}
        </div>
      ))}
    </div>
  );
}
