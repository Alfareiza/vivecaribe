"use client";

import React, { useEffect, useState } from "react";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import { Modal } from "@/components/ui/modal";
import { CalendarIcon, WhatsappIcon } from "@/icons";
import { ApiError } from "@/lib/api";
import { fetchReservaById } from "@/lib/reservas";
import type { Reservation } from "@/types/reservation";
import ShareMenu from "./ShareMenu";
import {
  buildGoogleCalendarUrl,
  buildWhatsAppShareUrl,
} from "./reservationShare";
import {
  formatDisplayDateTime,
  formatPrice,
  getEstadoBadgeColor,
} from "./reservationUtils";

type ReservationDetailModalProps = {
  reservation: Reservation | null;
  isOpen: boolean;
  onClose: () => void;
};

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-0.5 sm:grid-cols-3 sm:gap-3 sm:items-baseline">
      <dt className="text-theme-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
        {label}
      </dt>
      <dd className="text-sm text-gray-800 sm:col-span-2 dark:text-white/90 break-words">
        {value}
      </dd>
    </div>
  );
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <h5 className="text-theme-sm font-semibold text-gray-800 dark:text-white/90">
        {title}
      </h5>
      <dl className="space-y-3 border-t border-gray-100 pt-3 dark:border-gray-800">
        {children}
      </dl>
    </section>
  );
}

export default function ReservationDetailModal({
  reservation,
  isOpen,
  onClose,
}: ReservationDetailModalProps) {
  const [detail, setDetail] = useState<Reservation | null>(reservation);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !reservation) {
      return;
    }

    setDetail(reservation);
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

  if (!reservation || !detail) return null;

  const whatsappUrl = buildWhatsAppShareUrl(detail);
  const calendarUrl = buildGoogleCalendarUrl(detail);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      className="max-w-[700px] m-4 p-5 lg:p-8"
    >
      <div className="pr-8">
        <div className="mb-1 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h4 className="text-title-sm font-semibold text-gray-800 dark:text-white/90">
              Reserva {detail.reserva_reference}
            </h4>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
              {detail.subject}
            </p>
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

        <div className="mb-5 flex flex-wrap items-center gap-2">
          <Badge size="sm" color={getEstadoBadgeColor(detail.estado)}>
            {detail.estado}
          </Badge>
          <span className="text-theme-xs text-gray-400 dark:text-gray-500">
            {detail.booking_provider} · {detail.source}
          </span>
          {isRefreshing ? (
            <span
              role="status"
              aria-live="polite"
              className="text-theme-xs text-gray-400 dark:text-gray-500"
            >
              Actualizando…
            </span>
          ) : null}
        </div>

        {refreshError ? (
          <p
            role="alert"
            className="mb-4 rounded-lg border border-error-200 bg-error-50 px-3 py-2 text-theme-sm text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
          >
            {refreshError}
          </p>
        ) : null}

        <div className="max-h-[55vh] space-y-6 overflow-y-auto pe-1">
          <DetailSection title="Evento">
            <DetailRow label="Experiencia" value={detail.nombre_experiencia} />
            <DetailRow label="Ciudad" value={detail.ciudad_experiencia} />
            <DetailRow
              label="Fecha evento"
              value={
                <>
                  <span>{formatDisplayDateTime(detail.fecha_evento)}</span>
                  {detail.fecha_evento ? (
                    <span className="mt-0.5 block text-theme-xs text-gray-400">
                      {detail.fecha_evento}
                    </span>
                  ) : null}
                </>
              }
            />
            <DetailRow label="Participantes" value={detail.participants} />
          </DetailSection>

          <DetailSection title="Cliente">
            <DetailRow label="Nombre" value={detail.customer_name} />
            <DetailRow label="Teléfono" value={detail.phone || "—"} />
            <DetailRow
              label="País visitante"
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
              label="Notificado WhatsApp"
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

          <DetailSection title="Origen">
            <DetailRow label="ID" value={detail.id} />
            <DetailRow label="Referencia" value={detail.reserva_reference} />
            <DetailRow label="Remitente" value={detail.sender} />
            <DetailRow
              label="Email recibido"
              value={
                <>
                  <span>
                    {formatDisplayDateTime(detail.fecha_email_recibido)}
                  </span>
                  <span className="mt-0.5 block text-theme-xs text-gray-400">
                    {detail.fecha_email_recibido}
                  </span>
                </>
              }
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
          </DetailSection>
        </div>

        <div className="mt-8 flex items-center justify-end gap-3">
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
