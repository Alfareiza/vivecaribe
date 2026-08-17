"use client";

import React, { useEffect, useState } from "react";
import Button from "@/components/ui/button/Button";
import { Modal } from "@/components/ui/modal";
import ProviderLogo from "@/components/reservations/ProviderLogo";
import { formatRawDateTime } from "@/components/reservations/reservationUtils";
import { updateReserva } from "@/lib/reservas";
import type { ReservationListItem } from "@/types/reservation";

type PartidoMatchedReservasModalProps = {
  isOpen: boolean;
  partidoId: string | null;
  ciudad: string;
  fecha: string;
  candidates: ReservationListItem[];
  onClose: () => void;
  /** Called with the reservas that were successfully assigned (may be partial on failure). */
  onAssigned: (assigned: ReservationListItem[]) => void;
};

/**
 * Confirms bulk-assignment of reservas found for a just-created partido
 * (same ciudad + same calendar day, previously unassigned).
 */
export default function PartidoMatchedReservasModal({
  isOpen,
  partidoId,
  ciudad,
  fecha,
  candidates,
  onClose,
  onAssigned,
}: PartidoMatchedReservasModalProps) {
  const [pending, setPending] = useState<ReservationListItem[]>([]);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setPending(candidates);
    setChecked(Object.fromEntries(candidates.map((r) => [r.id, true])));
    setError(null);
    setSaving(false);
    // Only reset when the modal (re)opens with a fresh candidate set.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  function toggle(id: string) {
    setChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  async function handleConfirm() {
    if (!partidoId) return;
    const targetIds = pending.filter((r) => checked[r.id]).map((r) => r.id);
    if (targetIds.length === 0) {
      onClose();
      return;
    }

    setSaving(true);
    setError(null);

    const results = await Promise.allSettled(
      targetIds.map((id) => updateReserva(id, { partido_id: partidoId })),
    );

    const succeededIds = new Set<string>();
    let failedCount = 0;
    results.forEach((result, index) => {
      if (result.status === "fulfilled") {
        succeededIds.add(targetIds[index]);
      } else {
        failedCount += 1;
      }
    });

    const succeeded = pending.filter((r) => succeededIds.has(r.id));
    if (succeeded.length > 0) {
      onAssigned(succeeded);
    }

    if (failedCount > 0) {
      setPending((prev) => prev.filter((r) => !succeededIds.has(r.id)));
      setChecked((prev) => {
        const next = { ...prev };
        succeededIds.forEach((id) => delete next[id]);
        return next;
      });
      setError(
        `No se pudieron asignar ${failedCount} reserva${failedCount === 1 ? "" : "s"}. Intenta de nuevo.`,
      );
      setSaving(false);
      return;
    }

    setSaving(false);
    onClose();
  }

  const selectedCount = pending.filter((r) => checked[r.id]).length;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      className="m-4 max-w-[520px] p-5 sm:p-6"
    >
      <h4 className="mb-1 text-title-sm font-semibold text-gray-800 dark:text-white/90">
        Reservas encontradas
      </h4>
      <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
        {pending.length} reserva{pending.length === 1 ? "" : "s"} sin partido
        asignado en{" "}
        <span className="font-medium text-gray-700 dark:text-gray-300">
          {ciudad}
        </span>{" "}
        para el{" "}
        <span className="font-medium text-gray-700 dark:text-gray-300">
          {formatRawDateTime(fecha)}
        </span>
        . ¿Deseas asociarlas a este partido?
      </p>

      {error ? (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-error-200 bg-error-50 px-3 py-2 text-theme-sm text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
        >
          {error}
        </p>
      ) : null}

      <ul className="max-h-[min(50vh,24rem)] space-y-1.5 overflow-y-auto rounded-xl border border-gray-100 p-3 dark:border-gray-800">
        {pending.map((reserva) => (
          <li key={reserva.id}>
            <label className="flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2 hover:bg-gray-50 dark:hover:bg-white/[0.02]">
              <input
                type="checkbox"
                checked={checked[reserva.id] ?? false}
                onChange={() => toggle(reserva.id)}
                disabled={saving}
                className="size-4 shrink-0 rounded border-gray-300 text-brand-500 focus:ring-brand-500/20 dark:border-gray-700"
              />
              <ProviderLogo provider={reserva.booking_provider} size={20} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-theme-sm font-medium text-gray-700 dark:text-gray-300">
                  {reserva.customer_name}
                </p>
                <p className="text-theme-xs text-gray-500 dark:text-gray-400">
                  {formatRawDateTime(reserva.fecha_evento)}
                </p>
              </div>
              <span className="shrink-0 text-theme-xs font-medium text-gray-500 dark:text-gray-400">
                {reserva.participants} pax
              </span>
            </label>
          </li>
        ))}
      </ul>

      <div className="mt-5 flex items-center justify-end gap-3">
        <Button size="sm" variant="outline" onClick={onClose} disabled={saving}>
          No
        </Button>
        <Button
          size="sm"
          onClick={() => void handleConfirm()}
          disabled={saving || selectedCount === 0}
        >
          {saving ? "Asignando…" : "Aceptar"}
        </Button>
      </div>
    </Modal>
  );
}
