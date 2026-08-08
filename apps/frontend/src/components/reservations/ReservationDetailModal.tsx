"use client";

import React from "react";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import { Modal } from "@/components/ui/modal";
import type { Reservation } from "@/types/reservation";
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
    <div className="grid grid-cols-1 gap-1 sm:grid-cols-3 sm:gap-3">
      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
        {label}
      </dt>
      <dd className="text-sm text-gray-800 sm:col-span-2 dark:text-white/90 break-words">
        {value}
      </dd>
    </div>
  );
}

export default function ReservationDetailModal({
  reservation,
  isOpen,
  onClose,
}: ReservationDetailModalProps) {
  if (!reservation) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      className="max-w-[700px] m-4 p-5 lg:p-8"
    >
      <div className="pr-8">
        <h4 className="mb-1 text-title-sm font-semibold text-gray-800 dark:text-white/90">
          Reserva {reservation.reserva_reference}
        </h4>
        <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
          {reservation.subject}
        </p>

        <dl className="space-y-3 max-h-[60vh] overflow-y-auto pe-1">
          <DetailRow label="ID" value={reservation.id} />
          <DetailRow label="Referencia" value={reservation.reserva_reference} />
          <DetailRow label="Fuente (canal)" value={reservation.source} />
          <DetailRow
            label="Proveedor"
            value={reservation.booking_provider}
          />
          <DetailRow
            label="Estado"
            value={
              <Badge size="sm" color={getEstadoBadgeColor(reservation.estado)}>
                {reservation.estado}
              </Badge>
            }
          />
          <DetailRow label="Remitente" value={reservation.sender} />
          <DetailRow
            label="Email recibido"
            value={
              <>
                <span>{formatDisplayDateTime(reservation.fecha_email_recibido)}</span>
                <span className="mt-0.5 block text-theme-xs text-gray-400">
                  {reservation.fecha_email_recibido}
                </span>
              </>
            }
          />
          <DetailRow
            label="Experiencia"
            value={reservation.nombre_experiencia}
          />
          <DetailRow label="Ciudad" value={reservation.ciudad_experiencia} />
          <DetailRow
            label="Fecha evento"
            value={
              <>
                <span>{formatDisplayDateTime(reservation.fecha_evento)}</span>
                {reservation.fecha_evento && (
                  <span className="mt-0.5 block text-theme-xs text-gray-400">
                    {reservation.fecha_evento}
                  </span>
                )}
              </>
            }
          />
          <DetailRow label="Participantes" value={reservation.participants} />
          <DetailRow label="Cliente" value={reservation.customer_name} />
          <DetailRow label="Teléfono" value={reservation.phone || "—"} />
          <DetailRow
            label="País visitante"
            value={reservation.pais_del_visitante || "—"}
          />
          <DetailRow
            label="Precio"
            value={formatPrice(reservation.price, reservation.moneda)}
          />
          <DetailRow
            label="Ingreso"
            value={formatPrice(reservation.income, reservation.moneda)}
          />
          <DetailRow
            label="Notificado WhatsApp"
            value={
              <Badge
                size="sm"
                color={reservation.notificado_whatsapp ? "success" : "light"}
              >
                {reservation.notificado_whatsapp ? "Sí" : "No"}
              </Badge>
            }
          />
          <DetailRow
            label="Email message ID"
            value={reservation.email_message_id || "—"}
          />
          <DetailRow label="User ID" value={reservation.user_id || "—"} />
          <DetailRow
            label="Creado"
            value={formatDisplayDateTime(reservation.created_at)}
          />
          <DetailRow
            label="Actualizado"
            value={formatDisplayDateTime(reservation.updated_at)}
          />
        </dl>

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
