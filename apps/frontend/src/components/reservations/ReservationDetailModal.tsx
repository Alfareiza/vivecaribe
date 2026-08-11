"use client";

import React, { useEffect, useState } from "react";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import { Modal } from "@/components/ui/modal";
import { AngleDownIcon, CalendarIcon, WhatsappIcon } from "@/icons";
import { ApiError } from "@/lib/api";
import { fetchReservaById } from "@/lib/reservas";
import type { Reservation, ReservationListItem } from "@/types/reservation";
import ProviderLogo from "./ProviderLogo";
import ShareMenu from "./ShareMenu";
import { EsHoyStatusDot } from "./StatusDot";
import {
  buildGoogleCalendarUrl,
  buildWhatsAppShareUrl,
} from "./reservationShare";
import {
  formatDisplayDateTime,
  formatPrice,
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
          <div className="max-h-[min(55vh,28rem)] space-y-4 overflow-y-auto pe-1">
            <div className="grid gap-4 sm:grid-cols-2 sm:gap-x-6">
              <DetailSection title="Cliente">
                <DetailRow label="Nombre" value={detail.customer_name} />
                <DetailRow label="Personas" value={detail.participants} />
                <DetailRow label="Teléfono" value={detail.phone || "—"} />
                <DetailRow
                  label="País"
                  value={detail.pais_del_visitante || "—"}
                />
              </DetailSection>

              <DetailSection title="Comercial">
                <DetailRow
                  label="Precio"
                  value={formatPrice(detail.price, detail.moneda)}
                />
                <DetailRow
                  label="Ingreso"
                  value={formatPrice(detail.income, detail.moneda)}
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
              </DetailSection>
            </div>

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
