"use client";

import React from "react";
import type { BadgeColor } from "@/components/ui/badge/Badge";

type StatusDotProps = {
  label: string;
  color?: BadgeColor;
  /** When true, shows the warning-style ping animation. */
  animate?: boolean;
  className?: string;
  /** Prefer `right` inside overflow-clipped table cells. */
  tooltipSide?: "top" | "right";
};

const DOT_COLOR: Record<string, string> = {
  success: "bg-success-500",
  warning: "bg-warning-500",
  error: "bg-error-500",
  primary: "bg-brand-500",
  info: "bg-blue-light-500",
  light: "bg-gray-400",
  dark: "bg-gray-600",
};

const PING_COLOR: Record<string, string> = {
  success: "bg-success-400",
  warning: "bg-orange-400",
  error: "bg-error-400",
  primary: "bg-brand-400",
  info: "bg-blue-light-400",
  light: "bg-gray-300",
  dark: "bg-gray-500",
};

/**
 * Compact status indicator: colored dot + hover tooltip.
 * Keep generic so future badge kinds (estado, etc.) can reuse it.
 */
export default function StatusDot({
  label,
  color = "light",
  animate = false,
  className = "",
  tooltipSide = "top",
}: StatusDotProps) {
  const dotClass = DOT_COLOR[color] ?? DOT_COLOR.light;
  const pingClass = PING_COLOR[color] ?? PING_COLOR.light;

  const tooltipPosition =
    tooltipSide === "right"
      ? "left-full top-1/2 ml-2 -translate-y-1/2"
      : "bottom-full left-1/2 mb-2 -translate-x-1/2";

  return (
    <span
      className={`group relative inline-flex shrink-0 items-center justify-center ${className}`.trim()}
      tabIndex={0}
      aria-label={label}
    >
      <span
        className={`relative inline-flex h-2.5 w-2.5 rounded-full ${dotClass}`}
      >
        {animate ? (
          <span
            className={`absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping ${pingClass}`}
          />
        ) : null}
      </span>
      <span
        role="tooltip"
        className={`pointer-events-none absolute z-50 whitespace-nowrap rounded-md bg-gray-900 px-2 py-1 text-theme-xs font-medium text-white opacity-0 shadow-theme-sm transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 dark:bg-gray-700 ${tooltipPosition}`}
      >
        {label}
      </span>
    </span>
  );
}

/** Orange pinging badge when the event is today (America/Bogota). */
export function EsHoyStatusDot({
  esHoy,
  className = "",
  tooltipSide = "top",
}: {
  esHoy: boolean;
  className?: string;
  tooltipSide?: "top" | "right";
}) {
  if (!esHoy) return null;
  return (
    <StatusDot
      label="Hoy"
      color="warning"
      animate
      className={className}
      tooltipSide={tooltipSide}
    />
  );
}
