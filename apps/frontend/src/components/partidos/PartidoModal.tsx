"use client";

import React, { useEffect, useState } from "react";
import Button from "@/components/ui/button/Button";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Select from "@/components/form/Select";
import { Modal } from "@/components/ui/modal";
import Badge from "@/components/ui/badge/Badge";
import { AngleDownIcon } from "@/icons";
import {
  formatCOP,
  formatIntegerCO,
  formatRawDateTime,
  rawDateOnly,
  sanitizeIntegerInput,
  toDatetimeLocal,
  toIsoUtc,
} from "@/components/reservations/reservationUtils";
import ProviderLogo from "@/components/reservations/ProviderLogo";
import { ApiError } from "@/lib/api";
import { deleteGasto, upsertGasto } from "@/lib/gastos";
import {
  createPartido,
  deletePartido,
  fetchPartidoById,
  updatePartido,
} from "@/lib/partidos";
import { fetchReservas } from "@/lib/reservas";
import { CAMPEONATO_OPTIONS, CIUDAD_OPTIONS, ESTADIO_OPTIONS, EQUIPOS_LOCALES } from "@/types/partido";
import type { Partido } from "@/types/partido";
import type { ReservationListItem } from "@/types/reservation";
import {
  GASTO_CATEGORIA_META,
  GASTO_CATEGORIA_OPTIONS,
  type GastoCategoria,
} from "@/types/gasto";
import ReservationDetailModal from "@/components/reservations/ReservationDetailModal";
import PartidoMatchedReservasModal from "./PartidoMatchedReservasModal";

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

