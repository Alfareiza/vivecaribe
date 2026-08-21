/** Gasto (partido-level expense) shapes aligned with API OpenAPI schemas. */

/** Mirrors the backend's ``GastoCategoria`` enum — add new categories on both sides. */
export type GastoCategoria =
  | "Comida y/o Snacks"
  | "Transporte"
  | "Boletas"
  | "Apoyos"
  | "Otros";

export const GASTO_CATEGORIA_OPTIONS: GastoCategoria[] = [
  "Comida y/o Snacks",
  "Transporte",
  "Boletas",
  "Apoyos",
  "Otros",
];

/** One registered category amount, as embedded in ``PartidoResponse.gastos``. */
export type GastoItem = {
  categoria: GastoCategoria | string;
  monto: string;
};

/** A reserva's computed share of one gasto category, as embedded in ``ReservaResponse.gastos``. */
export type GastoShareItem = {
  categoria: GastoCategoria | string;
  monto: string;
};

/** Icon + color identity per category, shared by the partido editor grid and the reserva read-only breakdown. */
export const GASTO_CATEGORIA_META: Record<
  GastoCategoria,
  { icon: string; chipClass: string; barClass: string }
> = {
  "Comida y/o Snacks": {
    icon: "🍽️",
    chipClass: "bg-brand-50 text-brand-500 dark:bg-brand-500/15 dark:text-brand-400",
    barClass: "bg-brand-500",
  },
  Transporte: {
    icon: "🚗",
    chipClass:
      "bg-blue-light-50 text-blue-light-500 dark:bg-blue-light-500/15 dark:text-blue-light-500",
    barClass: "bg-blue-light-500",
  },
  Boletas: {
    icon: "🎫",
    chipClass: "bg-success-50 text-success-600 dark:bg-success-500/15 dark:text-success-500",
    barClass: "bg-success-500",
  },
  Apoyos: {
    icon: "🤝",
    chipClass: "bg-warning-50 text-warning-600 dark:bg-warning-500/15 dark:text-orange-400",
    barClass: "bg-warning-500",
  },
  Otros: {
    icon: "📦",
    chipClass: "bg-gray-100 text-gray-600 dark:bg-white/5 dark:text-white/70",
    barClass: "bg-gray-400",
  },
};
