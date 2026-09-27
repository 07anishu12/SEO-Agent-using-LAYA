/**
 * TypeScript API models for SEOJEV Platform API.
 */

export interface User {
  id: string;
  email: string;
  org_id: string;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Site {
  id: string;
  org_id: string;
  domain: string;
  url: string;
  vertical: string;
  config_json?: Record<string, any>;
  created_at?: string;
}

export interface SiteCreateRequest {
  url: string;
  domain?: string;
  vertical?: string;
  config_json?: Record<string, any>;
}

export interface RunCounts {
  findings?: number;
  opportunities?: number;
  work_orders?: number;
  templates?: number;
  [key: string]: number | undefined;
}

export interface Run {
  id: string;
  org_id: string;
  site_id: string;
  status: "queued" | "running" | "completed" | "cancelled" | "failed" | "needs_attention" | string;
  started_at?: string;
  finished_at?: string;
  progress_pct: number;
  current_pass?: string;
  urls_discovered: number;
  urls_crawled: number;
  urls_failed: number;
  total_issues: number;
  counts?: RunCounts;
  deliverables?: Record<string, any>;
}

export interface RunCreateRequest {
  site_id: string;
  crawl_id?: string;
  max_pages?: number;
  concurrency?: number;
  render?: boolean;
  fresh?: boolean;
  sync?: boolean;
  options?: Record<string, any>;
}

export interface Artifact {
  id: string;
  org_id: string;
  site_id: string;
  run_id: string;
  filename: string;
  artifact_type: string;
  size_bytes: number;
  checksum_sha256?: string;
  content_type?: string;
  created_at?: string;
}

export interface SignedDownloadResponse {
  artifact_id?: string;
  filename: string;
  download_url: string;
  expires_in: number;
  size_bytes?: number;
  checksum_sha256?: string;
}

export interface SSEProgressEvent {
  run_id?: string;
  status?: string;
  pct?: number;
  pass_name?: string;
  message?: string;
  urls_crawled?: number;
  urls_discovered?: number;
  issues_found?: number;
}
