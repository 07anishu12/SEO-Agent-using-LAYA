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

// ---------------------------------------------------------------------------
// Stage 7: Opportunities Models
// ---------------------------------------------------------------------------
export interface IceFactors {
  visibility?: number;
  gap?: number;
  page_importance?: number;
  template_scope?: number;
  technical_severity?: number;
  ctr_headroom?: number;
  link_gap?: number;
  [key: string]: any;
}

export interface Opportunity {
  id: string;
  org_id: string;
  run_id: string;
  site_id: string;
  fingerprint: string;
  display_id: string;
  type?: string;
  tier?: string;
  confidence?: string;
  effort?: string;
  priority_score?: number;
  factors_json?: IceFactors;
  evidence_refs?: any[];
  observation?: string;
  diagnosis?: string;
  hypothesis?: string;
  action?: string;
  implementation_location?: string;
  affected_templates?: any[];
  affected_urls_count: number;
  sample_urls?: string[];
  verification_spec?: string;
  feedback?: "fixed" | "false_positive" | "accepted" | "wont_fix" | string | null;
  created_at?: string;
}

// ---------------------------------------------------------------------------
// Stage 7: Templates Models
// ---------------------------------------------------------------------------
export interface TemplateSummary {
  id: string;
  org_id: string;
  run_id: string;
  site_id: string;
  template_id: string;
  page_type?: string;
  page_count: number;
  issue_count: number;
  avg_word_count?: number;
  avg_inlinks?: number;
  structural_signature?: string;
  sample_urls: string[];
}

export interface TemplateDetail {
  template: TemplateSummary;
  member_urls: string[];
  associated_findings: Array<{
    display_id: string;
    rule_id?: string;
    severity?: string;
    priority?: string;
    url?: string;
    message?: string;
    recommended_action?: string;
  }>;
}

// ---------------------------------------------------------------------------
// Stage 7: Blueprints Models
// ---------------------------------------------------------------------------
export interface BlueprintPage {
  url: string;
  template_id?: string;
  page_type?: string;
  status_code: number;
  title?: string;
  inlinks_count: number;
  word_count: number;
}

export interface BlueprintDetail {
  url: string;
  run_id: string;
  blueprint: Record<string, any>;
  markdown?: string;
}

// ---------------------------------------------------------------------------
// Stage 7: GSC & Search Performance Models
// ---------------------------------------------------------------------------
export interface StrikingDistanceQuery {
  query: string;
  url: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface CannibalizationPage {
  url: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface CannibalizationQuery {
  query: string;
  pages_count: number;
  total_impressions: number;
  total_clicks: number;
  pages: CannibalizationPage[];
}

export interface QueryCluster {
  cluster_name: string;
  query_count: number;
  clicks: number;
  impressions: number;
  avg_position: number;
}

export interface TrendBracket {
  bracket: string;
  impressions?: number;
  clicks?: number;
  query_count: number;
}

export interface GscData {
  has_data: boolean;
  total_queries: number;
  total_clicks: number;
  total_impressions: number;
  avg_position: number;
  striking_distance_count: number;
  striking_distance_queries: StrikingDistanceQuery[];
  cannibalization_queries: CannibalizationQuery[];
  query_clusters: QueryCluster[];
  impression_trends: TrendBracket[];
  click_trends: TrendBracket[];
}

// ---------------------------------------------------------------------------
// Stage 8: Work Orders Models
// ---------------------------------------------------------------------------
export interface WorkOrder {
  id: string;
  org_id: string;
  run_id: string;
  site_id: string;
  opportunity_id?: string;
  display_id: string;
  title: string;
  order_type: "engineering" | "content" | string;
  status: string;
  priority?: "P0" | "P1" | "P2" | "P3" | string;
  scope?: string;
  problem?: string;
  required_change?: string;
  acceptance_criteria?: string;
  verify_spec?: string;
  evidence?: Record<string, any>;
  file_locations?: string[];
  ticket_ref?: string;
  verify_last_result?: "PASS" | "FAIL" | "ERROR" | string | null;
  created_at?: string;
}

export interface WorkOrderExportResponse {
  work_order_id: string;
  display_id: string;
  platform: "github" | "jira" | "linear" | "markdown" | string;
  filename: string;
  payload: Record<string, any>;
  file_content: string;
}

export interface WorkOrderVerifyResponse {
  verification_id: string;
  work_order_id: string;
  display_id: string;
  status: "PASS" | "FAIL" | "ERROR";
  spec: string;
  target_url?: string;
  details: string;
  executed_at: string;
}

// ---------------------------------------------------------------------------
// Stage 8: Snapshot Diff Models
// ---------------------------------------------------------------------------
export interface SnapshotDiffItem {
  before_snapshot_id: string;
  after_snapshot_id: string;
  url: string;
  template_id: string;
  fingerprint: string;
  category: "FIXED" | "REGRESSED" | "NEW_ISSUE" | "IMPROVED" | "STILL_FAILING" | "UNCHANGED";
  details: Record<string, any>;
}

export interface SnapshotDiffSummary {
  FIXED: number;
  REGRESSED: number;
  IMPROVED: number;
  NEW_ISSUE: number;
  STILL_FAILING: number;
  UNCHANGED: number;
}

export interface CompareTarget {
  id: string;
  site_id: string;
  status: string;
  created_at?: string;
}

export interface SnapshotDiffResponse {
  before_run_id: string;
  after_run_id: string;
  total_urls_compared: number;
  summary: SnapshotDiffSummary;
  by_template: Record<string, SnapshotDiffItem[]>;
  by_category: Record<string, SnapshotDiffItem[]>;
  differences: SnapshotDiffItem[];
  compare_targets: CompareTarget[];
}

