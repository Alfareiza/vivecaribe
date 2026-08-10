import { getApiBaseUrl } from "@/lib/config";
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "@/lib/auth/token";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

type TokenResponse = {
  access_token: string;
  token_type?: string;
};

let refreshInFlight: Promise<boolean> | null = null;

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export async function refreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        clearAccessToken();
        return false;
      }
      const body = (await response.json()) as TokenResponse;
      if (!body.access_token) {
        clearAccessToken();
        return false;
      }
      setAccessToken(body.access_token);
      return true;
    } catch {
      clearAccessToken();
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const response = await fetch(`${getApiBaseUrl()}/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const body = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(
      detailMessage(body, "No se pudo iniciar sesión"),
      response.status,
      body,
    );
  }
  const tokens = body as TokenResponse;
  setAccessToken(tokens.access_token);
  return tokens;
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${getApiBaseUrl()}/logout`, {
      method: "POST",
      credentials: "include",
    });
  } finally {
    clearAccessToken();
  }
}

type ApiFetchOptions = RequestInit & {
  skipAuth?: boolean;
  retryOnUnauthorized?: boolean;
};

export async function apiFetch(
  path: string,
  options: ApiFetchOptions = {},
): Promise<Response> {
  const {
    skipAuth = false,
    retryOnUnauthorized = true,
    headers,
    ...rest
  } = options;

  const finalHeaders = new Headers(headers);
  if (!skipAuth) {
    const token = getAccessToken();
    if (token) {
      finalHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

  const url = path.startsWith("http") ? path : `${getApiBaseUrl()}${path}`;
  const response = await fetch(url, {
    ...rest,
    credentials: "include",
    headers: finalHeaders,
  });

  if (response.status !== 401 || skipAuth || !retryOnUnauthorized) {
    return response;
  }

  const refreshed = await refreshAccessToken();
  if (!refreshed) {
    return response;
  }

  const retryHeaders = new Headers(headers);
  const token = getAccessToken();
  if (token) {
    retryHeaders.set("Authorization", `Bearer ${token}`);
  }
  return fetch(url, {
    ...rest,
    credentials: "include",
    headers: retryHeaders,
  });
}

export async function apiJson<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const response = await apiFetch(path, options);
  const body = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(
      detailMessage(body, "Error de la API"),
      response.status,
      body,
    );
  }
  return body as T;
}
