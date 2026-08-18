/** In-flight/completed requests keyed by lowercase currency code, so concurrent or repeated lookups within a session dedupe instead of re-fetching. */
const cache = new Map<string, Promise<number>>();

/** COP value of 1 unit of `moneda` (e.g. "USD"), via a free public daily-rate API. Throws on any failure — caller decides how to surface it. */
export async function fetchTrmToCop(moneda: string): Promise<number> {
  const key = moneda.toLowerCase();
  if (!cache.has(key)) {
    const request = (async () => {
      const res = await fetch(
        `https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/${key}.json`,
      );
      if (!res.ok) throw new Error(`TRM fetch failed for ${moneda}`);
      const data = (await res.json()) as Record<string, Record<string, number>>;
      const rate = data?.[key]?.cop;
      if (typeof rate !== "number") throw new Error(`TRM missing cop rate for ${moneda}`);
      return rate;
    })();
    request.catch(() => cache.delete(key)); // don't cache a failure
    cache.set(key, request);
  }
  return cache.get(key)!;
}
