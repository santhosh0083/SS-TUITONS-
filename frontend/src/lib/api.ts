/**
 * API client for the SS Tuitions backend.
 *
 * Two deliberate choices:
 *
 * 1. The access token is held in memory only — never localStorage. Anything in
 *    localStorage is readable by any script on the page, so one XSS bug hands
 *    an attacker a working session. The refresh token lives in an httpOnly
 *    cookie the browser sends automatically and JavaScript cannot read.
 *
 * 2. A 401 triggers exactly one silent refresh-and-retry. Concurrent requests
 *    share that single refresh rather than each firing their own, which would
 *    otherwise cause the backend's token-rotation reuse detection to fire and
 *    log the user out of every device.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

let accessToken: string | null = null;
let refreshPromise: Promise<boolean> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Pull a readable message out of an error response body. */
async function extractMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") return data.detail;
    // FastAPI validation errors arrive as an array of field problems.
    if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
      return data.detail[0].msg as string;
    }
  } catch {
    /* body was not JSON */
  }
  if (response.status === 503) {
    return "The service is temporarily unavailable. Please try again shortly.";
  }
  return "Something went wrong. Please try again.";
}

/** Refresh the access token. Concurrent callers share one in-flight attempt. */
async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        accessToken = null;
        return false;
      }
      const data = await response.json();
      accessToken = data.access_token;
      return true;
    } catch {
      accessToken = null;
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Internal: prevents infinite retry loops. */
  _isRetry?: boolean;
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, _isRetry, headers, ...rest } = options;

  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    credentials: "include",
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // Expired access token: refresh once, then retry the original request.
  if (response.status === 401 && !_isRetry && accessToken !== null) {
    if (await refreshAccessToken()) {
      return apiFetch<T>(path, { ...options, _isRetry: true });
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, await extractMessage(response));
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  roles: string[];
  is_superadmin: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export async function login(
  email: string,
  password: string,
): Promise<UserProfile> {
  const tokens = await apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
  accessToken = tokens.access_token;
  return apiFetch<UserProfile>("/auth/me");
}

export async function logout(): Promise<void> {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } finally {
    accessToken = null;
  }
}

export async function fetchMe(): Promise<UserProfile> {
  return apiFetch<UserProfile>("/auth/me");
}

/** Restore a session on page load using the httpOnly refresh cookie. */
export async function restoreSession(): Promise<UserProfile | null> {
  if (!(await refreshAccessToken())) return null;
  try {
    return await fetchMe();
  } catch {
    return null;
  }
}

export interface ReadyStatus {
  ready: boolean;
  database: string;
  tables_expected?: number;
  tables_found?: number;
  migration_revision?: string | null;
  hint?: string | null;
  reason?: string;
}

export async function fetchReadiness(): Promise<ReadyStatus> {
  return apiFetch<ReadyStatus>("/ready");
}


export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await apiFetch("/auth/change-password", {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
  });
}

export async function forgotPassword(email: string): Promise<string> {
  const r = await apiFetch<{ detail: string }>("/auth/forgot-password", {
    method: "POST",
    body: { email },
  });
  return r.detail;
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<void> {
  await apiFetch("/auth/reset-password", {
    method: "POST",
    body: { token, new_password: newPassword },
  });
}
