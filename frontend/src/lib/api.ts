/**
 * Authenticated API client for SEOJEV Platform API.
 */
import {
  AuthResponse,
  Site,
  SiteCreateRequest,
  Run,
  RunCreateRequest,
  Artifact,
  SignedDownloadResponse,
  SSEProgressEvent,
  User,
} from "@/types/api";

const TOKEN_KEY = "seojev_access_token";
const USER_KEY = "seojev_user";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const custom = (window as any).__SEOJEV_API_URL__ || localStorage.getItem("seojev_api_url");
    if (custom) return custom;
    return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setStoredUser(user: User): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
}

export function clearStoredAuth(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${baseUrl}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearStoredAuth();
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // fallback to status text
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------
export async function register(
  email: string,
  password: string,
  orgName?: string,
  orgSlug?: string
): Promise<AuthResponse> {
  const res = await request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      org_name: orgName,
      org_slug: orgSlug,
    }),
  });
  setStoredToken(res.access_token);
  setStoredUser(res.user);
  return res;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setStoredToken(res.access_token);
  setStoredUser(res.user);
  return res;
}

// ---------------------------------------------------------------------------
// Sites CRUD
// ---------------------------------------------------------------------------
export async function getSites(): Promise<Site[]> {
  return request<Site[]>("/sites");
}

export async function getSite(id: string): Promise<Site> {
  return request<Site>(`/sites/${id}`);
}

export async function createSite(payload: SiteCreateRequest): Promise<Site> {
  return request<Site>("/sites", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// Runs CRUD & Actions
// ---------------------------------------------------------------------------
export async function getRuns(siteId?: string): Promise<Run[]> {
  const query = siteId ? `?site_id=${encodeURIComponent(siteId)}` : "";
  return request<Run[]>(`/runs${query}`);
}

export async function getRun(id: string): Promise<Run> {
  return request<Run>(`/runs/${id}`);
}

export async function createRun(payload: RunCreateRequest): Promise<Run> {
  return request<Run>("/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function cancelRun(id: string): Promise<{ cancelled: boolean; run_id: string; status: string }> {
  return request<{ cancelled: boolean; run_id: string; status: string }>(`/runs/${id}/cancel`, {
    method: "POST",
  });
}

// ---------------------------------------------------------------------------
// Artifacts & Deliverables
// ---------------------------------------------------------------------------
export async function getRunArtifacts(runId: string): Promise<Artifact[]> {
  return request<Artifact[]>(`/runs/${runId}/artifacts`);
}

export async function getArtifactDownloadUrl(artifactId: string): Promise<SignedDownloadResponse> {
  return request<SignedDownloadResponse>(`/artifacts/${artifactId}/download`);
}

export async function getRunExportZipUrl(runId: string): Promise<SignedDownloadResponse> {
  return request<SignedDownloadResponse>(`/runs/${runId}/export.zip`);
}

// ---------------------------------------------------------------------------
// Real-Time SSE Progress Stream
// ---------------------------------------------------------------------------
export function subscribeRunProgress(
  runId: string,
  onEvent: (event: SSEProgressEvent) => void,
  onError?: (err: Error) => void,
  onComplete?: () => void
): () => void {
  let isCancelled = false;
  const controller = new AbortController();

  async function connect() {
    const baseUrl = getApiBaseUrl();
    const token = getStoredToken();
    const headers: Record<string, string> = {
      Accept: "text/event-stream",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${baseUrl}/runs/${runId}/progress`, {
        headers,
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`SSE stream connection failed: HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error("ReadableStream not supported by browser/environment");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!isCancelled) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith(":")) continue; // heartbeat ping

          if (trimmed.startsWith("data:")) {
            const dataStr = trimmed.slice(5).trim();
            if (dataStr) {
              try {
                const parsed: SSEProgressEvent = JSON.parse(dataStr);
                onEvent(parsed);
                if (
                  parsed.status &&
                  ["completed", "cancelled", "failed", "needs_attention"].includes(parsed.status)
                ) {
                  if (onComplete) onComplete();
                  return;
                }
              } catch {
                // Ignore parse errors on partial frames
              }
            }
          }
        }
      }

      if (!isCancelled && onComplete) {
        onComplete();
      }
    } catch (err: any) {
      if (!isCancelled) {
        if (err.name !== "AbortError" && onError) {
          onError(err);
        }
      }
    }
  }

  connect();

  return () => {
    isCancelled = true;
    controller.abort();
  };
}
