"use client";

import React, { useEffect, useState } from "react";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import Select from "@/components/form/Select";
import TextArea from "@/components/form/input/TextArea";
import { Modal } from "@/components/ui/modal";
import InfoHint from "@/components/ui/tooltip/InfoHint";
import { AngleDownIcon, CalendarIcon, WhatsappIcon } from "@/icons";
import { ApiError } from "@/lib/api";
import { COUNTRY_NAMES } from "@/lib/countries";
import { fetchPartidoById, fetchPartidos } from "@/lib/partidos";
import {
  createReserva,
  deleteReserva,
  fetchReservaById,
  updateReserva,
  type ReservaCreatePayload,
  type ReservaUpdatePayload,
} from "@/lib/reservas";
import { fetchTrmToCop } from "@/lib/trm";
import { BOOKING_PROVIDER_OPTIONS } from "@/types/reservation";
import type { Reservation, ReservationListItem } from "@/types/reservation";
import type { PartidoListItem } from "@/types/partido";
import { GASTO_CATEGORIA_META, GASTO_CATEGORIA_OPTIONS } from "@/types/gasto";
import PartidoSelector from "./PartidoSelector";
import ProviderLogo from "./ProviderLogo";
import ShareMenu from "./ShareMenu";
import { EsHoyStatusDot } from "./StatusDot";
import {
  buildGoogleCalendarUrl,
  buildWhatsAppShareUrl,
} from "./reservationShare";
import {
  MEETING_POINT_LABELS,
  PROVIDER_LABELS,
  TIPO_TOUR_LABELS,
  dayWindow,
  formatCOP,
  formatPlainNumberCO,
  formatDisplayDateTime,
  formatPaidAtDate,
  formatPrice,
  formatRawDateTime,
  partidoLabel,
  sanitizeDecimalInput,
  toDatetimeLocal,
  toIsoUtc,
  truncateText,
} from "./reservationUtils";

type ReservationDetailModalProps = {
  reservation: ReservationListItem | null;
  isOpen: boolean;
  onClose: () => void;
  /** Opens the modal as a blank create form instead of loading `reservation`. */
  createMode?: boolean;
  /** Called after a successful create or update so the parent list can refresh. */
  onSaved?: () => void;
  /** Called after a successful soft-delete so the parent list can refresh. */
  onDeleted?: () => void;
};

type FormState = {
  nombre_experiencia: string;
  ciudad_experiencia: string;
  fecha_evento: string;
  booking_provider: string;
  customer_name: string;
  participants: string;
  phone: string;
  pais_del_visitante: string;
  menores_de_edad: boolean;
  meeting_point: string;
  notificado_whatsapp: boolean;
  lugar_de_recogida: string;
  moneda: string;
  price: string;
  income: string;
  income_estimado: string;
  trm_estimado: string;
  trm_final: string;
  notas_personales: string;
  notas_cliente: string;
  tipo_tour: string;
};

/** Estado is not operator-editable in this modal; every manual create is born confirmed. */
const CREATE_ESTADO = "confirmada";

/** Named experience -> auto-filled ciudad + punto de encuentro (create mode only). */
const EXPERIENCIA_PRESETS: Record<
  string,
  { ciudad: string; meetingPoint: string }
> = {
  "Watch Junior de Barranquilla Match": {
    ciudad: "Barranquilla",
    meetingPoint: "Door-to-Door",
  },
  "Cartagena Match Day Experience": {
    ciudad: "Cartagena",
    meetingPoint: "old shoes monument",
  },
};

const CREATE_DEFAULTS: FormState = {
  nombre_experiencia: "Watch Junior de Barranquilla Match",
  ciudad_experiencia: "Barranquilla",
  fecha_evento: "",
  booking_provider: "propio",
  customer_name: "",
  participants: "1",
  phone: "",
  pais_del_visitante: "",
  menores_de_edad: false,
  meeting_point: "Door-to-Door",
  notificado_whatsapp: false,
  lugar_de_recogida: "",
  moneda: "USD",
  price: "",
  income: "",
  income_estimado: "",
  trm_estimado: "",
  trm_final: "",
  notas_personales: "",
  notas_cliente: "",
  tipo_tour: "football tour",
};

function seedFormFromDetail(detail: Reservation): FormState {
  return {
    nombre_experiencia: detail.nombre_experiencia,
    ciudad_experiencia: detail.ciudad_experiencia,
    fecha_evento: detail.fecha_evento ? toDatetimeLocal(detail.fecha_evento) : "",
    booking_provider: detail.booking_provider,
    customer_name: detail.customer_name,
    participants: String(detail.participants),
    phone: detail.phone,
    pais_del_visitante: detail.pais_del_visitante,
    menores_de_edad: detail.menores_de_edad,
    meeting_point: detail.meeting_point ?? "",
    notificado_whatsapp: detail.notificado_whatsapp,
    lugar_de_recogida: detail.lugar_de_recogida ?? "",
    moneda: detail.moneda,
    price: detail.price,
    income: detail.income,
    income_estimado: detail.income_estimado ?? "",
    trm_estimado: detail.trm_estimado ?? "",
    trm_final: detail.trm_final ?? "",
    notas_personales: detail.notas_personales ?? "",
    notas_cliente: detail.notas_cliente ?? "",
    tipo_tour: detail.tipo_tour ?? "",
  };
}

/**
 * e.g. booking_provider="vayara" + today 21 Nov 2026 -> "VA-211126-X7Q".
 * The random suffix keeps two same-day/same-provider manual reservas from
 * colliding on the ``(booking_provider, reserva_reference)`` idempotency
 * key; `handleSave` also retries with a fresh suffix on an actual 409.
 */
function buildReservaReference(bookingProvider: string): string {
  const prefix = (bookingProvider || "NA").slice(0, 2).toUpperCase();
  const now = new Date();
  const dd = String(now.getDate()).padStart(2, "0");
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const yy = String(now.getFullYear()).slice(-2);
  const suffix = Math.random().toString(36).slice(2, 5).toUpperCase();
  return `${prefix}-${dd}${mm}${yy}-${suffix}`;
}

const MAX_CREATE_ATTEMPTS = 5;

/** Repeatedly clicking "Buscar partido" for the same ciudad+día reuses this instead of re-hitting the API every time. */
const PARTIDO_LOOKUP_CACHE_MS = 60_000;
const partidoLookupCache = new Map<
  string,
  { items: PartidoListItem[]; expiresAt: number }
>();

async function lookupPartidosCached(
  ciudad: string,
  window: { from: string; to: string } | null,
): Promise<PartidoListItem[]> {
  const key = `${ciudad}|${window?.from}|${window?.to}`;
  const cached = partidoLookupCache.get(key);
  if (cached && cached.expiresAt > Date.now()) return cached.items;

  const response = await fetchPartidos({
    ciudad,
    fecha_from: window?.from,
    fecha_to: window?.to,
    limit: 20,
  });
  partidoLookupCache.set(key, {
    items: response.items,
    expiresAt: Date.now() + PARTIDO_LOOKUP_CACHE_MS,
  });
  return response.items;
}

