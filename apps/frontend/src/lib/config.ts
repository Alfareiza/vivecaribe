export function getApiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (!base) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured");
  }
  return base;
}

export function getLoginRedirectUrl(): string {
  const path = process.env.NEXT_PUBLIC_LOGIN_REDIRECT_URL?.trim();
  if (path && path.startsWith("/") && !path.startsWith("//")) {
    return path;
  }
  return "/reservas";
}

/** Allow only same-origin relative paths (open-redirect safe). */
export function safeCallbackUrl(
  candidate: string | null | undefined,
  fallback: string = getLoginRedirectUrl(),
): string {
  if (!candidate) return fallback;
  if (!candidate.startsWith("/") || candidate.startsWith("//")) return fallback;
  if (candidate.startsWith("/signin") || candidate.startsWith("/signup")) {
    return fallback;
  }
  return candidate;
}
