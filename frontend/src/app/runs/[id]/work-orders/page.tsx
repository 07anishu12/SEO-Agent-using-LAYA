"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import RunNavTabs from "@/components/RunNavTabs";
import { getRunWorkOrders, exportWorkOrder, verifyWorkOrder } from "@/lib/api";
import { WorkOrder, WorkOrderExportResponse, WorkOrderVerifyResponse } from "@/types/api";
import {
  ClipboardList,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  Share2,
  Download,
  Copy,
  Check,
  Search,
  Code,
  FileText,
  RefreshCw,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Filter,
  CheckSquare,
  Wrench,
  BookOpen
} from "lucide-react";

export default function WorkOrdersPage() {
  const params = useParams();
  const runId = params.id as string;

  const [activeTab, setActiveTab] = useState<"engineering" | "content">("engineering");
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");

  // Expanded tickets
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});

  // Verification State
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [verificationResults, setVerificationResults] = useState<Record<string, WorkOrderVerifyResponse>>({});

  // Export Modal State
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [currentExport, setCurrentExport] = useState<WorkOrderExportResponse | null>(null);
  const [activeExportPlatform, setActiveExportPlatform] = useState<"github" | "jira" | "linear" | "markdown">("github");
  const [currentExportWo, setCurrentExportWo] = useState<WorkOrder | null>(null);
  const [copiedPayload, setCopiedPayload] = useState(false);

  const fetchWorkOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRunWorkOrders(runId, {
        order_type: activeTab,
      });
      setWorkOrders(data);
    } catch (err: any) {
      setError(err.message || "Failed to load work orders");
    } finally {
      setLoading(false);
    }
  }, [runId, activeTab]);

  useEffect(() => {
    fetchWorkOrders();
  }, [fetchWorkOrders]);

  const toggleExpand = (id: string) => {
    setExpandedCards((prev) => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Run real verification
  const handleVerify = async (wo: WorkOrder) => {
    try {
      setVerifyingId(wo.id);
      const res = await verifyWorkOrder(wo.id, { live_fetch: true });
      setVerificationResults((prev) => ({
        ...prev,
        [wo.id]: res
      }));
      // Update local work order verify_last_result
      setWorkOrders((prev) =>
        prev.map((item) => (item.id === wo.id ? { ...item, verify_last_result: res.status } : item))
      );
    } catch (err: any) {
      alert(`Verification execution failed: ${err.message || err}`);
    } finally {
      setVerifyingId(null);
    }
  };

  // Open Export Modal & fetch export payload
  const handleOpenExport = async (wo: WorkOrder, platform: "github" | "jira" | "linear" | "markdown" = "github") => {
    try {
      setCurrentExportWo(wo);
      setActiveExportPlatform(platform);
      setExportModalOpen(true);
      setExportLoading(true);
      const res = await exportWorkOrder(wo.id, platform);
      setCurrentExport(res);
    } catch (err: any) {
      alert(`Export failed: ${err.message || err}`);
    } finally {
      setExportLoading(false);
    }
  };

  const handleSwitchPlatform = async (platform: "github" | "jira" | "linear" | "markdown") => {
    if (!currentExportWo) return;
    setActiveExportPlatform(platform);
    setExportLoading(true);
    try {
      const res = await exportWorkOrder(currentExportWo.id, platform);
      setCurrentExport(res);
    } catch (err: any) {
      alert(`Export failed: ${err.message || err}`);
    } finally {
      setExportLoading(false);
    }
  };

  const handleDownloadExportFile = () => {
    if (!currentExport) return;
    const blob = new Blob([currentExport.file_content], {
      type: currentExport.filename.endsWith(".json") ? "application/json" : "text/markdown",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = currentExport.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const copyPayload = () => {
    if (!currentExport) return;
    navigator.clipboard.writeText(currentExport.file_content);
    setCopiedPayload(true);
    setTimeout(() => setCopiedPayload(false), 2000);
  };

  const getPriorityBadge = (priority?: string) => {
    switch (priority?.toUpperCase()) {
      case "P0":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">P0 Urgent</span>;
      case "P1":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-500/10 text-orange-400 border border-orange-500/30">P1 High</span>;
      case "P2":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">P2 Medium</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">P3 Low</span>;
    }
  };

  const getVerificationStatusBadge = (status?: string | null) => {
    switch (status?.toUpperCase()) {
      case "PASS":
      case "PASSED":
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            PASS
          </span>
        );
      case "FAIL":
      case "FAILED":
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1.5">
            <XCircle className="w-3.5 h-3.5" />
            FAIL
          </span>
        );
      case "ERROR":
      case "INCONCLUSIVE":
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            ERROR
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700/60 flex items-center gap-1.5">
            <CheckSquare className="w-3.5 h-3.5" />
            Not Verified
          </span>
        );
    }
  };

  const filteredWorkOrders = workOrders.filter((wo) => {
    const matchesSearch =
      wo.title.toLowerCase().includes(search.toLowerCase()) ||
      wo.display_id.toLowerCase().includes(search.toLowerCase()) ||
      (wo.problem && wo.problem.toLowerCase().includes(search.toLowerCase()));

    const matchesPriority = priorityFilter === "ALL" || wo.priority?.toUpperCase() === priorityFilter;
    return matchesSearch && matchesPriority;
  });

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2 text-xs text-slate-400 mb-1">
                <Link href="/runs" className="hover:text-slate-200">
                  Runs
                </Link>
                <span>/</span>
                <Link href={`/runs/${runId}`} className="hover:text-slate-200 font-mono">
                  {runId}
                </Link>
                <span>/</span>
                <span className="text-sky-400 font-medium">Work Orders</span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                <ClipboardList className="w-6 h-6 text-sky-400" />
                Work Orders & Developer Tickets
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Engine-synthesized implementation specs with real GitHub, Jira, and Linear export and automated verification.
              </p>
            </div>

            {/* View Switch Pills (Engineering vs Content) */}
            <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-xl">
              <button
                onClick={() => setActiveTab("engineering")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
                  activeTab === "engineering"
                    ? "bg-sky-500/20 text-sky-400 border border-sky-500/30 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Wrench className="w-3.5 h-3.5" />
                <span>Engineering Work Orders</span>
              </button>
              <button
                onClick={() => setActiveTab("content")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
                  activeTab === "content"
                    ? "bg-sky-500/20 text-sky-400 border border-sky-500/30 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Content Work Orders</span>
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <RunNavTabs runId={runId} />

          {/* Metrics summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              <span className="text-xs text-slate-400">{activeTab === "engineering" ? "Engineering" : "Content"} Tickets</span>
              <p className="text-2xl font-bold text-white mt-1">{workOrders.length}</p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              <span className="text-xs text-slate-400">P0 / P1 Urgent</span>
              <p className="text-2xl font-bold text-rose-400 mt-1">
                {workOrders.filter((w) => w.priority === "P0" || w.priority === "P1").length}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              <span className="text-xs text-slate-400">Verified PASS</span>
              <p className="text-2xl font-bold text-emerald-400 mt-1">
                {workOrders.filter((w) => w.verify_last_result === "PASS").length}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              <span className="text-xs text-slate-400">Verified FAIL</span>
              <p className="text-2xl font-bold text-amber-400 mt-1">
                {workOrders.filter((w) => w.verify_last_result === "FAIL" || w.verify_last_result === "ERROR").length}
              </p>
            </div>
          </div>

          {/* Filters & Search */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800/80">
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Filter className="w-3.5 h-3.5" />
                Priority:
              </span>
              <div className="flex flex-wrap gap-1">
                {[
                  { id: "ALL", label: "All" },
                  { id: "P0", label: "P0" },
                  { id: "P1", label: "P1" },
                  { id: "P2", label: "P2" },
                  { id: "P3", label: "P3" },
                ].map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setPriorityFilter(p.id)}
                    className={`px-2.5 py-1 text-xs rounded-md font-medium transition ${
                      priorityFilter === p.id
                        ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                        : "text-slate-400 hover:text-white hover:bg-slate-800"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search ticket title or ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition"
              />
            </div>
          </div>

          {/* Work Orders List */}
          {loading ? (
            <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
              <RefreshCw className="w-6 h-6 animate-spin text-sky-400" />
              <p className="text-sm">Retrieving synthesized work orders from database...</p>
            </div>
          ) : error ? (
            <div className="p-6 bg-red-950/30 border border-red-800/50 rounded-xl text-red-300 text-sm">
              {error}
            </div>
          ) : filteredWorkOrders.length === 0 ? (
            <div className="p-12 text-center text-slate-500 border border-slate-800/60 rounded-xl bg-slate-900/20">
              <ClipboardList className="w-8 h-8 mx-auto text-slate-600 mb-2" />
              <p className="text-sm text-slate-300 font-medium">No work orders found</p>
              <p className="text-xs text-slate-500 mt-1">
                No tickets matching {activeTab} view and filter criteria.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredWorkOrders.map((wo) => {
                const isExpanded = expandedCards[wo.id] !== false;
                const isVerifying = verifyingId === wo.id;
                const verifResult = verificationResults[wo.id];
                const currentStatus = verifResult ? verifResult.status : wo.verify_last_result;

                return (
                  <div
                    key={wo.id}
                    className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm transition hover:border-slate-700"
                  >
                    {/* Header */}
                    <div className="p-4 bg-slate-950/60 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-sky-400 bg-sky-500/10 px-2.5 py-1 rounded-md border border-sky-500/30">
                          {wo.display_id}
                        </span>
                        {getPriorityBadge(wo.priority)}
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 uppercase">
                          {wo.scope || "page"}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800/80 text-slate-400">
                          {wo.order_type}
                        </span>
                      </div>

                      {/* Top Action Bar */}
                      <div className="flex items-center gap-2">
                        {getVerificationStatusBadge(currentStatus)}

                        <button
                          onClick={() => handleVerify(wo)}
                          disabled={isVerifying}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-semibold transition disabled:opacity-50"
                          title="Run automated verification on live site"
                        >
                          {isVerifying ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Play className="w-3.5 h-3.5" />
                          )}
                          <span>Run verification now</span>
                        </button>

                        <button
                          onClick={() => handleOpenExport(wo, "github")}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition"
                          title="Export ticket to GitHub, Jira, or Linear"
                        >
                          <Share2 className="w-3.5 h-3.5" />
                          <span>Export</span>
                        </button>

                        <button
                          onClick={() => toggleExpand(wo.id)}
                          className="p-1.5 text-slate-400 hover:text-white transition"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Title */}
                    <div className="p-4 pb-2">
                      <h3 className="text-base font-semibold text-white tracking-tight">
                        {wo.title}
                      </h3>
                    </div>

                    {/* Expanded details */}
                    {isExpanded && (
                      <div className="px-4 pb-4 space-y-4 text-xs">
                        {/* Problem & Diagnosis */}
                        {wo.problem && (
                          <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 space-y-1">
                            <span className="font-semibold text-slate-300 uppercase text-[10px] tracking-wider">
                              Problem & Evidence
                            </span>
                            <p className="text-slate-300 whitespace-pre-line leading-relaxed">
                              {wo.problem}
                            </p>
                          </div>
                        )}

                        {/* Required Change */}
                        {wo.required_change && (
                          <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 space-y-1">
                            <span className="font-semibold text-slate-300 uppercase text-[10px] tracking-wider">
                              Required Implementation
                            </span>
                            <p className="text-slate-300 whitespace-pre-line leading-relaxed">
                              {wo.required_change}
                            </p>
                          </div>
                        )}

                        {/* Acceptance Criteria */}
                        {wo.acceptance_criteria && (
                          <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 space-y-1">
                            <span className="font-semibold text-slate-300 uppercase text-[10px] tracking-wider">
                              Acceptance Criteria
                            </span>
                            <p className="text-slate-300 whitespace-pre-line leading-relaxed font-mono text-[11px]">
                              {wo.acceptance_criteria}
                            </p>
                          </div>
                        )}

                        {/* Automated Verification Spec */}
                        {wo.verify_spec && (
                          <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 space-y-1.5">
                            <span className="font-semibold text-slate-300 uppercase text-[10px] tracking-wider flex items-center gap-1.5">
                              <Code className="w-3.5 h-3.5 text-sky-400" />
                              Automated Verification Spec
                            </span>
                            <pre className="p-2 bg-slate-900 border border-slate-800 rounded font-mono text-[11px] text-sky-300 overflow-x-auto">
                              {wo.verify_spec}
                            </pre>
                          </div>
                        )}

                        {/* Inline Verification Result */}
                        {verifResult && (
                          <div
                            className={`p-3 rounded-lg border ${
                              verifResult.status === "PASS"
                                ? "bg-emerald-950/30 border-emerald-500/40 text-emerald-300"
                                : verifResult.status === "FAIL"
                                ? "bg-rose-950/30 border-rose-500/40 text-rose-300"
                                : "bg-amber-950/30 border-amber-500/40 text-amber-300"
                            }`}
                          >
                            <div className="flex items-center justify-between font-semibold mb-1">
                              <span className="flex items-center gap-1.5">
                                {verifResult.status === "PASS" ? (
                                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                ) : verifResult.status === "FAIL" ? (
                                  <XCircle className="w-4 h-4 text-rose-400" />
                                ) : (
                                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                                )}
                                Verification Execution Result: {verifResult.status}
                              </span>
                              <span className="font-mono text-[10px] text-slate-400">
                                {verifResult.executed_at}
                              </span>
                            </div>
                            <p className="text-xs">{verifResult.details}</p>
                            {verifResult.target_url && (
                              <p className="font-mono text-[11px] text-slate-400 mt-1 truncate">
                                Target: {verifResult.target_url}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Export Ticket Modal */}
          {exportModalOpen && currentExportWo && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl space-y-4 p-6">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Share2 className="w-5 h-5 text-sky-400" />
                    <h3 className="font-semibold text-white text-base">
                      Export Ticket — {currentExportWo.display_id}
                    </h3>
                  </div>
                  <button
                    onClick={() => setExportModalOpen(false)}
                    className="text-slate-400 hover:text-white text-sm"
                  >
                    ✕
                  </button>
                </div>

                {/* Platform Switcher Tabs */}
                <div className="flex border-b border-slate-800">
                  {[
                    { id: "github", label: "GitHub Issue" },
                    { id: "jira", label: "Jira Task" },
                    { id: "linear", label: "Linear Issue" },
                    { id: "markdown", label: "Markdown Document" },
                  ].map((p) => (
                    <button
                      key={p.id}
                      onClick={() => handleSwitchPlatform(p.id as any)}
                      className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${
                        activeExportPlatform === p.id
                          ? "border-sky-500 text-sky-400"
                          : "border-transparent text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>

                {/* Content Payload Preview */}
                {exportLoading ? (
                  <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-2">
                    <RefreshCw className="w-5 h-5 animate-spin text-sky-400" />
                    <span className="text-xs">Generating platform payload...</span>
                  </div>
                ) : currentExport ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span className="font-mono">Output: {currentExport.filename}</span>
                      <button
                        onClick={copyPayload}
                        className="flex items-center gap-1 text-sky-400 hover:text-sky-300 font-medium"
                      >
                        {copiedPayload ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                        <span>{copiedPayload ? "Copied" : "Copy Payload"}</span>
                      </button>
                    </div>

                    <pre className="p-3 bg-slate-950 border border-slate-800 rounded-xl font-mono text-[11px] text-slate-300 max-h-80 overflow-y-auto whitespace-pre-wrap">
                      {currentExport.file_content}
                    </pre>
                  </div>
                ) : null}

                {/* Modal Footer */}
                <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
                  <button
                    onClick={() => setExportModalOpen(false)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition"
                  >
                    Close
                  </button>
                  <button
                    onClick={handleDownloadExportFile}
                    disabled={!currentExport || exportLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md transition disabled:opacity-50"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Export File</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
