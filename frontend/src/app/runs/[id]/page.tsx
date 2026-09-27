"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import {
  getRun,
  cancelRun,
  getRunArtifacts,
  getArtifactDownloadUrl,
  getRunExportZipUrl,
  subscribeRunProgress,
} from "@/lib/api";
import { Run, Artifact, SSEProgressEvent } from "@/types/api";
import RunNavTabs from "@/components/RunNavTabs";
import {
  ArrowLeft,
  Play,
  Square,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Download,
  FileText,
  FileSpreadsheet,
  FileCode,
  Archive,
  RefreshCw,
  Layers,
  Search,
  ExternalLink,
} from "lucide-react";

const PASS_NAMES = [
  { id: "P1_CRAWL", label: "Pass 1: Discovery & HTTP Crawl" },
  { id: "P2_DETERMINISTIC_EVIDENCE", label: "Pass 2: Deterministic Evidence" },
  { id: "P3_CANDIDATE_REDUCTION", label: "Pass 3: Candidate & Template Reduction" },
  { id: "P4_LAYA_DECISION_ENGINE", label: "Pass 4: Laya SEO Decision Engine" },
  { id: "P5_VALIDATED_OPPORTUNITIES", label: "Pass 5: Validated Opportunities, Priority & Work Orders" },
  { id: "P6_REPORTS", label: "Pass 6: Reports" },
];

