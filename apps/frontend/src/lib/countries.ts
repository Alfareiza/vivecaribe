import countries from "world-countries";

/** All country common names, sorted alphabetically, for the país searchable input. */
export const COUNTRY_NAMES: string[] = countries
  .map((country) => country.name.common)
  .sort((a, b) => a.localeCompare(b));
