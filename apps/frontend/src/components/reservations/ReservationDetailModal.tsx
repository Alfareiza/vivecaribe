"use client";

import React, { useEffect, useState } from "react";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import TextArea from "@/components/form/input/TextArea";
import { Modal } from "@/components/ui/modal";
import { AngleDownIcon, CalendarIcon, WhatsappIcon } from "@/icons";
import { ApiError } from "@/lib/api";
import { fetchReservaById, updateReserva } from "@/lib/reservas";
import type { Reservation, ReservationListItem } from "@/types/reservation";
import ProviderLogo from "./ProviderLogo";
import ShareMenu from "./ShareMenu";
import { EsHoyStatusDot } from "./StatusDot";
import {
  buildGoogleCalendarUrl,
  buildWhatsAppShareUrl,
} from "./reservationShare";
import {
  MEETING_POINT_LABELS,
  TIPO_TOUR_LABELS,
  TRM_COP_PLACEHOLDER,
  estimateIncomeCOP,
  formatCOP,
  formatDisplayDateTime,
  formatPrice,
  truncateText,
} from "./reservationUtils";

type ReservationDetailModalProps = {
  reservation: ReservationListItem | null;
  isOpen: boolean;
  onClose: () => void;
};

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

function DetailSection({
  title,
  children,
  className = "",
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
        {title}
      </h5>
      <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-1.5">
        {children}
      </dl>
    </section>
  );
}

/** Micro-header for a subgroup within a DetailSection (e.g. Financiero / Operativo). */
function SubGroupLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="col-span-2 mt-1 text-theme-xs font-medium text-gray-400 first:mt-0 dark:text-gray-500">
      {children}
    </p>
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