export default function RunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Live SSE Telemetry state
  const [pct, setPct] = useState<number>(0);
  const [currentPass, setCurrentPass] = useState<string>("QUEUED");
  const [liveMessage, setLiveMessage] = useState<string>("Waiting for run telemetry...");
  const [sseConnected, setSseConnected] = useState<boolean>(false);
  const [terminalReached, setTerminalReached] = useState<boolean>(false);
  const [layaTelemetry, setLayaTelemetry] = useState<Record<string, any> | null>(null);

  // Cancellation state
  const [cancelling, setCancelling] = useState<boolean>(false);

  // Artifacts state
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loadingArtifacts, setLoadingArtifacts] = useState<boolean>(false);
  const [exportingZip, setExportingZip] = useState<boolean>(false);

  // Fetch run metadata
  const fetchRunData = useCallback(async () => {
    try {
      const data = await getRun(runId);
      setRun(data);
      setPct(data.progress_pct || 0);
      if (data.current_pass) {
        setCurrentPass(data.current_pass);
      }
      if (["completed", "cancelled", "failed", "needs_attention"].includes(data.status)) {
        setTerminalReached(true);
        setSseConnected(false);
        if (data.status === "completed") {
          setPct(100);
          setCurrentPass("P6_REPORTS");
          setLiveMessage("Run completed. Telemetry stream closed.");
        }
      }
      return data;
    } catch (err: any) {
      setError(err.message || "Failed to load run details");
      return null;
    } finally {
      setLoading(false);
    }
  }, [runId]);

  // Fetch artifacts
  const fetchArtifacts = useCallback(async () => {
    setLoadingArtifacts(true);
    try {
      const list = await getRunArtifacts(runId);
      setArtifacts(list);
    } catch {
      // Artifacts may not be ready yet
    } finally {
      setLoadingArtifacts(false);
    }
  }, [runId]);

  // Initial load
  useEffect(() => {
    fetchRunData().then((r) => {
      if (r && r.status === "completed") {
        fetchArtifacts();
      }
    });
  }, [fetchRunData, fetchArtifacts]);

  // SSE subscription
  useEffect(() => {
    if (!runId || terminalReached) return;

    let unsubscribe: (() => void) | null = null;

    try {
      unsubscribe = subscribeRunProgress(
        runId,
        (evt: SSEProgressEvent) => {
          setSseConnected(true);
          if (evt.pct !== undefined) {
            setPct((prev) => Math.max(prev, evt.pct || 0));
          }
          if (evt.pass_name || evt.pass) {
            setCurrentPass(evt.pass_name || evt.pass || "QUEUED");
          }
          if (evt.message) {
            setLiveMessage(evt.message);
          }
          if (evt.meta?.laya_telemetry) {
            setLayaTelemetry(evt.meta.laya_telemetry);
          }
          if (evt.status) {
            setRun((prev) => (prev ? { ...prev, status: evt.status! } : prev));
            if (["completed", "cancelled", "failed", "needs_attention"].includes(evt.status)) {
              setTerminalReached(true);
              setSseConnected(false);
              if (evt.status === "completed") {
                setPct(100);
                setCurrentPass("P6_REPORTS");
                setLiveMessage("Run completed. Telemetry stream closed.");
              }
              fetchRunData();
              if (evt.status === "completed") {
                fetchArtifacts();
              }
            }
          }
        },
        (err) => {
          setSseConnected(false);
          // Fall back to polling if SSE drops
          fetchRunData();
        },
        () => {
          setSseConnected(false);
          fetchRunData();
          fetchArtifacts();
        }
      );
    } catch (e) {
      // Fallback
    }

    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [runId, terminalReached, fetchRunData, fetchArtifacts]);

  // Handle Cancellation
  const handleCancel = async () => {
    if (!confirm("Are you sure you want to stop this crawl run?")) return;
    setCancelling(true);
    try {
      await cancelRun(runId);
      await fetchRunData();
    } catch (err: any) {
      alert(err.message || "Failed to cancel run");
    } finally {
      setCancelling(false);
    }
  };

  // Handle Individual Artifact Download
  const handleDownloadArtifact = async (artifactId: string) => {
    try {
      const res = await getArtifactDownloadUrl(artifactId);
      window.open(res.download_url, "_blank");
    } catch (err: any) {
      alert(err.message || "Failed to generate download link");
    }
  };

  // Handle Export Zip Download
  const handleExportZip = async () => {
    setExportingZip(true);
    try {
      const res = await getRunExportZipUrl(runId);
      window.open(res.download_url, "_blank");
    } catch (err: any) {
      alert(err.message || "Failed to create export zip");
    } finally {
      setExportingZip(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "queued":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            <Clock className="w-3.5 h-3.5" />
            Queued
          </span>
        );
      case "running":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-sky-950 text-sky-300 border border-sky-800 animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            Running
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Completed
          </span>
        );
      case "cancelled":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            <Square className="w-3.5 h-3.5" />
            Cancelled
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-950 text-rose-300 border border-rose-800">
            <XCircle className="w-3.5 h-3.5" />
            Failed
          </span>
        );
      case "needs_attention":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            <AlertTriangle className="w-3.5 h-3.5" />
            Needs Attention
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400">
            {status}
          </span>
        );
    }
  };

  const getArtifactIcon = (type: string) => {
    switch (type) {
      case "report_docx":
        return <FileText className="w-4 h-4 text-blue-400" />;
      case "csv_report":
        return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
      case "html_report":
        return <FileCode className="w-4 h-4 text-purple-400" />;
      case "archive_zip":
        return <Archive className="w-4 h-4 text-amber-400" />;
      default:
        return <FileText className="w-4 h-4 text-slate-400" />;
    }
  };

  const isPassActive = (passId: string) => currentPass === passId;
  const isPassFinished = (passIndex: number) => {
    if (run?.status === "completed") return true;
    const currentPassIndex = PASS_NAMES.findIndex((p) => p.id === currentPass);
    if (currentPassIndex === -1) return false;
    return passIndex < currentPassIndex;
  };

  return (
    <ProtectedRoute>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Navigation & Header */}
        <div>
          <Link
            href="/runs"
            className="inline-flex items-center space-x-2 text-sm text-slate-400 hover:text-white transition mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Runs</span>
          </Link>

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center space-x-3">
                <h1 className="text-2xl font-bold tracking-tight text-white font-mono">
                  {runId}
                </h1>
                {run && getStatusBadge(run.status)}
              </div>
              <p className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                <span>Site ID: <strong className="text-slate-200">{run?.site_id || "Loading..."}</strong></span>
                <span>•</span>
                <span>Org ID: <strong className="text-slate-200">{run?.org_id || "..."}</strong></span>
              </p>
            </div>

            {/* Header Actions */}
            <div className="flex items-center space-x-3">
              {run && (run.status === "running" || run.status === "queued") && (
                <button
                  onClick={handleCancel}
                  disabled={cancelling}
                  className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-sm font-semibold transition"
                >
                  <Square className="w-4 h-4 fill-current" />
                  <span>{cancelling ? "Stopping..." : "Cancel Run"}</span>
                </button>
              )}

              {run && run.status === "completed" && (
                <button
                  onClick={handleExportZip}
                  disabled={exportingZip}
                  className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold shadow-md shadow-sky-600/20 transition disabled:opacity-50"
                >
                  {exportingZip ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  <span>Download All (.zip)</span>
                </button>
              )}
            </div>
          </div>

          <div className="mt-6">
            <RunNavTabs runId={runId} />
          </div>
        </div>

        {error && (
          <div className="rounded-lg bg-rose-500/10 border border-rose-500/30 p-4 flex items-center space-x-3 text-rose-300 text-sm">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Live Progress Telemetry Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-slate-800 gap-4">
            <div>
              <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                Live Pipeline Telemetry
              </span>
              <div className="flex items-center space-x-3 mt-1">
                <span className="text-3xl font-extrabold text-white font-mono">
                  {Math.round(pct)}%
                </span>
                <span className="text-sm font-medium text-sky-400 px-2.5 py-0.5 rounded bg-sky-950 border border-sky-800 font-mono">
                  {currentPass}
                </span>
              </div>
            </div>

            <div className="text-right flex items-center sm:block space-x-2 sm:space-x-0">
              <span className="text-xs text-slate-500">Channel Status: </span>
              <span
                className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
                  sseConnected ? "text-emerald-400" : "text-slate-400"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    sseConnected ? "bg-emerald-400 animate-ping" : "bg-slate-500"
                  }`}
                ></span>
                {sseConnected ? "Live SSE Connected" : "Stream Closed"}
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mt-6">
            <div className="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
              <div
                className="bg-gradient-to-r from-sky-500 to-emerald-400 h-full transition-all duration-300 ease-out"
                style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
              ></div>
            </div>
            <p className="text-xs text-slate-400 mt-2 font-mono truncate" title={liveMessage}>
              &gt; {liveMessage}
            </p>
            {layaTelemetry && (
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                Laya: {layaTelemetry.total_candidates ?? 0} candidates · {layaTelemetry.total_decisions ?? 0} decisions · {layaTelemetry.total_cache_hits ?? 0} cache hits · {layaTelemetry.total_cache_misses ?? 0} misses · {layaTelemetry.decisions_per_sec ?? 0}/s · p50 {Math.round(layaTelemetry.p50_ms ?? 0)}ms · p95 {Math.round(layaTelemetry.p95_ms ?? 0)}ms
              </p>
            )}
          </div>

          {/* 6-Pass Step Timeline */}
          <div className="mt-8 pt-6 border-t border-slate-800">
            <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-4">
              Pass-by-Pass Pipeline Execution
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {PASS_NAMES.map((p, idx) => {
                const finished = isPassFinished(idx);
                const active = isPassActive(p.id);

                return (
                  <div
                    key={p.id}
                    className={`p-3 rounded-lg border text-xs flex items-center space-x-3 transition ${
                      finished
                        ? "bg-slate-950 border-emerald-800/40 text-emerald-300"
                        : active
                        ? "bg-sky-950/40 border-sky-600 text-sky-200 animate-pulse"
                        : "bg-slate-950/60 border-slate-800 text-slate-500"
                    }`}
                  >
                    {finished ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    ) : active ? (
                      <RefreshCw className="w-4 h-4 text-sky-400 animate-spin flex-shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-slate-700 flex items-center justify-center text-[10px] text-slate-500">
                        {idx + 1}
                      </div>
                    )}
                    <span className="font-medium truncate">{p.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Crawl & Opportunity Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
              URLs Crawled
            </span>
            <div className="text-2xl font-bold text-white mt-1">
              {run?.urls_crawled || 0}
            </div>
            <span className="text-[11px] text-slate-500">
              Discovered: {run?.urls_discovered || 0}
            </span>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
              Opportunities
            </span>
            <div className="text-2xl font-bold text-sky-400 mt-1">
              {run?.counts?.opportunities || 0}
            </div>
            <span className="text-[11px] text-slate-500">
              Findings: {run?.counts?.findings || run?.total_issues || 0}
            </span>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
              Templates
            </span>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              {run?.counts?.templates || 0}
            </div>
            <span className="text-[11px] text-slate-500">SimHash Clustered</span>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
              Work Orders
            </span>
            <div className="text-2xl font-bold text-purple-400 mt-1">
              {run?.counts?.work_orders || 0}
            </div>
            <span className="text-[11px] text-slate-500">Eng & Content Tickets</span>
          </div>
        </div>

        {/* Artifacts & Deliverables Section */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl">
          <div className="flex items-center justify-between pb-6 border-b border-slate-800">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <Archive className="w-5 h-5 text-sky-400" />
                <span>Generated Deliverables & Reports</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Direct S3/MinIO signed downloads without API proxying
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href={`/runs/${runId}/downloads`}
                className="text-xs text-sky-400 hover:text-sky-300 font-semibold flex items-center gap-1 hover:underline"
              >
                <span>Downloads Center</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
              {run?.status === "completed" && (
                <button
                  onClick={fetchArtifacts}
                  className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
                  title="Refresh Artifacts"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {loadingArtifacts ? (
            <div className="py-8 flex items-center justify-center space-x-3 text-slate-400 text-xs">
              <div className="w-5 h-5 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
              <span>Loading artifacts ledger...</span>
            </div>
          ) : artifacts.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              {run?.status === "completed"
                ? "No artifacts recorded in ledger for this run."
                : "Deliverables will appear here once the run reaches 'completed' status."}
            </div>
          ) : (
            <div className="mt-4 divide-y divide-slate-800">
              {artifacts.map((art) => (
                <div
                  key={art.id}
                  className="py-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 hover:bg-slate-850/40 px-2 rounded-lg transition"
                >
                  <div className="flex items-center space-x-3 min-w-0">
                    <div className="p-2 rounded bg-slate-800 flex-shrink-0">
                      {getArtifactIcon(art.artifact_type)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate" title={art.filename}>
                        {art.filename}
                      </p>
                      <div className="flex items-center space-x-3 text-[11px] text-slate-500 font-mono mt-0.5">
                        <span>{(art.size_bytes / 1024).toFixed(1)} KB</span>
                        <span>•</span>
                        <span className="uppercase">{art.artifact_type}</span>
                        {art.checksum_sha256 && (
                          <>
                            <span>•</span>
                            <span className="truncate max-w-[120px]" title={art.checksum_sha256}>
                              SHA: {art.checksum_sha256.slice(0, 8)}...
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDownloadArtifact(art.id)}
                    className="self-start sm:self-auto inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-400 hover:text-sky-300 text-xs font-semibold transition"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
