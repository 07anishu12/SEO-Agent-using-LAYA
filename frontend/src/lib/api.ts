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
  Opportunity,
  TemplateSummary,
  TemplateDetail,
  BlueprintPage,
  BlueprintDetail,
  GscData,
  WorkOrder,
  WorkOrderExportResponse,
  WorkOrderVerifyResponse,
  SnapshotDiffResponse,
  CompareTarget,
  WatchConfig,
  WatchConfigRequest,
  Alert,
  AlertListResponse,
  SiteTrendsResponse,
  TrendPoint,
  SearchResponse,
  PortfolioResponse,
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
// Stage 7: Opportunities & Feedback API
// ---------------------------------------------------------------------------
export interface OpportunityFilterParams {
  tier?: string;
  confidence?: string;
  type?: string;
  search?: string;
  sort_by?: string;
  order?: "asc" | "desc";
}

export async function getRunOpportunities(
  runId: string,
  filters: OpportunityFilterParams = {}
): Promise<Opportunity[]> {
  const params = new URLSearchParams();
  if (filters.tier) params.set("tier", filters.tier);
  if (filters.confidence) params.set("confidence", filters.confidence);
  if (filters.type) params.set("type", filters.type);
  if (filters.search) params.set("search", filters.search);
  if (filters.sort_by) params.set("sort_by", filters.sort_by);
  if (filters.order) params.set("order", filters.order);

  const query = params.toString() ? `?${params.toString()}` : "";
  return request<Opportunity[]>(`/runs/${runId}/opportunities${query}`);
}

export async function getOpportunity(id: string): Promise<Opportunity> {
  return request<Opportunity>(`/opportunities/${id}`);
}