/** Ingreso as a fraction of Precio, by provider payout terms. No rule was given for a provider defaults to 100% (same as Propio). */
const INCOME_RATE_BY_PROVIDER: Record<string, number> = {
  propio: 1,
  airbnb: 1,
  vayara: 1,
  otro: 1,
  getyourguide: 0.7,
  viator: 0.7634,
  homefans: 0.75,
};

/** Debounce for the Ingreso-estimado TRM fetch — Precio is typed keystroke by keystroke, which cascades into Ingreso and would otherwise fire one HTTP request per keystroke. */
const TRM_FETCH_DEBOUNCE_MS = 500;

/**
 * Backend requires a leading "+" (E.164-style) on any non-empty phone.
 * Adds it automatically if the operator typed only digits; leaves blank
 * phones untouched.
 */
function normalizePhone(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return trimmed;
  return trimmed.startsWith("+") ? trimmed : `+${trimmed}`;
}

const experienciaOptions = Object.keys(EXPERIENCIA_PRESETS).map((value) => ({
  value,
  label: value,
}));

const ciudadOptions = [
  { value: "Barranquilla", label: "Barranquilla" },
  { value: "Cartagena", label: "Cartagena" },
];

const monedaOptions = [
  { value: "USD", label: "USD" },
  { value: "COP", label: "COP" },
  { value: "EUR", label: "EUR" },
];

const bookingProviderOptions = BOOKING_PROVIDER_OPTIONS.map((value) => ({
  value,
  label: PROVIDER_LABELS[value] ?? value,
}));

const meetingPointOptions = [
  { value: "", label: "Sin definir" },
  ...Object.entries(MEETING_POINT_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

/** Edit mode: all options open (legacy pipeline reservas may be city tours). */
const tipoTourOptionsEdit = [
  { value: "", label: "Sin definir" },
  ...Object.entries(TIPO_TOUR_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

/** Create mode: locked to football tour — this modal only creates match-tour reservas. */
const tipoTourOptionsCreate = Object.entries(TIPO_TOUR_LABELS).map(
  ([value, label]) => ({ value, label, disabled: value !== "football tour" }),
);

/** Label + value as adjacent dl grid cells (tight, aligned within a section). */
function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-theme-xs font-medium text-gray-500 dark:text-gray-400">
        {label}
      </dt>
      <dd className="min-w-0 break-words text-sm font-medium text-gray-800 dark:text-white/90">
        {value}
      </dd>
    </>
  );
}

/** Wraps a value with a hover/focus tooltip, matching StatusDot's visual language. */
function InfoTooltip({
  label,
  underline = true,
  children,
}: {
  label: string;
  underline?: boolean;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`group relative inline-flex cursor-help items-center ${underline ? "border-b border-dashed border-gray-300 dark:border-gray-600" : ""}`}
      tabIndex={0}
    >
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-max max-w-[220px] -translate-x-1/2 whitespace-normal rounded-md bg-gray-900 px-2 py-1 text-center text-theme-xs font-medium text-white opacity-0 shadow-theme-sm transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 dark:bg-gray-700"
      >
        {label}
      </span>
    </span>
  );
}

/**
 * A single financial figure as a card — label on top, value sized by
 * `emphasis`, an optional caption below (e.g. the FX rate that produced
 * it). Used to build the Resumen's financial hierarchy: "hero" cards for
 * the headline outcome (Ingreso final, Profit, % Profit) read much larger
 * than "secondary" reference cards (Ingreso, Ingreso estimado, Costos).
 */
function StatCard({
  label,
  value,
  caption,
  emphasis = "secondary",
}: {
  label: string;
  value: React.ReactNode;
  caption?: React.ReactNode;
  emphasis?: "hero" | "secondary";
}) {
  return (
    <div
      className={`rounded-xl border border-gray-100 p-3 dark:border-gray-800 ${
        emphasis === "hero"
          ? "bg-white dark:bg-white/[0.03]"
          : "bg-gray-50/60 dark:bg-white/[0.02]"
      }`}
    >
      <p className="text-theme-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
        {label}
      </p>
      <p
        className={
          emphasis === "hero"
            ? "mt-1 text-title-sm font-bold text-gray-800 dark:text-white/90"
            : "mt-1 text-sm font-semibold text-gray-700 dark:text-gray-200"
        }
      >
        {value}
      </p>
      {caption ? (
        <p className="mt-1 text-theme-xs text-gray-400 dark:text-gray-500">{caption}</p>
      ) : null}
    </div>
  );
}

/** Controlled on/off toggle (Switch is uncontrolled internally, unsuited for optimistic rollback). */
function ControlledSwitch({
  checked,
  disabled,
  onChange,
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-150 ease-linear disabled:cursor-not-allowed disabled:opacity-60"
    >
      <span
        className={`absolute inset-0 rounded-full transition-colors duration-150 ease-linear ${checked ? "bg-brand-500" : "bg-gray-200 dark:bg-white/10"}`}
      />
      <span
        className={`relative h-5 w-5 translate-x-0.5 rounded-full bg-white shadow-theme-sm transition-transform duration-150 ease-linear ${checked ? "translate-x-[22px]" : ""}`}
      />
    </button>
  );
}

function CollapsibleMetadata({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <section className="rounded-xl border border-gray-100 bg-gray-50/60 dark:border-gray-800 dark:bg-white/[0.02]">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
      >
        <span className="text-theme-sm font-semibold text-gray-800 dark:text-white/90">
          Metadatos
        </span>
        <AngleDownIcon
          className={`size-5 shrink-0 text-gray-400 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      <div
        className={`grid transition-[grid-template-rows] duration-200 ease-out ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-1.5 border-t border-gray-100 px-3 py-2.5 dark:border-gray-800">
            {children}
          </dl>
        </div>
      </div>
    </section>
  );
}

function FormField({
  label,
  hint,
  hintAlign = "center",
  children,
}: {
  label: React.ReactNode;
  hint?: string;
  hintAlign?: "center" | "right";
  children: React.ReactNode;
}) {
  return (
    <div>
      <Label>
        <span className="inline-flex items-center gap-1">
          {label}
          {hint ? <InfoHint text={hint} align={hintAlign} /> : null}
        </span>
      </Label>
      {children}
    </div>
  );
}

/** FormField label suffixed with a muted "(calculado)" — for fields that are always derived, never typed into directly. */
function CalculatedLabel({ text }: { text: string }) {
  return (
    <>
      {text}{" "}
      <span className="font-normal normal-case text-gray-300 dark:text-gray-600">
        (calculado)
      </span>
    </>
  );
}

/** Same Label-above-control shape as FormField, so a switch lines up with the Inputs/Selects around it instead of sitting inline with its label. */
function SwitchField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="flex h-11 items-center">
        <ControlledSwitch checked={checked} onChange={onChange} />
      </div>
    </div>
  );
}

