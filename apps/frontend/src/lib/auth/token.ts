/**
 * In-memory access token only (never localStorage / sessionStorage / cookie).
 * Refresh token lives in an HttpOnly cookie on the API origin.
 */
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function clearAccessToken(): void {
  accessToken = null;
}
