"use client";

import React, { useEffect, useState } from "react";
import Button from "@/components/ui/button/Button";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Select from "@/components/form/Select";
import { Modal } from "@/components/ui/modal";
import { formatRawDateTime } from "@/components/reservations/reservationUtils";
import { ApiError } from "@/lib/api";
import {
  createPartido,
  deletePartido,
  fetchPartidoById,
  updatePartido,
} from "@/lib/partidos";
import { CAMPEONATO_OPTIONS, CIUDAD_OPTIONS, ESTADIO_OPTIONS } from "@/types/partido";
import type { Partido } from "@/types/partido";

type PartidoModalProps = {
  /** ``null`` opens the modal in create mode. */
  partidoId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
};

type FormState = {
  equipo_local: string;
  equipo_visitante: string;
  nombre_campeonato: string;
  estadio: string;
  fecha: string;
  ciudad: string;
};

const EMPTY_FORM: FormState = {
  equipo_local: "",
  equipo_visitante: "",
  nombre_campeonato: "",
  estadio: "",
  fecha: "",
  ciudad: "",
};

/** "2026-09-01T20:00:00Z" -> "2026-09-01T20:00" for a datetime-local input. */
function toDatetimeLocal(iso: string): string {
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})/.exec(iso);
  return match ? match[1] : "";
}

/** "2026-09-01T20:00" -> "2026-09-01T20:00:00Z" for the API payload. */
function toIsoUtc(datetimeLocal: string): string {
  return `${datetimeLocal}:00Z`;
}

const campeonatoOptions = CAMPEONATO_OPTIONS.map((value) => ({
  value,
  label: value,
}));
const estadioOptions = ESTADIO_OPTIONS.map((value) => ({ value, label: value }));
const ciudadOptions = CIUDAD_OPTIONS.map((value) => ({ value, label: value }));

export default function PartidoModal({
  partidoId,
  isOpen,
  onClose,
  onSaved,
  onDeleted,
}: PartidoModalProps) {
  const isCreate = partidoId === null;
  const [detail, setDetail] = useState<Partido | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    if (isCreate) {
      setDetail(null);
      setForm(EMPTY_FORM);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const fresh = await fetchPartidoById(partidoId);
        if (cancelled) return;
        setDetail(fresh);
        setForm({
          equipo_local: fresh.equipo_local,
          equipo_visitante: fresh.equipo_visitante,
          nombre_campeonato: fresh.nombre_campeonato,
          estadio: fresh.estadio,
          fecha: toDatetimeLocal(fresh.fecha),
          ciudad: fresh.ciudad,
        });
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "No se pudo cargar el partido",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isOpen, isCreate, partidoId]);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const isValid =
    form.equipo_local.trim().length > 0 &&
    form.equipo_visitante.trim().length > 0 &&
    form.nombre_campeonato.length > 0 &&
    form.estadio.length > 0 &&
    form.fecha.length > 0 &&
    form.ciudad.trim().length > 0;

  async function handleSave() {
    if (!isValid) return;
    setSaving(true);
    setError(null);
    const payload = {
      equipo_local: form.equipo_local.trim(),
      equipo_visitante: form.equipo_visitante.trim(),
      nombre_campeonato: form.nombre_campeonato,
      estadio: form.estadio,
      fecha: toIsoUtc(form.fecha),
      ciudad: form.ciudad.trim(),
    };
    try {
      if (isCreate) {
        await createPartido(payload);
      } else if (partidoId) {
        await updatePartido(partidoId, payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo guardar el partido",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!partidoId) return;
    const confirmed = window.confirm(
      "¿Eliminar este partido? Se desvinculará de cualquier reserva asociada.",
    );
    if (!confirmed) return;

    setDeleting(true);
    setError(null);
    try {
      await deletePartido(partidoId);
      onDeleted();
      onClose();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo eliminar el partido",
      );
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      className="m-4 max-w-[584px] p-5 sm:p-6"
    >
      <h4 className="mb-5 text-title-sm font-semibold text-gray-800 dark:text-white/90">
        {isCreate ? "Agregar partido" : "Detalle del partido"}
      </h4>

      {error ? (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-error-200 bg-error-50 px-3 py-2 text-theme-sm text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
        >
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="py-6 text-center text-theme-sm text-gray-500 dark:text-gray-400">
          Cargando…
        </p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2">
            <div>
              <Label>Equipo local</Label>
              <Input
                type="text"
                value={form.equipo_local}
                onChange={(e) =>
                  update("equipo_local", e.target.value.slice(0, 25))
                }
                placeholder="Junior"
              />
            </div>
            <div>
              <Label>Equipo visitante</Label>
              <Input
                type="text"
                value={form.equipo_visitante}
                onChange={(e) =>
                  update("equipo_visitante", e.target.value.slice(0, 25))
                }
                placeholder="Millonarios"
              />
            </div>
            <div>
              <Label>Campeonato</Label>
              <Select
                options={campeonatoOptions}
                placeholder="Selecciona un campeonato"
                defaultValue={form.nombre_campeonato}
                onChange={(value) => update("nombre_campeonato", value)}
              />
            </div>
            <div>
              <Label>Estadio</Label>
              <Select
                options={estadioOptions}
                placeholder="Selecciona un estadio"
                defaultValue={form.estadio}
                onChange={(value) => update("estadio", value)}
              />
            </div>
            <div>
              <Label>Fecha</Label>
              <Input
                type="datetime-local"
                value={form.fecha}
                onChange={(e) => update("fecha", e.target.value)}
              />
            </div>
            <div>
              <Label>Ciudad</Label>
              <Select
                options={ciudadOptions}
                placeholder="Selecciona una ciudad"
                defaultValue={form.ciudad}
                onChange={(value) => update("ciudad", value)}
              />
            </div>
          </div>

          {detail && detail.reservas.length > 0 ? (
            <div className="mt-5">
              <h5 className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                Reservas vinculadas ({detail.reservas.length})
              </h5>
              <ul className="space-y-1.5 rounded-xl border border-gray-100 p-3 dark:border-gray-800">
                {detail.reservas.map((reserva) => (
                  <li
                    key={reserva.id}
                    className="flex items-center justify-between gap-3 text-theme-sm"
                  >
                    <span className="min-w-0 truncate text-gray-700 dark:text-gray-300">
                      {reserva.customer_name}
                    </span>
                    <span className="shrink-0 text-theme-xs text-gray-400 dark:text-gray-500">
                      {formatRawDateTime(reserva.fecha_evento)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="mt-6 flex items-center justify-between gap-3">
            {!isCreate ? (
              <Button
                size="sm"
                variant="outline"
                onClick={handleDelete}
                disabled={deleting || saving}
                className="!text-error-600 dark:!text-error-400"
              >
                {deleting ? "Eliminando…" : "Eliminar"}
              </Button>
            ) : (
              <span />
            )}
            <div className="flex items-center gap-3">
              <Button size="sm" variant="outline" onClick={onClose}>
                Cerrar
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={!isValid || saving || deleting}
              >
                {saving ? "Guardando…" : isCreate ? "Crear" : "Guardar cambios"}
              </Button>
            </div>
          </div>
        </>
      )}
    </Modal>
  );
}
