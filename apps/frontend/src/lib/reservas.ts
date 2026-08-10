import { apiJson } from "@/lib/api";
import type { Reservation } from "@/types/reservation";

export type ReservaListResponse = {
  total: number;
  items: Reservation[];
};

const PAGE_LIMIT = 100;

export async function fetchAllReservas(): Promise<Reservation[]> {
  const all: Reservation[] = [];
  let skip = 0;
  let total = Infinity;

  while (skip < total) {
    const page = await apiJson<ReservaListResponse>(
      `/reservas?skip=${skip}&limit=${PAGE_LIMIT}`,
    );
    total = page.total;
    all.push(...page.items);
    if (page.items.length === 0) break;
    skip += page.items.length;
  }

  return all;
}