/** 0-100% fill bar; green when >= 0, a minimal red sliver when negative. */
function PercentageBar({ value }: { value: string | null }) {
  if (value === null) return <span>—</span>;
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return <span>—</span>;

  const isNegative = numeric < 0;
  const width = isNegative ? 4 : Math.max(0, Math.min(100, numeric));

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-gray-100 dark:bg-white/10">
        <div
          className={`h-full rounded-full ${isNegative ? "bg-error-500" : "bg-success-500"}`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span
        className={`text-sm font-medium tabular-nums ${isNegative ? "text-error-600 dark:text-error-400" : "text-gray-800 dark:text-white/90"}`}
      >
        {numeric.toFixed(2)}%
      </span>
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

export default function ReservationDetailModal({
  reservation,
  isOpen,
  onClose,
}: ReservationDetailModalProps) {
  const [detail, setDetail] = useState<Reservation | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [isSavingMenores, setIsSavingMenores] = useState(false);
  const [menoresError, setMenoresError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !reservation) {
      setDetail(null);
      return;
    }

    setDetail(null);
    setRefreshError(null);

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
  }, [isOpen, reservation]);

  if (!reservation) return null;

  const preview = detail ?? reservation;
  const esHoy = detail?.es_hoy ?? reservation.es_hoy;
  const titleRef = detail?.reserva_reference;
  const whatsappUrl = detail ? buildWhatsAppShareUrl(detail) : null;
  const calendarUrl = detail ? buildGoogleCalendarUrl(detail) : null;
  const isFootballTour = detail?.tipo_tour === "football tour";
  const incomeEstimadoCOP = detail ? estimateIncomeCOP(detail.income) : null;

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

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      className="m-4 max-w-[560px] overflow-visible p-5 sm:p-6"
    >
      <div className="pr-8">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <ProviderLogo provider={preview.booking_provider} size={40} />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2.5">
                <h4 className="text-title-sm font-semibold text-gray-800 dark:text-white/90">
                  {titleRef ? `Reserva ${titleRef}` : preview.nombre_experiencia}
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
                id: "whatsapp",
                label: "WhatsApp",
                icon: <WhatsappIcon />,
                href: whatsappUrl,
                disabled: !whatsappUrl,
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

        {refreshError ? (
          <p
            role="alert"
            className="mb-3 rounded-lg border border-error-200 bg-error-50 px-3 py-2 text-theme-sm text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
          >
            {refreshError}
          </p>
        ) : null}

        <div className="mb-4 rounded-xl border border-gray-100 bg-gray-50/70 px-3.5 py-3 dark:border-gray-800 dark:bg-white/[0.02]">
          <p className="text-sm font-semibold text-gray-800 dark:text-white/90">
            {preview.nombre_experiencia}
          </p>
          <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
            {[
              preview.ciudad_experiencia,
              formatDisplayDateTime(preview.fecha_evento),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>

        {detail ? (
          <div className="max-h-[min(65vh,34rem)] space-y-4 overflow-y-auto pe-1">
            <DetailSection title="Cliente">
              <DetailRow label="Nombre" value={detail.customer_name} />
              <DetailRow label="Personas" value={detail.participants} />
              <DetailRow label="Teléfono" value={detail.phone || "—"} />
              <DetailRow
                label="País"
                value={detail.pais_del_visitante || "—"}
              />
            </DetailSection>

            <section>
              <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                Resumen
              </h5>
              <div className="grid gap-x-6 gap-y-4 rounded-xl border border-gray-100 p-3.5 sm:grid-cols-2 dark:border-gray-800">
                <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-1.5">
                  <SubGroupLabel>Financiero</SubGroupLabel>
                  <DetailRow
                    label="Ingreso"
                    value={
                      <InfoTooltip
                        label={`El cliente pagó ${formatPrice(detail.price, detail.moneda)} en total`}
                      >
                        {formatPrice(detail.income, detail.moneda)}
                      </InfoTooltip>
                    }
                  />
                  <DetailRow
                    label="Ingreso est."
                    value={
                      <span>
                        {formatCOP(incomeEstimadoCOP)}
                        <span className="ml-1 text-theme-xs text-gray-400 dark:text-gray-500">
                          (TRM {TRM_COP_PLACEHOLDER})
                        </span>
                      </span>
                    }
                  />
                  <DetailRow label="Costos" value={formatCOP(detail.costos)} />
                  <DetailRow label="Profit" value={formatCOP(detail.profit)} />
                  <DetailRow
                    label="% Profit"
                    value={<PercentageBar value={detail.percentage_profit} />}
                  />
                  <DetailRow
                    label="Pago estimado"
                    value={formatDisplayDateTime(detail.paid_at)}
                  />
                </dl>

                <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-1.5">
                  <SubGroupLabel>Operativo</SubGroupLabel>
                  <DetailRow
                    label="Menores de edad"
                    value={
                      <div className="flex items-center gap-2 rounded-lg border border-brand-100 bg-brand-50/40 px-2 py-1 dark:border-brand-500/20 dark:bg-brand-500/5">
                        <ControlledSwitch
                          checked={detail.menores_de_edad}
                          disabled={isSavingMenores}
                          onChange={handleMenoresDeEdadChange}
                        />
                        <span className="text-theme-xs text-gray-400 dark:text-gray-500">
                          {isSavingMenores ? "Guardando…" : "Se guarda al instante"}
                        </span>
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
                    label="Lugar de recogida"
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
                </dl>
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

            <CollapsibleMetadata>
              <DetailRow label="Fuente" value={detail.source} />
              <DetailRow label="ID" value={detail.id} />
              <DetailRow label="Referencia" value={detail.reserva_reference} />
              <DetailRow label="Remitente" value={detail.sender} />
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

        <div className="mt-5 flex items-center justify-end gap-3">
          <Button size="sm" variant="outline" onClick={onClose}>
            Cerrar
          </Button>
          {/* Enabled in #40 once PATCH form + auth exist */}
          <Button size="sm" disabled>
            Editar
          </Button>
        </div>
      </div>
    </Modal>
  );
}
