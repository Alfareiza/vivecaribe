"use client";

import React, { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import InlineLoading from "@/components/ui/loading/InlineLoading";
import { PlusIcon } from "@/icons";
import { useModal } from "@/hooks/useModal";
import { fetchPartidos } from "@/lib/partidos";
import type { PartidoListItem } from "@/types/partido";
import PartidoCard from "./PartidoCard";
import PartidoModal from "./PartidoModal";

export default function PartidosGrid() {
  const { isOpen, openModal, closeModal } = useModal();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [items, setItems] = useState<PartidoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchPartidos({
        limit: 100,
        q: search.trim() || undefined,
      });
      // Sort by fecha descending (newest first)
      const sorted = [...response.items].sort((a, b) => {
        const dateA = new Date(a.fecha).getTime();
        const dateB = new Date(b.fecha).getTime();
        return dateB - dateA;
      });
      setItems(sorted);
      setTotal(response.total);
    } catch {
      setItems([]);
      setTotal(0);
      setError("No se pudieron cargar los partidos");
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    void load();
  }, [load]);

  function handleOpenCreate() {
    setSelectedId(null);
    openModal();
  }

  function handleOpenDetail(partido: PartidoListItem) {
    setSelectedId(partido.id);
    openModal();
  }

  function handleCloseModal() {
    closeModal();
    setSelectedId(null);
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white px-4 pb-5 pt-4 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            Partidos
          </h3>
          <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
            {total} resultado{total === 1 ? "" : "s"}
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="w-full sm:w-64">
            <Input
              type="text"
              placeholder="Buscar equipo o ciudad"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button size="sm" startIcon={<PlusIcon />} onClick={handleOpenCreate}>
            Agregar
          </Button>
        </div>
      </div>

      {error ? (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-error-200 bg-error-50 px-3 py-2 text-theme-sm text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
        >
          {error}
        </p>
      ) : null}

      {loading ? (
        <InlineLoading label="Cargando partidos" />
      ) : items.length === 0 ? (
        <p className="py-10 text-center text-theme-sm text-gray-500 dark:text-gray-400">
          No hay partidos registrados.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((partido) => (
            <PartidoCard
              key={partido.id}
              partido={partido}
              onClick={() => handleOpenDetail(partido)}
            />
          ))}
        </div>
      )}

      <PartidoModal
        partidoId={selectedId}
        isOpen={isOpen}
        onClose={handleCloseModal}
        onSaved={() => void load()}
        onDeleted={() => void load()}
      />
    </div>
  );
}