const campeonatoOptions = CAMPEONATO_OPTIONS.map((value) => ({
  value,
  label: value,
}));
const estadioOptions = ESTADIO_OPTIONS.map((value) => ({ value, label: value }));
const ciudadOptions = CIUDAD_OPTIONS.map((value) => ({ value, label: value }));
const equipoLocalOptions = EQUIPOS_LOCALES.map((value) => ({ value, label: value }));

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
  const [selectedReserva, setSelectedReserva] = useState<ReservationListItem | null>(null);
  const [isReservaModalOpen, setIsReservaModalOpen] = useState(false);
  const [matchCandidates, setMatchCandidates] = useState<ReservationListItem[]>([]);
  const [isMatchModalOpen, setIsMatchModalOpen] = useState(false);
  const [gastoDrafts, setGastoDrafts] = useState<Record<string, string>>({});
  const [gastoFocus, setGastoFocus] = useState<Record<string, boolean>>({});
  const [gastoSaving, setGastoSaving] = useState<Record<string, boolean>>({});
  const [gastoError, setGastoError] = useState<string | null>(null);
  const [gastoExpanded, setGastoExpanded] = useState(false);

  /**
   * `partidoId` (prop) stays null through a create-with-matches flow — the
   * parent doesn't learn the new id until the modal closes. `detail.id`
   * fills that gap once creation succeeds, so the modal can keep rendering
   * as "existing partido" (title, delete button, linked reservas) without
   * the parent's involvement.
   */
  const effectiveId = partidoId ?? detail?.id ?? null;
  const displayAsExisting = effectiveId !== null;

  useEffect(() => {
    // Reset state when modal closes
    if (!isOpen) {
      setDetail(null);
      setForm(EMPTY_FORM);
      setError(null);
      setLoading(false);
      setSelectedReserva(null);
      setIsReservaModalOpen(false);
      setMatchCandidates([]);
      setIsMatchModalOpen(false);
      setGastoDrafts({});
      setGastoFocus({});
      setGastoSaving({});
      setGastoError(null);
      setGastoExpanded(false);
      return;
    }

    // Reset state when switching to create mode
    if (isCreate) {
      setDetail(null);
      setForm(EMPTY_FORM);
      setError(null);
      setLoading(false);
      return;
    }

    // Load detail when switching to edit mode
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

  /** Auto-select ciudad based on equipo_local name (stops once persisted). */
  useEffect(() => {
    if (displayAsExisting || !form.equipo_local) return;
    const equipo = form.equipo_local.toLowerCase();
    if (equipo.includes("junior")) {
      setForm((prev) => ({ ...prev, ciudad: "Barranquilla" }));
      setForm((prev) => ({ ...prev, estadio: "Romelio Martínez" }));
    } else if (equipo.includes("cartagena")) {
      setForm((prev) => ({ ...prev, ciudad: "Cartagena" }));
      setForm((prev) => ({ ...prev, estadio: "Jaime Morón" }));
    }
  }, [form.equipo_local, displayAsExisting]);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  /**
   * Seed the Gastos grid drafts once per loaded partido (keyed on id, not
   * the whole `detail` object) — re-running this on every `detail` update
   * would blindly overwrite every category's draft each time any single
   * category's save resolves, clobbering a sibling field the operator is
   * still mid-edit on. `handleGastoBlur` updates its own draft directly
   * once its save completes instead.
   */
  useEffect(() => {
    const next: Record<string, string> = {};
    for (const categoria of GASTO_CATEGORIA_OPTIONS) {
      const existing = detail?.gastos.find((g) => g.categoria === categoria);
      next[categoria] = existing ? existing.monto : "";
    }
    setGastoDrafts(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail?.id]);

  async function handleGastoBlur(categoria: GastoCategoria) {
    setGastoFocus((prev) => ({ ...prev, [categoria]: false }));
    if (!effectiveId) return;
    const raw = gastoDrafts[categoria]?.trim() ?? "";
    const existing = detail?.gastos.find((g) => g.categoria === categoria);

    // Nothing changed since the last committed value — skip the round-trip.
    if ((existing?.monto ?? "") === raw) return;

    setGastoError(null);
    setGastoSaving((prev) => ({ ...prev, [categoria]: true }));
    try {
      const updated =
        raw && Number(raw) > 0
          ? await upsertGasto(effectiveId, categoria, raw)
          : existing
            ? await deleteGasto(effectiveId, categoria)
            : null;
      if (updated) {
        setDetail(updated);
        const saved = updated.gastos.find((g) => g.categoria === categoria);
        setGastoDrafts((prev) => ({
          ...prev,
          [categoria]: saved ? saved.monto : "",
        }));
      }
      onSaved();
    } catch (err) {
      setGastoError(
        err instanceof ApiError ? err.message : "No se pudo guardar el gasto",
      );
    } finally {
      setGastoSaving((prev) => ({ ...prev, [categoria]: false }));
    }
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
      if (effectiveId) {
        await updatePartido(effectiveId, payload);
        onSaved();
        onClose();
        return;
      }

      const created = await createPartido(payload);

      let matches: ReservationListItem[] = [];
      try {
        const dayKey = rawDateOnly(created.fecha);
        const response = await fetchReservas({
          ciudad: created.ciudad,
          fecha_evento_from: dayKey,
          fecha_evento_to: dayKey,
          unassigned_only: true,
          limit: 100,
        });
        matches = response.items;
      } catch {
        // Auto-match is best-effort; the partido was already created successfully.
        matches = [];
      }

      onSaved();
      if (matches.length > 0) {
        setDetail(created);
        setMatchCandidates(matches);
        setIsMatchModalOpen(true);
      } else {
        onClose();
      }
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo guardar el partido",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!effectiveId) return;
    const confirmed = window.confirm(
      "¿Eliminar este partido? Se desvinculará de cualquier reserva asociada.",
    );
    if (!confirmed) return;

    setDeleting(true);
    setError(null);
    try {
      await deletePartido(effectiveId);
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
        {displayAsExisting ? "Detalle del partido" : "Agregar partido"}
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
          <div className="max-h-[min(65vh,34rem)] space-y-5 overflow-y-auto overflow-x-hidden pe-1">
          {/* Key ensures form fields reset when switching between create/edit modes */}
          <div key={`form-${displayAsExisting}`} className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2">
            <div>
              <Label>Equipo local</Label>
              <Select
                options={equipoLocalOptions}
                placeholder="Selecciona un equipo"
                defaultValue={form.equipo_local}
                onChange={(value) =>
                  update("equipo_local", value)
                }
              />
              {/* <Input
                type="text"
                value={form.equipo_local}
                onChange={(e) =>
                  update("equipo_local", e.target.value.slice(0, 25))
                }
                placeholder="Junior"
              /> */}
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
                key={`estadio-${form.estadio}`}
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
                key={`ciudad-${form.ciudad}`}
                options={ciudadOptions}
                placeholder="Selecciona una ciudad"
                defaultValue={form.ciudad}
                onChange={(value) => update("ciudad", value)}
              />
            </div>
          </div>

          {effectiveId ? (
            <div className="mt-5 rounded-xl border border-gray-100 dark:border-gray-800">
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
                  Gastos
                </span>
                <Badge color="primary" variant="light" size="sm">
                  Total {formatCOP(detail?.gastos_total ?? "0")}
                </Badge>
              </button>
              <div
                className={`grid transition-[grid-template-rows] duration-200 ease-out ${
                  gastoExpanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                }`}
                // Keeps the collapsed rows' inputs out of tab order and out
                // of find-in-page/AT reach, not just visually hidden.
                inert={!gastoExpanded}
              >
                <div className="overflow-hidden">
                  {gastoError ? (
                    <p
                      role="alert"
                      className="px-3 text-theme-xs text-error-600 dark:text-error-400"
                    >
                      {gastoError}
                    </p>
                  ) : null}
                  <ul className="divide-y divide-gray-100 border-t border-gray-100 dark:divide-gray-800 dark:border-gray-800">
                    {GASTO_CATEGORIA_OPTIONS.map((categoria) => {
                      const meta = GASTO_CATEGORIA_META[categoria];
                      const registered = detail?.gastos.find(
                        (g) => g.categoria === categoria,
                      );
                      const total = Number(detail?.gastos_total ?? "0");
                      const share =
                        registered && total > 0
                          ? (Number(registered.monto) / total) * 100
                          : 0;
                      const draft = gastoDrafts[categoria] ?? "";
                      const focused = gastoFocus[categoria] ?? false;

                      return (
                        <li
                          key={categoria}
                          className="relative flex items-center gap-2 px-3 py-1"
                        >
                          <span
                            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${meta.chipClass}`}
                          >
                            {meta.icon}
                          </span>
                          <span className="min-w-0 flex-1 truncate text-theme-sm text-gray-600 dark:text-gray-300">
                            {categoria}
                          </span>
                          <div className="relative w-[8.5rem] shrink-0">
                            <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center border-r border-gray-300 px-2 text-theme-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
                              COP
                            </span>
                            <input
                              type="text"
                              inputMode="numeric"
                              placeholder="0"
                              disabled={gastoSaving[categoria]}
                              value={
                                focused || !draft
                                  ? draft
                                  : formatIntegerCO(draft)
                              }
                              onFocus={() =>
                                setGastoFocus((prev) => ({
                                  ...prev,
                                  [categoria]: true,
                                }))
                              }
                              onChange={(e) =>
                                setGastoDrafts((prev) => ({
                                  ...prev,
                                  [categoria]: sanitizeIntegerInput(
                                    e.target.value,
                                  ),
                                }))
                              }
                              onBlur={() => handleGastoBlur(categoria)}
                              className="h-8 w-full rounded-lg border border-gray-300 bg-transparent py-1 pl-11 pr-2 text-right text-theme-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:outline-hidden focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:disabled:text-gray-500"
                            />
                          </div>
                          {/* Proportion of the total, drawn on the row divider itself — no extra height. */}
                          <span className="pointer-events-none absolute inset-x-0 bottom-0 h-0.5 overflow-hidden">
                            <span
                              className={`block h-full rounded-r-full transition-all duration-300 ${meta.barClass}`}
                              style={{ width: registered ? `${Math.max(share, 4)}%` : "0%" }}
                            />
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              </div>
            </div>
          ) : null}

          {detail && detail.reservas.length > 0 ? (
            <div className="mt-5">
              <div className="mb-3 flex items-center justify-between">
                <h5 className="text-theme-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                  Reservas vinculadas ({detail.reservas.length})
                </h5>
                <div className="text-right">
                  <p className="text-theme-xs font-medium text-gray-500 dark:text-gray-400">
                    Total participantes
                  </p>
                  <p className="text-lg font-semibold text-gray-800 dark:text-white/90">
                    {detail.reservas.reduce((sum, r) => sum + r.participants, 0)}
                  </p>
                </div>
              </div>
              <ul className="space-y-1.5 rounded-xl border border-gray-100 p-3 dark:border-gray-800">
                {detail.reservas.map((reserva) => (
                  <li
                    key={reserva.id}
                    className="flex items-center justify-between gap-3"
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedReserva(reserva);
                        setIsReservaModalOpen(true);
                      }}
                      className="group flex min-w-0 flex-1 flex-col text-left transition-colors hover:text-orange-600 dark:hover:text-orange-400"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <ProviderLogo
                          provider={reserva.booking_provider}
                          size={20}
                        />
                        <span className="min-w-0 truncate text-theme-sm font-medium text-gray-700 group-hover:text-orange-600 dark:text-gray-300 dark:group-hover:text-orange-400">
                          {reserva.customer_name}
                        </span>
                      </div>
                      <span className="mt-0.5 ml-6 text-theme-xs text-gray-500 dark:text-gray-400">
                        {formatRawDateTime(reserva.fecha_evento)}
                      </span>
                    </button>
                    <span className="shrink-0 text-theme-sm font-medium text-gray-700 dark:text-gray-300">
                      {reserva.participants} pax
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          </div>

          <div className="mt-6 flex items-center justify-between gap-3">
            {displayAsExisting ? (
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
                {saving
                  ? "Guardando…"
                  : displayAsExisting
                    ? "Guardar cambios"
                    : "Crear"}
              </Button>
            </div>
          </div>
        </>
      )}

      <PartidoMatchedReservasModal
        isOpen={isMatchModalOpen}
        partidoId={detail?.id ?? null}
        ciudad={detail?.ciudad ?? form.ciudad}
        fecha={detail?.fecha ?? toIsoUtc(form.fecha)}
        candidates={matchCandidates}
        onClose={() => setIsMatchModalOpen(false)}
        onAssigned={(assigned) => {
          setDetail((prev) =>
            prev ? { ...prev, reservas: [...prev.reservas, ...assigned] } : prev,
          );
          onSaved();
        }}
      />

      <ReservationDetailModal
        reservation={selectedReserva}
        isOpen={isReservaModalOpen}
        onClose={() => {
          setIsReservaModalOpen(false);
          setSelectedReserva(null);
        }}
      />
    </Modal>
  );
}