export default function ReservationDetailModal({
  reservation,
  isOpen,
  onClose,
  createMode = false,
  onSaved,
  onDeleted,
}: ReservationDetailModalProps) {
  const [detail, setDetail] = useState<Reservation | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [isSavingMenores, setIsSavingMenores] = useState(false);
  const [menoresError, setMenoresError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [form, setForm] = useState<FormState>(CREATE_DEFAULTS);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gastoExpanded, setGastoExpanded] = useState(false);

  // Precio -> Ingreso -> Ingreso estimado auto-fill (create mode only);
  // each stops once the operator edits that specific field by hand.
  const [incomeTouched, setIncomeTouched] = useState(false);
  const [incomeEstimadoTouched, setIncomeEstimadoTouched] = useState(false);
  const [incomeEstimadoFocused, setIncomeEstimadoFocused] = useState(false);
  const [trmError, setTrmError] = useState<string | null>(null);
  const [trmLoading, setTrmLoading] = useState(false);

  // Partido picker (create mode only) — kept out of FormState since it
  // holds a full object for display, not a plain form value.
  const [selectedPartido, setSelectedPartido] = useState<PartidoListItem | null>(null);
  const [partidoCandidates, setPartidoCandidates] = useState<PartidoListItem[] | null>(null);
  const [partidoLookupLoading, setPartidoLookupLoading] = useState(false);
  // Linked partido for view-mode WhatsApp itinerary (Reservation only has partido_id).
  const [linkedPartido, setLinkedPartido] = useState<PartidoListItem | null>(null);

  // View-mode Resumen: live TRM estimate, only used when the reserva has
  // no stored income_estimado.
  const [liveIncomeEstimado, setLiveIncomeEstimado] = useState<number | null>(null);
  const [liveIncomeEstimadoFailed, setLiveIncomeEstimadoFailed] = useState(false);

  function resetAutoFillState() {
    setIncomeTouched(false);
    setIncomeEstimadoTouched(false);
    setIncomeEstimadoFocused(false);
    setTrmError(null);
    setTrmLoading(false);
    setSelectedPartido(null);
    setPartidoCandidates(null);
    setPartidoLookupLoading(false);
    setLinkedPartido(null);
    setGastoExpanded(false);
  }

  useEffect(() => {
    if (!isOpen) {
      setDetail(null);
      setRefreshError(null);
      setIsEditing(false);
      setForm(CREATE_DEFAULTS);
      setError(null);
      resetAutoFillState();
      return;
    }

    if (createMode) {
      setDetail(null);
      setRefreshError(null);
      setIsEditing(true);
      setForm(CREATE_DEFAULTS);
      setError(null);
      resetAutoFillState();
      return;
    }

    if (!reservation) {
      setDetail(null);
      return;
    }

    setDetail(null);
    setRefreshError(null);
    setIsEditing(false);
    setError(null);
    resetAutoFillState();

    let cancelled = false;
    setIsRefreshing(true);

    void (async () => {
      try {
        const fresh = await fetchReservaById(reservation.id);
        if (!cancelled) {
          setDetail(fresh);
          setRefreshError(null);
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof ApiError
              ? err.message
              : "No se pudo actualizar el detalle";
          setRefreshError(message);
        }
      } finally {
        if (!cancelled) setIsRefreshing(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isOpen, reservation, createMode]);

  useEffect(() => {
    if (!createMode) return;
    const preset = EXPERIENCIA_PRESETS[form.nombre_experiencia];
    if (!preset) return;
    setForm((prev) => ({
      ...prev,
      ciudad_experiencia: preset.ciudad,
      meeting_point: preset.meetingPoint,
      tipo_tour: "football tour",
    }));
  }, [form.nombre_experiencia, createMode]);

  // Precio -> Ingreso, until the operator edits Ingreso by hand.
  useEffect(() => {
    if (!createMode || incomeTouched) return;
    const price = Number(form.price);
    if (!form.price.trim() || Number.isNaN(price)) return;
    const rate = INCOME_RATE_BY_PROVIDER[form.booking_provider] ?? 1;
    setForm((prev) => ({ ...prev, income: (price * rate).toFixed(2) }));
  }, [form.price, form.booking_provider, createMode, incomeTouched]);

  // Ingreso (+ Moneda) -> Ingreso estimado + TRM estimado, until the operator
  // edits Ingreso estimado by hand — TRM estimado has no manual override UI
  // in create mode (it's purely a third-party lookup), so it always tracks
  // the same auto-fill toggle as Ingreso estimado. COP is a direct
  // passthrough (no TRM applies); the fetched rate becomes trm_estimado and
  // income_estimado = income * rate, debounced so Precio's keystroke-by-
  // keystroke cascade doesn't fire one request per keystroke.
  useEffect(() => {
    if (!createMode || incomeEstimadoTouched) return;
    setTrmError(null);

    if (form.moneda === "COP") {
      setForm((prev) => ({ ...prev, income_estimado: form.income, trm_estimado: "" }));
      return;
    }

    const income = Number(form.income);
    if (!form.income.trim() || Number.isNaN(income)) return;

    let cancelled = false;
    setTrmLoading(true);
    const timer = setTimeout(() => {
      void (async () => {
        try {
          const rate = await fetchTrmToCop(form.moneda);
          if (!cancelled) {
            setForm((prev) => ({
              ...prev,
              income_estimado: (income * rate).toFixed(2),
              trm_estimado: rate.toFixed(2),
            }));
          }
        } catch {
          if (!cancelled) {
            setTrmError(
              "No fue posible calcular el ingreso estimado por un error al buscar el TRM del día",
            );
          }
        } finally {
          if (!cancelled) setTrmLoading(false);
        }
      })();
    }, TRM_FETCH_DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      setTrmLoading(false);
    };
  }, [form.income, form.moneda, createMode, incomeEstimadoTouched]);

  // Edit mode: once the operator finishes filling in a previously-null
  // trm_estimado, derive Ingreso estimado the same way creation does
  // (income * trm_estimado) — same formula, just triggered by manual entry
  // instead of the auto-fetch. Only applies while trm_estimado is still the
  // editable/unlocked case; stops once the operator edits Ingreso estimado
  // by hand.
  useEffect(() => {
    if (createMode || detail?.trm_estimado != null || incomeEstimadoTouched) {
      return;
    }
    const rate = Number(form.trm_estimado);
    const income = Number(form.income);
    if (!form.trm_estimado.trim() || Number.isNaN(rate)) return;
    if (!form.income.trim() || Number.isNaN(income)) return;
    setForm((prev) => ({ ...prev, income_estimado: (income * rate).toFixed(2) }));
  }, [
    form.trm_estimado,
    form.income,
    createMode,
    detail?.trm_estimado,
    incomeEstimadoTouched,
  ]);

  // A stale partido link shouldn't silently survive a city/date edit.
  useEffect(() => {
    if (!createMode) return;
    setSelectedPartido(null);
    setPartidoCandidates(null);
  }, [form.ciudad_experiencia, form.fecha_evento, createMode]);

  // View-mode Resumen: prefer the stored income_estimado; only fetch a
  // live TRM when it's missing (old/pipeline records).
  useEffect(() => {
    setLiveIncomeEstimado(null);
    setLiveIncomeEstimadoFailed(false);
    if (!detail || detail.income_estimado !== null) return;
    if (detail.moneda === "COP") {
      setLiveIncomeEstimado(Number(detail.income));
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const rate = await fetchTrmToCop(detail.moneda);
        if (!cancelled) setLiveIncomeEstimado(Number(detail.income) * rate);
      } catch {
        if (!cancelled) setLiveIncomeEstimadoFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [detail]);

  useEffect(() => {
    const partidoId = detail?.partido_id;
    if (!partidoId) {
      setLinkedPartido(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const partido = await fetchPartidoById(partidoId);
        if (!cancelled) setLinkedPartido(partido);
      } catch {
        if (!cancelled) setLinkedPartido(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [detail?.partido_id]);

  if (!reservation && !createMode) return null;

  const preview = detail ?? reservation;
  const esHoy = detail?.es_hoy ?? reservation?.es_hoy ?? false;
  const titleRef = detail?.reserva_reference;
  const whatsappWelcomeUrl = detail
    ? buildWhatsAppShareUrl(detail, "welcome")
    : null;
  const whatsappItineraryUrl = detail
    ? buildWhatsAppShareUrl(detail, "itinerary", linkedPartido)
    : null;
  const calendarUrl = detail ? buildGoogleCalendarUrl(detail) : null;
  const isFootballTour = detail?.tipo_tour === "football tour";
  const incomeEstimadoCOP =
    detail?.income_estimado !== null && detail?.income_estimado !== undefined
      ? Number(detail.income_estimado)
      : liveIncomeEstimado;
  // Whether to show TRM estimado as a locked caption vs. an editable input.
  // Must come from `detail` (fixed for the whole edit session), not the
  // live `form.trm_estimado` — that flips truthy after the operator's very
  // first keystroke, which would yank the input out from under them mid-edit.
  const trmEstimadoLocked = detail?.trm_estimado != null;
  // Live preview of Ingreso final in the edit form — income_final has no
  // backing FormState field (it's never submitted, purely derived for
  // display), so it's recomputed straight from income + trm_final on every
  // render instead.
  const editFormIncomeFinal = (() => {
    const income = Number(form.income);
    if (!form.income.trim() || Number.isNaN(income)) return null;
    if (form.moneda === "COP") return income;
    const rate = Number(form.trm_final);
    if (!form.trm_final.trim() || Number.isNaN(rate)) return null;
    return income * rate;
  })();

  const isValid =
    form.nombre_experiencia.trim().length > 0 &&
    form.ciudad_experiencia.trim().length > 0 &&
    form.customer_name.trim().length > 0 &&
    form.price.trim().length > 0 &&
    !Number.isNaN(Number(form.price)) &&
    Number(form.price) > 0 &&
    form.income.trim().length > 0 &&
    !Number.isNaN(Number(form.income)) &&
    Number(form.income) > 0 &&
    form.booking_provider.length > 0 &&
    !Number.isNaN(Number(form.participants)) &&
    Number(form.participants) >= 0;

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleEditClick() {
    if (!detail) return;
    setForm(seedFormFromDetail(detail));
    setError(null);
    setIsEditing(true);
  }

  function handleCancelEdit() {
    if (createMode) {
      onClose();
      return;
    }
    setIsEditing(false);
    setError(null);
  }

  async function handleLookupPartidos() {
    if (!form.ciudad_experiencia || !form.fecha_evento) return;
    const window = dayWindow(toIsoUtc(form.fecha_evento));
    setPartidoLookupLoading(true);
    try {
      const items = await lookupPartidosCached(
        form.ciudad_experiencia,
        window,
      );
      setPartidoCandidates(items);
    } catch {
      setPartidoCandidates([]);
    } finally {
      setPartidoLookupLoading(false);
    }
  }

  async function handleMenoresDeEdadChange(next: boolean) {
    if (!detail) return;
    const previous = detail.menores_de_edad;
    setDetail({ ...detail, menores_de_edad: next });
    setMenoresError(null);
    setIsSavingMenores(true);
    try {
      const updated = await updateReserva(detail.id, {
        menores_de_edad: next,
      });
      setDetail(updated);
    } catch (err) {
      setDetail((current) =>
        current ? { ...current, menores_de_edad: previous } : current,
      );
      setMenoresError(
        err instanceof ApiError ? err.message : "No se pudo guardar",
      );
    } finally {
      setIsSavingMenores(false);
    }
  }

  async function handleSave() {
    if (!isValid) return;
    setSaving(true);
    setError(null);
    try {
      if (createMode) {
        const basePayload: Omit<ReservaCreatePayload, "reserva_reference"> = {
          source: "manual",
          booking_provider: form.booking_provider,
          sender: null,
          estado: CREATE_ESTADO,
          subject: null,
          fecha_email_recibido: new Date().toISOString(),
          nombre_experiencia: form.nombre_experiencia.trim(),
          ciudad_experiencia: form.ciudad_experiencia.trim(),
          fecha_evento: form.fecha_evento ? toIsoUtc(form.fecha_evento) : null,
          participants: Number(form.participants),
          customer_name: form.customer_name.trim(),
          phone: normalizePhone(form.phone),
          pais_del_visitante: form.pais_del_visitante.trim(),
          moneda: form.moneda.trim() || "USD",
          price: form.price.trim(),
          income: form.income.trim(),
          notificado_whatsapp: form.notificado_whatsapp,
          notas_cliente: form.notas_cliente.trim() || null,
          tipo_tour: form.tipo_tour || null,
          notas_personales: form.notas_personales.trim() || null,
          meeting_point: form.meeting_point || null,
          lugar_de_recogida: form.lugar_de_recogida.trim() || null,
          income_estimado: form.income_estimado.trim() || null,
          trm_estimado:
            form.moneda.trim() === "COP"
              ? null
              : form.trm_estimado.trim() || null,
          menores_de_edad: form.menores_de_edad,
          partido_id: selectedPartido?.id ?? null,
        };

        for (let attempt = 1; attempt <= MAX_CREATE_ATTEMPTS; attempt += 1) {
          try {
            await createReserva({
              ...basePayload,
              reserva_reference: buildReservaReference(form.booking_provider),
            });
            onSaved?.();
            onClose();
            return;
          } catch (err) {
            const isReferenceCollision =
              err instanceof ApiError && err.status === 409;
            if (!isReferenceCollision || attempt === MAX_CREATE_ATTEMPTS) {
              throw err;
            }
            // Reference collided with an existing reserva — regenerate and retry.
          }
        }
        return;
      }

      if (!detail) return;
      const payload: ReservaUpdatePayload = {
        booking_provider: form.booking_provider,
        nombre_experiencia: form.nombre_experiencia.trim(),
        ciudad_experiencia: form.ciudad_experiencia.trim(),
        fecha_evento: form.fecha_evento ? toIsoUtc(form.fecha_evento) : null,
        participants: Number(form.participants),
        customer_name: form.customer_name.trim(),
        phone: form.phone.trim(),
        pais_del_visitante: form.pais_del_visitante.trim(),
        moneda: form.moneda.trim() || "USD",
        price: form.price.trim(),
        income: form.income.trim(),
        notificado_whatsapp: form.notificado_whatsapp,
        notas_cliente: form.notas_cliente.trim() || null,
        tipo_tour: form.tipo_tour || null,
        notas_personales: form.notas_personales.trim() || null,
        meeting_point: form.meeting_point || null,
        lugar_de_recogida: form.lugar_de_recogida.trim() || null,
        income_estimado: form.income_estimado.trim() || null,
        trm_estimado:
          form.moneda.trim() === "COP" ? null : form.trm_estimado.trim() || null,
        trm_final:
          form.moneda.trim() === "COP" ? null : form.trm_final.trim() || null,
        menores_de_edad: form.menores_de_edad,
      };
      const updated = await updateReserva(detail.id, payload);
      setDetail(updated);
      setIsEditing(false);
      onSaved?.();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo guardar la reserva",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!detail) return;
    const confirmed = window.confirm(
      "¿Eliminar esta reserva? Esta acción no se puede deshacer.",
    );
    if (!confirmed) return;

    setDeleting(true);
    setError(null);
    try {
      await deleteReserva(detail.id);
      onDeleted?.();
      onClose();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo eliminar la reserva",
      );
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      className="m-4 max-w-[640px] overflow-visible p-5 sm:p-6"
    >
      <div className="pr-8">
        {createMode ? (
          <h4 className="mb-4 text-title-sm font-semibold text-gray-800 dark:text-white/90">
            Nueva reserva
          </h4>
        ) : (
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              {preview ? (
                <ProviderLogo provider={preview.booking_provider} size={40} />
              ) : null}
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h4 className="text-title-sm font-semibold text-gray-800 dark:text-white/90">
                    {titleRef
                      ? `Reserva ${titleRef}`
                      : preview?.nombre_experiencia}
                  </h4>
                  {isFootballTour ? (
                    <InfoTooltip
                      label={TIPO_TOUR_LABELS["football tour"]}
                      underline={false}
                    >
                      <span aria-hidden="true">⚽</span>
                      <span className="sr-only">
                        {TIPO_TOUR_LABELS["football tour"]}
                      </span>
                    </InfoTooltip>
                  ) : null}
                  <EsHoyStatusDot esHoy={esHoy} tooltipSide="right" />
                </div>
                {isRefreshing ? (
                  <p
                    role="status"
                    aria-live="polite"
                    className="mt-1 text-theme-xs text-gray-400 dark:text-gray-500"
                  >
                    Actualizando…
                  </p>
                ) : null}
              </div>
            </div>
            <ShareMenu
              className="shrink-0"
              options={[
                {
                  id: "whatsapp-welcome",
                  label: "WhatsApp Welcome",
                  icon: <WhatsappIcon />,
                  href: whatsappWelcomeUrl,
                  disabled: !whatsappWelcomeUrl,
                },
                {
                  id: "whatsapp-itinerary",
                  label: "WhatsApp Itinerary",
                  icon: <WhatsappIcon />,
                  href: whatsappItineraryUrl,
                  disabled: !whatsappItineraryUrl,
                },
                {
                  id: "calendar",
                  label: "Google Calendar",
                  icon: <CalendarIcon />,
                  href: calendarUrl,
                  disabled: !calendarUrl,
                },
              ]}
            />
          </div>
        )}

        {refreshError ? (
          <p
            role="alert"
            className="mb-3 rounded-lg border border-error-200 bg-error-50 px-3 py-2 text-theme-sm text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
          >
            {refreshError}
          </p>
        ) : null}

        {error ? (
          <p
            role="alert"
            className="mb-3 rounded-lg border border-error-200 bg-error-50 px-3 py-2 text-theme-sm text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
          >
            {error}
          </p>
        ) : null}

        {!createMode && !isEditing && preview ? (
          <div className="mb-4 rounded-xl border border-gray-100 bg-gray-50/70 px-3.5 py-3 dark:border-gray-800 dark:bg-white/[0.02]">
            <p className="text-sm font-semibold text-gray-800 dark:text-white/90">
              {preview.nombre_experiencia}
            </p>
            <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
              {[
                preview.ciudad_experiencia,
                formatRawDateTime(preview.fecha_evento),
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </div>
        ) : null}

        {createMode || isEditing ? (
          <div className="max-h-[min(65vh,34rem)] space-y-5 overflow-y-auto overflow-x-hidden pe-1">
            <section>
              <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                Detalles
              </h5>
              <div className="mb-4">
                <FormField label="Nombre de la experiencia">
                  {createMode ? (
                    <Select
                      key={`experiencia-${form.nombre_experiencia}`}
                      options={experienciaOptions}
                      placeholder="Selecciona una experiencia"
                      defaultValue={form.nombre_experiencia}
                      onChange={(value) =>
                        update("nombre_experiencia", value)
                      }
                    />
                  ) : (
                    <Input
                      type="text"
                      maxLength={512}
                      value={form.nombre_experiencia}
                      onChange={(e) =>
                        update("nombre_experiencia", e.target.value)
                      }
                      placeholder="City Tour"
                    />
                  )}
                </FormField>
              </div>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
                <div className="sm:flex-1">
                  <FormField label="Proveedor">
                    <Select
                      key={`provider-${form.booking_provider}`}
                      options={bookingProviderOptions}
                      placeholder="Selecciona un proveedor"
                      defaultValue={form.booking_provider}
                      onChange={(value) => update("booking_provider", value)}
                    />
                  </FormField>
                </div>
                <div className="sm:flex-1">
                  <FormField label="Ciudad">
                    {createMode ? (
                      <Select
                        key={`ciudad-${form.ciudad_experiencia}`}
                        options={ciudadOptions}
                        placeholder="Selecciona una ciudad"
                        defaultValue={form.ciudad_experiencia}
                        onChange={(value) =>
                          update("ciudad_experiencia", value)
                        }
                      />
                    ) : (
                      <Input
                        type="text"
                        maxLength={255}
                        value={form.ciudad_experiencia}
                        onChange={(e) =>
                          update("ciudad_experiencia", e.target.value)
                        }
                        placeholder="Cartagena"
                      />
                    )}
                  </FormField>
                </div>
                <div className="sm:w-[220px] sm:shrink-0">
                  <FormField label="Fecha del evento">
                    <Input
                      type="datetime-local"
                      value={form.fecha_evento}
                      onChange={(e) => update("fecha_evento", e.target.value)}
                    />
                  </FormField>
                </div>
              </div>
            </section>

            {createMode ? (
              <section>
                <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                  Partido
                </h5>
                {selectedPartido ? (
                  <div className="flex items-center justify-between gap-3 rounded-xl border border-gray-100 px-3.5 py-2.5 dark:border-gray-800">
                    <span className="min-w-0 truncate text-theme-sm text-gray-800 dark:text-white/90">
                      {partidoLabel(selectedPartido)}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setSelectedPartido(null)}
                    >
                      Quitar
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleLookupPartidos}
                      disabled={
                        !form.ciudad_experiencia ||
                        !form.fecha_evento ||
                        partidoLookupLoading
                      }
                    >
                      {partidoLookupLoading
                        ? "Buscando…"
                        : "+ Buscar partido"}
                    </Button>
                    {!form.ciudad_experiencia || !form.fecha_evento ? (
                      <p className="text-theme-xs text-gray-400 dark:text-gray-500">
                        Completa Ciudad y Fecha del evento para buscar.
                      </p>
                    ) : null}
                    {partidoCandidates !== null ? (
                      partidoCandidates.length === 0 ? (
                        <p className="text-theme-xs text-gray-500 dark:text-gray-400">
                          No se encontraron partidos para esta ciudad y
                          fecha.
                        </p>
                      ) : (
                        <div className="space-y-1.5">
                          <p className="text-theme-xs text-gray-500 dark:text-gray-400">
                            Haz clic en un partido para vincularlo a esta
                            reserva:
                          </p>
                          <ul className="space-y-1.5 rounded-xl border border-gray-100 p-2 dark:border-gray-800">
                            {partidoCandidates.map((partido) => (
                              <li key={partido.id}>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setSelectedPartido(partido);
                                    setPartidoCandidates(null);
                                  }}
                                  className="group flex w-full items-center justify-between gap-3 rounded-lg border border-transparent px-2.5 py-2 text-left transition-colors hover:border-brand-200 hover:bg-brand-50/50 dark:hover:border-brand-500/30 dark:hover:bg-brand-500/10"
                                >
                                  <span className="min-w-0 truncate text-theme-sm text-gray-700 dark:text-gray-300">
                                    {partidoLabel(partido)}
                                  </span>
                                  <span className="shrink-0 text-theme-xs font-medium text-brand-600 opacity-0 transition-opacity group-hover:opacity-100 dark:text-brand-400">
                                    Vincular
                                  </span>
                                </button>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )
                    ) : null}
                  </div>
                )}
              </section>
            ) : null}

            <section>
              <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                Cliente
              </h5>
              <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-start">
                <div className="sm:flex-1">
                  <FormField label="Nombre">
                    <Input
                      type="text"
                      maxLength={255}
                      value={form.customer_name}
                      onChange={(e) =>
                        update("customer_name", e.target.value)
                      }
                      placeholder="Ada Lovelace"
                    />
                  </FormField>
                </div>
                <div className="sm:w-20 sm:shrink-0">
                  <FormField label="Personas">
                    <Input
                      type="number"
                      min="0"
                      value={form.participants}
                      onChange={(e) =>
                        update("participants", e.target.value)
                      }
                    />
                  </FormField>
                </div>
                <div className="shrink-0">
                  <SwitchField
                    label="Menores de edad"
                    checked={form.menores_de_edad}
                    onChange={(next) => update("menores_de_edad", next)}
                  />
                </div>
                <div className="shrink-0">
                  <SwitchField
                    label="Notificado WhatsApp"
                    checked={form.notificado_whatsapp}
                    onChange={(next) =>
                      update("notificado_whatsapp", next)
                    }
                  />
                </div>
              </div>
              <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                <FormField label="Teléfono">
                  <Input
                    type="text"
                    maxLength={64}
                    value={form.phone}
                    onChange={(e) => update("phone", e.target.value)}
                    onBlur={() => update("phone", normalizePhone(form.phone))}
                    placeholder="+573001112233"
                  />
                </FormField>
                <FormField label="País">
                  <Input
                    type="text"
                    maxLength={128}
                    list={`pais-options-${detail?.id ?? "new"}`}
                    value={form.pais_del_visitante}
                    onChange={(e) =>
                      update("pais_del_visitante", e.target.value)
                    }
                    placeholder="Colombia"
                  />
                  <datalist id={`pais-options-${detail?.id ?? "new"}`}>
                    {COUNTRY_NAMES.map((name) => (
                      <option key={name} value={name} />
                    ))}
                  </datalist>
                </FormField>
                <FormField label="Punto de encuentro">
                  <Select
                    key={`meeting-${form.meeting_point}`}
                    options={meetingPointOptions}
                    placeholder="Selecciona un punto"
                    defaultValue={form.meeting_point}
                    onChange={(value) => update("meeting_point", value)}
                  />
                </FormField>
                <FormField
                  label="Lugar de entrega"
                  hint="Lugar donde se está hospedando o se acordó devolver al cliente."
                >
                  <Input
                    type="text"
                    value={form.lugar_de_recogida}
                    onChange={(e) =>
                      update("lugar_de_recogida", e.target.value)
                    }
                  />
                </FormField>
                <FormField label="Tipo de tour">
                  <Select
                    key={`tipo-tour-${form.tipo_tour}`}
                    options={
                      createMode ? tipoTourOptionsCreate : tipoTourOptionsEdit
                    }
                    placeholder="Selecciona un tipo"
                    defaultValue={form.tipo_tour}
                    onChange={(value) => update("tipo_tour", value)}
                  />
                </FormField>
              </div>
            </section>

            <section>
              <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                Financiero
              </h5>
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
                <div className="lg:w-24 lg:shrink-0">
                  <FormField label="Moneda">
                    <Select
                      key={`moneda-${form.moneda}`}
                      options={monedaOptions}
                      placeholder="Moneda"
                      defaultValue={form.moneda}
                      onChange={(value) => update("moneda", value)}
                    />
                  </FormField>
                </div>
                <div className="flex-1">
                  <FormField
                    label="Precio"
                    hint="Valor que el cliente pagó al proveedor."
                  >
                    <Input
                      type="text"
                      value={form.price}
                      onChange={(e) => update("price", e.target.value)}
                      placeholder="120.50"
                    />
                  </FormField>
                </div>
                <div className="flex-1">
                  <FormField label="Ingreso" hint="Valor que ViveCaribe recibe.">
                    <Input
                      type="text"
                      value={form.income}
                      onChange={(e) => {
                        setIncomeTouched(true);
                        update("income", e.target.value);
                      }}
                      placeholder="84.35"
                    />
                  </FormField>
                </div>
                {createMode ? (
                  <div className="lg:w-46 lg:shrink-0">
                    <FormField
                      label="Ingreso estimado"
                      hint={
                        form.moneda === "COP"
                          ? "Mismo valor que Ingreso, ya está en COP."
                          : "Calculado con el TRM estimado (de un tercero) sobre el Ingreso."
                      }
                      hintAlign="right"
                    >
                      <Input
                        type="text"
                        prefix="COP"
                        value={
                          trmLoading
                            ? "Calculando…"
                            : incomeEstimadoFocused
                              ? form.income_estimado
                              : formatPlainNumberCO(form.income_estimado)
                        }
                        disabled={trmLoading}
                        onFocus={() => setIncomeEstimadoFocused(true)}
                        onBlur={() => setIncomeEstimadoFocused(false)}
                        onChange={(e) => {
                          setIncomeEstimadoTouched(true);
                          update("income_estimado", e.target.value);
                        }}
                      />
                      {trmError ? (
                        <p
                          role="alert"
                          className="mt-1.5 text-theme-xs text-error-600 dark:text-error-400"
                        >
                          {trmError}
                        </p>
                      ) : null}
                    </FormField>
                  </div>
                ) : null}
              </div>

              {/* Edit mode only: Estimado (creation-time guess) and Final
                  (post-payment reality) each get their own bordered panel,
                  rate above the amount it derives — so the two pairs read as
                  parallel, separate groups instead of one field tucked under
                  Ingreso estimado and the other stranded in an unrelated row.
                  Both derived amounts render disabled: they're always
                  computed, never typed into directly. */}
              {!createMode && form.moneda !== "COP" ? (
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-xl border border-gray-100 bg-gray-50/40 p-3 dark:border-gray-800 dark:bg-white/[0.02]">
                    <p className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                      Estimado
                    </p>
                    <div className="space-y-3">
                      <FormField
                        label="TRM estimado"
                        hint={
                          trmEstimadoLocked
                            ? "Se fijó al crear la reserva y ya no se puede editar."
                            : "Tomado de un tercero al crear la reserva; aquí se puede completar si quedó vacío. Solo números."
                        }
                      >
                        <Input
                          type="text"
                          prefix="COP"
                          placeholder="0.00"
                          disabled={trmEstimadoLocked}
                          value={
                            trmEstimadoLocked
                              ? formatPlainNumberCO(form.trm_estimado)
                              : form.trm_estimado
                          }
                          onChange={
                            trmEstimadoLocked
                              ? undefined
                              : (e) =>
                                  update(
                                    "trm_estimado",
                                    sanitizeDecimalInput(e.target.value),
                                  )
                          }
                        />
                      </FormField>
                      <FormField label={<CalculatedLabel text="Ingreso estimado" />}>
                        <Input
                          type="text"
                          prefix="COP"
                          placeholder="Pendiente"
                          disabled
                          value={formatPlainNumberCO(form.income_estimado)}
                        />
                      </FormField>
                    </div>
                  </div>

                  <div className="rounded-xl border border-gray-100 bg-gray-50/40 p-3 dark:border-gray-800 dark:bg-white/[0.02]">
                    <p className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                      Final
                    </p>
                    <div className="space-y-3">
                      <FormField
                        label="TRM Final"
                        hint="Se llena cuando se recibe el pago; hasta entonces el profit queda pendiente. Solo números."
                      >
                        <Input
                          type="text"
                          prefix="COP"
                          placeholder="0.00"
                          value={form.trm_final}
                          onChange={(e) =>
                            update(
                              "trm_final",
                              sanitizeDecimalInput(e.target.value),
                            )
                          }
                        />
                      </FormField>
                      <FormField label={<CalculatedLabel text="Ingreso final" />}>
                        <Input
                          type="text"
                          prefix="COP"
                          placeholder="Pendiente TRM Final"
                          disabled
                          value={
                            editFormIncomeFinal !== null
                              ? formatPlainNumberCO(editFormIncomeFinal.toFixed(2))
                              : ""
                          }
                        />
                      </FormField>
                    </div>
                  </div>
                </div>
              ) : null}

              {!createMode ? (
                <div className="mt-4 grid grid-cols-1 sm:grid-cols-2">
                  <FormField
                    label={<CalculatedLabel text="Costos" />}
                    hint="Suma de la parte de esta reserva en los gastos del partido. Se edita desde la sección Gastos del partido."
                  >
                    <Input
                      type="text"
                      prefix="COP"
                      placeholder="Sin gastos registrados"
                      disabled
                      value={
                        detail?.costos != null
                          ? formatPlainNumberCO(detail.costos)
                          : ""
                      }
                    />
                  </FormField>
                </div>
              ) : null}
            </section>

            <section>
              <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                Notas
              </h5>
              <div className="space-y-4">
                <div>
                  <Label>Notas personales</Label>
                  <TextArea
                    value={form.notas_personales}
                    onChange={(value) => update("notas_personales", value)}
                    rows={2}
                    placeholder="Sin notas"
                  />
                </div>
                <div>
                  <Label>Notas cliente</Label>
                  <TextArea
                    value={form.notas_cliente}
                    onChange={(value) => update("notas_cliente", value)}
                    rows={2}
                    placeholder="Sin notas"
                  />
                </div>
              </div>
            </section>
          </div>
        ) : detail ? (
          <div className="max-h-[min(65vh,34rem)] space-y-4 overflow-y-auto overflow-x-hidden pe-1">
            <section>
              <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                Cliente
              </h5>
              <div className="flex flex-col gap-4 sm:flex-row sm:gap-x-6">
                <dl className="grid min-w-0 flex-1 grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-1.5">
                  <DetailRow label="Nombre" value={detail.customer_name} />
                  <DetailRow label="Personas" value={detail.participants} />
                  <DetailRow label="Teléfono" value={detail.phone || "—"} />
                  <DetailRow
                    label="País"
                    value={detail.pais_del_visitante || "—"}
                  />
                </dl>

                <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-1.5">
                  <DetailRow
                    label="Menores de edad"
                    value={
                      <div className="inline-flex items-center rounded-lg border border-brand-100 bg-brand-50/40 px-2 py-1 dark:border-brand-500/20 dark:bg-brand-500/5">
                        <ControlledSwitch
                          checked={detail.menores_de_edad}
                          disabled={isSavingMenores}
                          onChange={handleMenoresDeEdadChange}
                        />
                      </div>
                    }
                  />
                  {menoresError ? (
                    <>
                      <dt />
                      <dd className="text-theme-xs text-error-600 dark:text-error-400">
                        {menoresError}
                      </dd>
                    </>
                  ) : null}
                  <DetailRow
                    label="Punto de encuentro"
                    value={
                      detail.meeting_point ? (
                        <Badge size="sm" color="light">
                          {MEETING_POINT_LABELS[detail.meeting_point] ??
                            detail.meeting_point}
                        </Badge>
                      ) : (
                        "—"
                      )
                    }
                  />
                  <DetailRow
                    label="WhatsApp"
                    value={
                      <Badge
                        size="sm"
                        color={detail.notificado_whatsapp ? "success" : "light"}
                      >
                        {detail.notificado_whatsapp ? "Sí" : "No"}
                      </Badge>
                    }
                  />
                  <DetailRow
                    label="Lugar de entrega"
                    value={(() => {
                      const { display, truncated } = truncateText(
                        detail.lugar_de_recogida,
                        20,
                      );
                      return truncated ? (
                        <InfoTooltip label={detail.lugar_de_recogida ?? ""}>
                          {display}
                        </InfoTooltip>
                      ) : (
                        display
                      );
                    })()}
                  />
                </dl>
              </div>
            </section>

            <section>
              <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                Partido asociado
              </h5>
              <PartidoSelector
                reservationId={detail.id}
                ciudadExperiencia={detail.ciudad_experiencia}
                fechaEvento={detail.fecha_evento}
                partidoId={detail.partido_id}
                onChanged={(next) =>
                  setDetail((current) =>
                    current ? { ...current, partido_id: next } : current,
                  )
                }
              />
            </section>

            <section>
              <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                Resumen
              </h5>
              <div className="rounded-xl border border-gray-100 p-3.5 dark:border-gray-800">
                {/* Hero row: the bottom line — what actually happened.
                    Ingreso final always resolves (COP needs no conversion,
                    so it's just Ingreso there), so it anchors the section
                    at the largest size, alongside the profit it produces.
                    Empty values render as a plain "—" at hero size — a full
                    sentence ("Pendiente TRM del pago") reads as an error at that
                    scale, so the explanation moves to the small caption
                    instead. */}
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <StatCard
                    emphasis="hero"
                    label="Ingreso final"
                    value={formatCOP(detail.income_final)}
                    caption={
                      detail.moneda !== "COP" && detail.trm_final === null
                        ? "Pendiente TRM del pago"
                        : undefined
                    }
                  />
                  <StatCard
                    emphasis="hero"
                    label="Profit"
                    value={
                      <span className="inline-flex flex-wrap items-center gap-2">
                        <span
                          className={
                            detail.profit !== null && Number(detail.profit) < 0
                              ? "text-error-600 dark:text-error-400"
                              : undefined
                          }
                        >
                          {formatCOP(detail.profit)}
                        </span>
                        {detail.percentage_profit !== null ? (
                          <Badge
                            size="sm"
                            color={
                              Number(detail.percentage_profit) < 0 ? "error" : "success"
                            }
                          >
                            {Math.round(Number(detail.percentage_profit))}%
                          </Badge>
                        ) : null}
                      </span>
                    }
                    caption={
                      detail.costos !== null
                        ? `Costos: ${formatCOP(detail.costos)}`
                        : "Costos sin definir"
                    }
                  />
                </div>

                {/* Secondary row: supporting reference figures — Ingreso is
                    the second-most important number (what the client's
                    payment nominally is before conversion/costs), Ingreso
                    estimado is only a creation-time guess, and Costos feeds
                    the hero Profit card above. */}
                <div
                  className={`mt-3 grid grid-cols-1 gap-3 ${
                    detail.moneda === "COP" ? "sm:grid-cols-2" : "sm:grid-cols-3"
                  }`}
                >
                  <StatCard
                    label="Ingreso"
                    value={
                      <InfoTooltip
                        label={`El cliente pagó ${formatPrice(detail.price, detail.moneda)} en total`}
                      >
                        {formatPrice(detail.income, detail.moneda)}
                      </InfoTooltip>
                    }
                  />
                  {detail.moneda !== "COP" ? (
                    <StatCard
                      label="Ingreso estimado"
                      value={
                        detail.trm_estimado !== null || liveIncomeEstimadoFailed ? (
                          formatCOP(incomeEstimadoCOP)
                        ) : (
                          <InfoTooltip label={`TRM real del día, ${detail.moneda} → COP`}>
                            {formatCOP(incomeEstimadoCOP)}
                          </InfoTooltip>
                        )
                      }
                      caption={
                        detail.trm_estimado !== null
                          ? `TRM estimado: ${formatCOP(detail.trm_estimado)}`
                          : undefined
                      }
                    />
                  ) : null}
                  <StatCard label="Costos" value={formatCOP(detail.costos)} />
                </div>

                <p className="mt-3 text-theme-xs text-gray-400 dark:text-gray-500">
                  Pago estimado:{" "}
                  <span className="font-medium text-gray-600 dark:text-gray-300">
                    {formatPaidAtDate(detail.paid_at)}
                  </span>
                </p>
              </div>

              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="mb-1 text-theme-xs font-medium text-gray-400 dark:text-gray-500">
                    Notas personales
                  </p>
                  <TextArea
                    value={detail.notas_personales ?? ""}
                    onChange={() => {}}
                    rows={2}
                    disabled
                    placeholder="Sin notas"
                  />
                </div>
                <div>
                  <p className="mb-1 text-theme-xs font-medium text-gray-400 dark:text-gray-500">
                    Notas cliente
                  </p>
                  <TextArea
                    value={detail.notas_cliente ?? ""}
                    onChange={() => {}}
                    rows={2}
                    disabled
                    placeholder="Sin notas"
                  />
                </div>
              </div>
            </section>

            {detail.partido_id ? (
              <section className="rounded-xl border border-gray-100 dark:border-gray-800">
                <button
                  type="button"
                  aria-expanded={gastoExpanded}
                  onClick={() => setGastoExpanded((value) => !value)}
                  className="flex w-full items-center gap-2 px-3 py-2.5 text-left"
                >
                  <AngleDownIcon
                    className={`size-4 shrink-0 text-gray-400 transition-transform duration-200 ${
                      gastoExpanded ? "-rotate-90" : ""
                    }`}
                  />
                  <span className="flex-1 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                    Gastos de esta reserva
                  </span>
                  <Badge color="primary" variant="light" size="sm">
                    Total {formatCOP(detail.gastos_total)}
                  </Badge>
                </button>
                <div
                  className={`grid transition-[grid-template-rows] duration-200 ease-out ${
                    gastoExpanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                  }`}
                  inert={!gastoExpanded}
                >
                  <div className="overflow-hidden">
                    <ul className="space-y-1.5 border-t border-gray-100 p-3 dark:border-gray-800">
                      {GASTO_CATEGORIA_OPTIONS.map((categoria) => {
                        const meta = GASTO_CATEGORIA_META[categoria];
                        const share = detail.gastos.find(
                          (g) => g.categoria === categoria,
                        );
                        return (
                          <li
                            key={categoria}
                            className="flex items-center gap-2.5"
                          >
                            <span
                              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm ${meta.chipClass}`}
                            >
                              {meta.icon}
                            </span>
                            <span className="min-w-0 flex-1 truncate text-theme-sm text-gray-600 dark:text-gray-300">
                              {categoria}
                            </span>
                            <span className="shrink-0 text-theme-sm font-medium text-gray-700 dark:text-gray-300">
                              {share ? formatCOP(share.monto) : "—"}
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                    <p className="px-3 pb-3 text-theme-xs text-gray-400 dark:text-gray-500">
                      Se editan desde el partido asociado.
                    </p>
                  </div>
                </div>
              </section>
            ) : null}

            <CollapsibleMetadata>
              <DetailRow label="Fuente" value={detail.source || "—"} />
              <DetailRow label="ID" value={detail.id} />
              <DetailRow label="Referencia" value={detail.reserva_reference} />
              <DetailRow label="Remitente" value={detail.sender || "—"} />
              <DetailRow
                label="Email recibido"
                value={formatDisplayDateTime(detail.fecha_email_recibido)}
              />
              <DetailRow
                label="Email message ID"
                value={detail.email_message_id || "—"}
              />
              <DetailRow label="User ID" value={detail.user_id || "—"} />
              <DetailRow
                label="Creado"
                value={formatDisplayDateTime(detail.created_at)}
              />
              <DetailRow
                label="Actualizado"
                value={formatDisplayDateTime(detail.updated_at)}
              />
            </CollapsibleMetadata>
          </div>
        ) : !refreshError ? (
          <p className="py-6 text-center text-theme-sm text-gray-500 dark:text-gray-400">
            Cargando detalle…
          </p>
        ) : null}

        <div className="mt-5 flex items-center justify-between gap-3">
          {!createMode && detail && !isEditing ? (
            <Button
              size="sm"
              variant="outline"
              onClick={handleDelete}
              disabled={deleting}
              className="!text-error-600 dark:!text-error-400"
            >
              {deleting ? "Eliminando…" : "Eliminar"}
            </Button>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-3">
            <Button
              size="sm"
              variant="outline"
              onClick={createMode || isEditing ? handleCancelEdit : onClose}
            >
              {createMode || isEditing ? "Cancelar" : "Cerrar"}
            </Button>
            {createMode || isEditing ? (
              <Button
                size="sm"
                onClick={handleSave}
                disabled={!isValid || saving}
              >
                {saving
                  ? "Guardando…"
                  : createMode
                    ? "Crear"
                    : "Guardar cambios"}
              </Button>
            ) : (
              <Button size="sm" onClick={handleEditClick} disabled={!detail}>
                Editar
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