export async function submitOpportunityFeedback(
  opportunityId: string,
  verdict: "fixed" | "false_positive" | "accepted" | "wont_fix",
  note?: string
): Promise<{ success: boolean; verdict: string }> {
  return request<{ success: boolean; verdict: string }>(`/opportunities/${opportunityId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ verdict, note }),
  });
}

// ---------------------------------------------------------------------------
// Stage 7: Templates API
// ---------------------------------------------------------------------------
export async function getRunTemplates(runId: string, search?: string): Promise<TemplateSummary[]> {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  return request<TemplateSummary[]>(`/runs/${runId}/templates${query}`);
}

export async function getTemplateDetail(runId: string, templateId: string): Promise<TemplateDetail> {
  return request<TemplateDetail>(`/runs/${runId}/templates/${encodeURIComponent(templateId)}`);
}

// ---------------------------------------------------------------------------
// Stage 7: Blueprints API
// ---------------------------------------------------------------------------
export async function getRunBlueprintPages(
  runId: string,
  search?: string,
  templateId?: string
): Promise<BlueprintPage[]> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (templateId) params.set("template_id", templateId);
  const query = params.toString() ? `?${params.toString()}` : "";
  return request<BlueprintPage[]>(`/runs/${runId}/blueprints${query}`);
}

export async function getBlueprintDetail(runId: string, url: string): Promise<BlueprintDetail> {
  return request<BlueprintDetail>(`/runs/${runId}/blueprints/detail?url=${encodeURIComponent(url)}`);
}

// ---------------------------------------------------------------------------
// Stage 7: Query / GSC API
// ---------------------------------------------------------------------------
export async function getRunGsc(runId: string): Promise<GscData> {
  return request<GscData>(`/runs/${runId}/gsc`);
}

export async function importRunGsc(
  runId: string,
  payload: { csv_content?: string; generate_synthetic?: boolean; rows?: any[] }
): Promise<any> {
  return request<any>(`/runs/${runId}/gsc`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
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

// ---------------------------------------------------------------------------
// Stage 8: Work Orders API
// ---------------------------------------------------------------------------
export interface WorkOrderFilterParams {
  order_type?: string;
  priority?: string;
  search?: string;
}

export async function getRunWorkOrders(
  runId: string,
  filters: WorkOrderFilterParams = {}
): Promise<WorkOrder[]> {
  const params = new URLSearchParams();
  if (filters.order_type) params.set("order_type", filters.order_type);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.search) params.set("search", filters.search);

  const query = params.toString() ? `?${params.toString()}` : "";
  return request<WorkOrder[]>(`/runs/${runId}/work-orders${query}`);
}

export async function getWorkOrder(id: string): Promise<WorkOrder> {
  return request<WorkOrder>(`/work-orders/${id}`);
}

export async function exportWorkOrder(
  id: string,
  platform: "github" | "jira" | "linear" | "markdown" = "github"
): Promise<WorkOrderExportResponse> {
  return request<WorkOrderExportResponse>(`/work-orders/${id}/export?platform=${platform}`, {
    method: "POST",
  });
}

export async function verifyWorkOrder(
  id: string,
  options: { target_url?: string; html_content?: string; live_fetch?: boolean } = {}
): Promise<WorkOrderVerifyResponse> {
  return request<WorkOrderVerifyResponse>(`/work-orders/${id}/verify`, {
    method: "POST",
    body: JSON.stringify(options),
  });
}

// ---------------------------------------------------------------------------
// Stage 8: Snapshot Diff API
// ---------------------------------------------------------------------------
export async function getRunDiff(
  runId: string,
  compareRunId?: string
): Promise<SnapshotDiffResponse> {
  const query = compareRunId ? `?compare_run_id=${encodeURIComponent(compareRunId)}` : "";
  return request<SnapshotDiffResponse>(`/runs/${runId}/diff${query}`);
}

export async function getRunCompareTargets(runId: string): Promise<CompareTarget[]> {
  return request<CompareTarget[]>(`/runs/${runId}/compare-targets`);
}

// ---------------------------------------------------------------------------
// Stage 9: Watch & Alerts API
// ---------------------------------------------------------------------------
export async function getWatchConfig(siteId: string): Promise<WatchConfig> {
  return request<WatchConfig>(`/sites/${siteId}/watch`);
}

export async function updateWatchConfig(siteId: string, req: WatchConfigRequest): Promise<WatchConfig> {
  return request<WatchConfig>(`/sites/${siteId}/watch`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getSiteAlerts(
  siteId: string,
  params?: { severity?: string; alert_type?: string; status?: string; limit?: number; offset?: number }
): Promise<AlertListResponse> {
  const query = new URLSearchParams();
  if (params?.severity) query.set("severity", params.severity);
  if (params?.alert_type) query.set("alert_type", params.alert_type);
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset) query.set("offset", params.offset.toString());
  const qs = query.toString();
  return request<AlertListResponse>(`/sites/${siteId}/alerts${qs ? `?${qs}` : ""}`);
}

export async function resolveAlert(siteId: string, alertId: string): Promise<Alert> {
  return request<Alert>(`/sites/${siteId}/alerts/${alertId}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "resolved" }),
  });
}

// ---------------------------------------------------------------------------
// Stage 10a: Historical Trends API
// ---------------------------------------------------------------------------
export async function getSiteTrends(
  siteId: string,
  params?: { metric?: string; start_date?: string; end_date?: string }
): Promise<SiteTrendsResponse> {
  const query = new URLSearchParams();
  if (params?.metric) query.set("metric", params.metric);
  if (params?.start_date) query.set("start_date", params.start_date);
  if (params?.end_date) query.set("end_date", params.end_date);
  const qs = query.toString();
  return request<SiteTrendsResponse>(`/sites/${siteId}/trends${qs ? `?${qs}` : ""}`);
}

// ---------------------------------------------------------------------------
// Stage 10g: Full-Text Search API
// ---------------------------------------------------------------------------
export async function searchContent(
  query: string,
  siteId?: string,
  category?: string,
  limit: number = 20
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (siteId) params.append("site_id", siteId);
  if (category) params.append("category", category);
  if (limit) params.append("limit", limit.toString());
  const qs = params.toString();
  return request<SearchResponse>(`/search${qs ? `?${qs}` : ""}`);
}

// ---------------------------------------------------------------------------
// Stage 10i.1: Multi-Site Portfolio API
// ---------------------------------------------------------------------------
export async function getPortfolio(): Promise<PortfolioResponse> {
  return request<PortfolioResponse>("/sites/portfolio");
}

