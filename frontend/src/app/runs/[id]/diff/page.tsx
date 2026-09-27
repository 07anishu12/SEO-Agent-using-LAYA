"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import RunNavTabs from "@/components/RunNavTabs";
import { getRunDiff } from "@/lib/api";
import { SnapshotDiffResponse, SnapshotDiffItem, CompareTarget } from "@/types/api";
import {
  GitCompare,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Layers,
  ExternalLink,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  ArrowRight,
  TrendingUp,
  AlertCircle
} from "lucide-react";

export default function SnapshotDiffPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const runId = params.id as string;

  const compareQuery = searchParams.get("compare_run_id");

  const [diffData, setDiffData] = useState<SnapshotDiffResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [searchUrl, setSearchUrl] = useState("");
  const [selectedTarget, setSelectedTarget] = useState<string>(compareQuery || "");
  const [expandedTemplates, setExpandedTemplates] = useState<Record<string, boolean>>({});

  const fetchDiff = useCallback(async (compareId?: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRunDiff(runId, compareId || undefined);
      setDiffData(data);
      if (data.before_run_id && !selectedTarget) {
        setSelectedTarget(data.before_run_id);
      }
      // Expand all templates by default
      const exp: Record<string, boolean> = {};
      Object.keys(data.by_template || {}).forEach((t) => {
        exp[t] = true;
      });
      setExpandedTemplates(exp);
    } catch (err: any) {
      setError(err.message || "Failed to load snapshot diff");
    } finally {
      setLoading(false);
    }
  }, [runId, selectedTarget]);

  useEffect(() => {
    fetchDiff(compareQuery || undefined);
  }, [fetchDiff, compareQuery]);

  const handleSelectCompare = (newTarget: string) => {
    setSelectedTarget(newTarget);
    router.push(`/runs/${runId}/diff?compare_run_id=${encodeURIComponent(newTarget)}`);
    fetchDiff(newTarget);
  };

  const toggleTemplate = (tpl: string) => {
    setExpandedTemplates((prev) => ({
      ...prev,
      [tpl]: !prev[tpl]
    }));
  };

  const getCategoryBadge = (category: string) => {
    switch (category.toUpperCase()) {
      case "FIXED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            Fixed
          </span>
        );
      case "REGRESSED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Regressed
          </span>
        );
      case "NEW_ISSUE":
      case "NEW":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            New
          </span>
        );
      case "IMPROVED":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-500/10 text-sky-400 border border-sky-500/30 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            Improved
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-800 text-slate-400">
            {category}
          </span>
        );
    }
  };

  const summary = diffData?.summary || {
    FIXED: 0,
    REGRESSED: 0,
    IMPROVED: 0,
    NEW_ISSUE: 0,
    STILL_FAILING: 0,
    UNCHANGED: 0
  };

  // Filter items by category & search
  const filterItem = (item: SnapshotDiffItem) => {
    const matchesCategory =
      selectedCategory === "ALL" ||
      (selectedCategory === "FIXED" && item.category === "FIXED") ||
      (selectedCategory === "REGRESSED" && item.category === "REGRESSED") ||
      (selectedCategory === "NEW" && (item.category === "NEW_ISSUE" || (item.category as string) === "NEW")) ||
      (selectedCategory === "IMPROVED" && item.category === "IMPROVED");

    const matchesSearch = item.url.toLowerCase().includes(searchUrl.toLowerCase());
    return matchesCategory && matchesSearch;
  };

  const templatesWithDiffs = Object.keys(diffData?.by_template || {}).filter((tpl) => {
    const items = diffData?.by_template[tpl] || [];
    return items.some(filterItem);
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
                <span className="text-sky-400 font-medium">Snapshot Diff</span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                <GitCompare className="w-6 h-6 text-sky-400" />
                Snapshot Diff Viewer
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Deterministic pre vs post deployment verification powered by the engine diff pipeline.
              </p>
            </div>

            {/* Run comparison selector */}
            {diffData?.compare_targets && diffData.compare_targets.length > 0 && (
              <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg p-2">
                <span className="text-xs text-slate-400">Compare with:</span>
                <select
                  value={selectedTarget}
                  onChange={(e) => handleSelectCompare(e.target.value)}
                  className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-sky-500 font-mono"
                >
                  {diffData.compare_targets.map((target) => (
                    <option key={target.id} value={target.id}>
                      {target.id} ({target.status})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Navigation Tabs */}
          <RunNavTabs runId={runId} />

          {/* Before & After Run Identity */}
          {diffData && diffData.before_run_id && (
            <div className="flex items-center gap-3 p-3 bg-slate-900/60 border border-slate-800 rounded-xl text-xs">
              <span className="text-slate-400">Baseline (Before):</span>
              <span className="font-mono text-sky-400 font-semibold">{diffData.before_run_id}</span>
              <ArrowRight className="w-4 h-4 text-slate-600" />
              <span className="text-slate-400">Deployment (After):</span>
              <span className="font-mono text-indigo-400 font-semibold">{diffData.after_run_id}</span>
              <span className="ml-auto text-slate-500">
                {diffData.total_urls_compared} URLs evaluated
              </span>
            </div>
          )}

          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div
              onClick={() => setSelectedCategory("FIXED")}
              className={`cursor-pointer rounded-xl p-4 border transition ${
                selectedCategory === "FIXED"
                  ? "bg-emerald-950/40 border-emerald-500/50 shadow-sm"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Fixed</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <p data-testid="fixed-count" className="text-2xl font-bold text-emerald-400 mt-2">
                {loading && !diffData ? "..." : summary.FIXED}
              </p>
              <span className="text-[11px] text-slate-500">Defects resolved</span>
            </div>

            <div
              onClick={() => setSelectedCategory("REGRESSED")}
              className={`cursor-pointer rounded-xl p-4 border transition ${
                selectedCategory === "REGRESSED"
                  ? "bg-rose-950/40 border-rose-500/50 shadow-sm"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Regressed</span>
                <AlertTriangle className="w-4 h-4 text-rose-400" />
              </div>
              <p data-testid="regressed-count" className="text-2xl font-bold text-rose-400 mt-2">
                {loading && !diffData ? "..." : summary.REGRESSED}
              </p>
              <span className="text-[11px] text-slate-500">Issues introduced</span>
            </div>

            <div
              onClick={() => setSelectedCategory("NEW")}
              className={`cursor-pointer rounded-xl p-4 border transition ${
                selectedCategory === "NEW"
                  ? "bg-amber-950/40 border-amber-500/50 shadow-sm"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">New</span>
                <AlertCircle className="w-4 h-4 text-amber-400" />
              </div>
              <p data-testid="new-count" className="text-2xl font-bold text-amber-400 mt-2">
                {loading && !diffData ? "..." : summary.NEW_ISSUE}
              </p>
              <span className="text-[11px] text-slate-500">New error pages</span>
            </div>

            <div
              onClick={() => setSelectedCategory("IMPROVED")}
              className={`cursor-pointer rounded-xl p-4 border transition ${
                selectedCategory === "IMPROVED"
                  ? "bg-sky-950/40 border-sky-500/50 shadow-sm"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Improved</span>
                <TrendingUp className="w-4 h-4 text-sky-400" />
              </div>
              <p data-testid="improved-count" className="text-2xl font-bold text-sky-400 mt-2">
                {loading && !diffData ? "..." : summary.IMPROVED}
              </p>
              <span className="text-[11px] text-slate-500">Positive content/schema lifts</span>
            </div>
          </div>

          {/* Filter Pills & Search */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800/80">
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400">Category:</span>
              <div className="flex flex-wrap gap-1">
                {[
                  { id: "ALL", label: "All Differences" },
                  { id: "FIXED", label: `Fixed (${summary.FIXED})` },
                  { id: "REGRESSED", label: `Regressed (${summary.REGRESSED})` },
                  { id: "NEW", label: `New (${summary.NEW_ISSUE})` },
                  { id: "IMPROVED", label: `Improved (${summary.IMPROVED})` },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-2.5 py-1 text-xs rounded-md font-medium transition ${
                      selectedCategory === cat.id
                        ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                        : "text-slate-400 hover:text-white hover:bg-slate-800"
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search affected URL..."
                value={searchUrl}
                onChange={(e) => setSearchUrl(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition"
              />
            </div>
          </div>

          {/* Grouped by Template List */}
          {loading ? (
            <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
              <RefreshCw className="w-6 h-6 animate-spin text-sky-400" />
              <p className="text-sm">Comparing pre and post deployment snapshot signatures...</p>
            </div>
          ) : error ? (
            <div className="p-6 bg-red-950/30 border border-red-800/50 rounded-xl text-red-300 text-sm">
              {error}
            </div>
          ) : !diffData || !diffData.before_run_id ? (
            <div className="p-12 text-center text-slate-500 border border-slate-800/60 rounded-xl bg-slate-900/20">
              <GitCompare className="w-8 h-8 mx-auto text-slate-600 mb-2" />
              <p className="text-sm text-slate-300 font-medium">No previous snapshot run available</p>
              <p className="text-xs text-slate-500 mt-1">
                At least two snapshot runs are required to compute regression and fix diffs.
              </p>
            </div>
          ) : templatesWithDiffs.length === 0 ? (
            <div className="p-12 text-center text-slate-400 border border-slate-800/60 rounded-xl bg-slate-900/20">
              <ShieldCheck className="w-10 h-10 mx-auto text-emerald-400 mb-2" />
              <p className="text-sm text-white font-semibold">Zero Regressions Detected</p>
              <p className="text-xs text-slate-400 mt-1">
                No differences found matching your filter criteria across {diffData.total_urls_compared} compared URLs.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {templatesWithDiffs.map((tpl) => {
                const items = (diffData.by_template[tpl] || []).filter(filterItem);
                const isExpanded = expandedTemplates[tpl] !== false;

                const fixedCount = items.filter((i) => i.category === "FIXED").length;
                const regressedCount = items.filter((i) => i.category === "REGRESSED").length;
                const newCount = items.filter((i) => i.category === "NEW_ISSUE" || (i.category as string) === "NEW").length;
                const improvedCount = items.filter((i) => i.category === "IMPROVED").length;

                return (
                  <div
                    key={tpl}
                    className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm"
                  >
                    {/* Template Section Header */}
                    <div
                      onClick={() => toggleTemplate(tpl)}
                      className="p-4 bg-slate-950/60 border-b border-slate-800/80 flex items-center justify-between cursor-pointer hover:bg-slate-900/60 transition"
                    >
                      <div className="flex items-center gap-3">
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-slate-400" />
                        )}
                        <Layers className="w-4 h-4 text-sky-400" />
                        <span className="font-mono text-sm font-semibold text-slate-200">
                          {tpl}
                        </span>
                        <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-slate-800 text-slate-300">
                          {items.length} {items.length === 1 ? "page" : "pages"} changed
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {fixedCount > 0 && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            {fixedCount} Fixed
                          </span>
                        )}
                        {regressedCount > 0 && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                            {regressedCount} Regressed
                          </span>
                        )}
                        {newCount > 0 && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                            {newCount} New
                          </span>
                        )}
                        {improvedCount > 0 && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/10 text-sky-400 border border-sky-500/30">
                            {improvedCount} Improved
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Template Changed Items */}
                    {isExpanded && (
                      <div className="divide-y divide-slate-800/60">
                        {items.map((item, idx) => {
                          const fixes: string[] = item.details?.fixes || [];
                          const regressions: string[] = item.details?.regressions || [];
                          const improvements: string[] = item.details?.improvements || [];
                          const event: string = item.details?.event || "";

                          return (
                            <div key={idx} className="p-4 hover:bg-slate-850/40 transition space-y-2">
                              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                                <div className="flex items-center gap-2.5">
                                  {getCategoryBadge(item.category)}
                                  <a
                                    href={item.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="font-mono text-xs text-sky-400 hover:text-sky-300 hover:underline flex items-center gap-1 truncate max-w-xl"
                                  >
                                    <span>{item.url}</span>
                                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                                  </a>
                                </div>

                                <div className="text-[11px] font-mono text-slate-500">
                                  FP: {item.fingerprint}
                                </div>
                              </div>

                              {/* Details content */}
                              <div className="pl-6 space-y-1 text-xs">
                                {fixes.length > 0 && (
                                  <div className="space-y-0.5">
                                    {fixes.map((f, i) => (
                                      <div key={i} className="text-emerald-300 flex items-center gap-1.5">
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                                        <span>{f}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {regressions.length > 0 && (
                                  <div className="space-y-0.5">
                                    {regressions.map((r, i) => (
                                      <div key={i} className="text-rose-300 flex items-center gap-1.5">
                                        <AlertTriangle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                                        <span>{r}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {improvements.length > 0 && (
                                  <div className="space-y-0.5">
                                    {improvements.map((im, i) => (
                                      <div key={i} className="text-sky-300 flex items-center gap-1.5">
                                        <TrendingUp className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
                                        <span>{im}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {event && (
                                  <p className="text-slate-300 text-xs italic">
                                    {event}
                                  </p>
                                )}

                                <div className="text-[11px] text-slate-500 flex gap-4 pt-1">
                                  <span>Before Snap: {item.before_snapshot_id}</span>
                                  <span>After Snap: {item.after_snapshot_id}</span>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
