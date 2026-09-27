"use client";

import React, { useState, useEffect, useCallback, Fragment } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import RunNavTabs from "@/components/RunNavTabs";
import { getRunOpportunities, submitOpportunityFeedback, getRun } from "@/lib/api";
import { Opportunity, Run } from "@/types/api";
import {
  Lightbulb,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Filter,
  CheckCircle,
  XCircle,
  Clock,
  ArrowRight,
  AlertCircle,
  ThumbsUp,
  Ban,
  Check,
  Search,
} from "lucide-react";

export default function OpportunitiesPage() {
  const params = useParams();
  const runId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Sorting
  const [tierFilter, setTierFilter] = useState<string>("");
  const [confidenceFilter, setConfidenceFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("priority_score");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Expanded row IDs
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Feedback loading state
  const [submittingFeedback, setSubmittingFeedback] = useState<string | null>(null);

  const fetchOpps = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [oppsData, runData] = await Promise.all([
        getRunOpportunities(runId, {
          tier: tierFilter || undefined,
          confidence: confidenceFilter || undefined,
          type: typeFilter || undefined,
          search: searchQuery || undefined,
          sort_by: sortBy,
          order: sortOrder,
        }),
        getRun(runId),
      ]);
      setOpportunities(oppsData);
      setRun(runData);
    } catch (err: any) {
      setError(err.message || "Failed to load opportunities");
    } finally {
      setLoading(false);
    }
  }, [runId, tierFilter, confidenceFilter, typeFilter, searchQuery, sortBy, sortOrder]);

  useEffect(() => {
    fetchOpps();
  }, [fetchOpps]);

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleFeedback = async (
    opp: Opportunity,
    verdict: "fixed" | "false_positive" | "accepted" | "wont_fix"
  ) => {
    setSubmittingFeedback(opp.id);
    try {
      await submitOpportunityFeedback(opp.id, verdict);
      setOpportunities((prev) =>
        prev.map((item) =>
          item.id === opp.id || item.fingerprint === opp.fingerprint
            ? { ...item, feedback: verdict }
            : item
        )
      );
    } catch (err: any) {
      alert(err.message || "Failed to update feedback");
    } finally {
      setSubmittingFeedback(null);
    }
  };

  const getTierBadge = (tier?: string) => {
    switch (tier?.toLowerCase()) {
      case "tier1":
      case "tier 1":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-950 text-rose-300 border border-rose-800">Tier 1</span>;
      case "tier2":
      case "tier 2":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-950 text-amber-300 border border-amber-800">Tier 2</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300">Tier 3</span>;
    }
  };

  const getConfidenceBadge = (conf?: string) => {
    switch (conf?.toLowerCase()) {
      case "high":
        return <span className="text-emerald-400 font-medium text-xs">High</span>;
      case "medium":
        return <span className="text-amber-400 font-medium text-xs">Medium</span>;
      default:
        return <span className="text-slate-400 font-medium text-xs">Low</span>;
    }
  };

  const getFeedbackBadge = (fb?: string | null) => {
    if (!fb) return null;
    switch (fb.toLowerCase()) {
      case "fixed":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800 uppercase">Fixed</span>;
      case "false_positive":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-950 text-rose-300 border border-rose-800 uppercase">False Positive</span>;
      case "accepted":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-950 text-sky-300 border border-sky-800 uppercase">Accepted</span>;
      case "wont_fix":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 uppercase">Won&apos;t Fix</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400 uppercase">{fb}</span>;
    }
  };

  return (
    <ProtectedRoute>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
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
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                <Lightbulb className="w-6 h-6 text-amber-400" />
                <span>Opportunities Explorer</span>
              </h1>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Run ID: {runId} {run && `• Site: ${run.site_id}`}
              </p>
            </div>
          </div>

          <div className="mt-6">
            <RunNavTabs runId={runId} />
          </div>
        </div>

        {error && (
          <div className="rounded-lg bg-rose-500/10 border border-rose-500/30 p-4 text-rose-300 text-sm flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Filter & Search Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                placeholder="Search opportunities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 w-48 sm:w-60"
              />
            </div>

            <select
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none"
            >
              <option value="">All Tiers</option>
              <option value="tier1">Tier 1</option>
              <option value="tier2">Tier 2</option>
              <option value="tier3">Tier 3</option>
            </select>

            <select
              value={confidenceFilter}
              onChange={(e) => setConfidenceFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none"
            >
              <option value="">All Confidences</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-xs text-slate-500">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none"
            >
              <option value="priority_score">Priority Score</option>
              <option value="tier">Tier</option>
              <option value="effort">Effort</option>
              <option value="display_id">Display ID</option>
            </select>

            <button
              onClick={() => setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"))}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300 hover:text-white transition font-mono"
              title="Toggle sort direction"
            >
              {sortOrder.toUpperCase()}
            </button>
          </div>
        </div>

        {/* Opportunities Table */}
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm text-slate-400">Loading prioritized opportunities...</p>
          </div>
        ) : opportunities.length === 0 ? (
          <div className="border border-dashed border-slate-800 rounded-2xl p-12 text-center bg-slate-900/40">
            <Lightbulb className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white">No opportunities found</h3>
            <p className="text-sm text-slate-400 max-w-sm mx-auto mt-1">
              No opportunities match the current filter criteria or none were detected for this crawl run.
            </p>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3.5 w-12 text-center">#</th>
                    <th className="px-4 py-3.5">ID / Type</th>
                    <th className="px-4 py-3.5">Recommended Action</th>
                    <th className="px-4 py-3.5">Tier</th>
                    <th className="px-4 py-3.5">Confidence</th>
                    <th className="px-4 py-3.5">Score</th>
                    <th className="px-4 py-3.5">Feedback</th>
                    <th className="px-4 py-3.5 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {opportunities.map((opp) => {
                    const isExpanded = expandedIds.has(opp.id);
                    const factors = opp.factors_json || {};

                    return (
                      <React.Fragment key={opp.id}>
                        <tr className="hover:bg-slate-800/40 transition cursor-pointer" onClick={() => toggleExpand(opp.id)}>
                          <td className="px-4 py-4 text-center text-slate-500 font-mono text-xs">
                            {isExpanded ? <ChevronUp className="w-4 h-4 mx-auto" /> : <ChevronDown className="w-4 h-4 mx-auto" />}
                          </td>
                          <td className="px-4 py-4">
                            <span className="font-mono font-bold text-white block">{opp.display_id}</span>
                            <span className="text-[11px] text-slate-400 uppercase tracking-wider">{opp.type || "GENERIC"}</span>
                          </td>
                          <td className="px-4 py-4 max-w-md">
                            <p className="text-sm text-slate-200 line-clamp-2">{opp.action || opp.diagnosis || opp.observation}</p>
                            <span className="text-[11px] text-slate-500 block mt-0.5">
                              Affects {opp.affected_urls_count} URLs
                            </span>
                          </td>
                          <td className="px-4 py-4">{getTierBadge(opp.tier)}</td>
                          <td className="px-4 py-4">{getConfidenceBadge(opp.confidence)}</td>
                          <td className="px-4 py-4 font-mono font-bold text-sky-400">
                            {opp.priority_score ? Number(opp.priority_score).toFixed(1) : "—"}
                          </td>
                          <td className="px-4 py-4">
                            {getFeedbackBadge(opp.feedback) || <span className="text-xs text-slate-600">—</span>}
                          </td>
                          <td className="px-4 py-4 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleExpand(opp.id);
                              }}
                              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium transition"
                            >
                              {isExpanded ? "Close" : "Inspect"}
                            </button>
                          </td>
                        </tr>

                        {/* Expanded Diagnostic Chain & ICE Factors */}
                        {isExpanded && (
                          <tr className="bg-slate-950/80 border-t border-slate-800">
                            <td colSpan={8} className="p-6">
                              <div className="space-y-6">
                                {/* Diagnostic Reasoning Chain */}
                                <div>
                                  <h4 className="text-xs uppercase tracking-wider text-slate-400 font-bold mb-3">
                                    Root-Cause Diagnostic Chain
                                  </h4>
                                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
                                    <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="font-semibold text-sky-400 block mb-1">1. Observation</span>
                                      <p className="text-slate-300">{opp.observation || "None recorded"}</p>
                                    </div>

                                    <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="font-semibold text-amber-400 block mb-1">2. Evidence Provenance</span>
                                      <p className="text-slate-300">
                                        Location: <code className="text-slate-200">{opp.implementation_location || "Global"}</code>
                                      </p>
                                      {opp.sample_urls && opp.sample_urls.length > 0 && (
                                        <div className="mt-1 text-[11px] text-slate-400 truncate">
                                          Sample: {opp.sample_urls[0]}
                                        </div>
                                      )}
                                    </div>

                                    <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="font-semibold text-rose-400 block mb-1">3. Diagnosis</span>
                                      <p className="text-slate-300">{opp.diagnosis || "None recorded"}</p>
                                    </div>

                                    <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="font-semibold text-purple-400 block mb-1">4. Hypothesis</span>
                                      <p className="text-slate-300">{opp.hypothesis || "None recorded"}</p>
                                    </div>

                                    <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="font-semibold text-emerald-400 block mb-1">5. Recommended Action</span>
                                      <p className="text-slate-300">{opp.action || "None recorded"}</p>
                                    </div>

                                    <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="font-semibold text-blue-400 block mb-1">6. Verification Specification</span>
                                      <p className="text-slate-300 font-mono text-[11px]">{opp.verification_spec || "Standard crawl assertion"}</p>
                                    </div>
                                  </div>
                                </div>

                                {/* Actual ICE Factors */}
                                <div>
                                  <h4 className="text-xs uppercase tracking-wider text-slate-400 font-bold mb-3">
                                    Opportunity Engine ICE Factors
                                  </h4>
                                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 text-center">
                                    <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="text-[10px] text-slate-500 uppercase block">Visibility</span>
                                      <span className="text-sm font-bold text-white font-mono">{factors.visibility ?? "—"}</span>
                                    </div>
                                    <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="text-[10px] text-slate-500 uppercase block">Gap</span>
                                      <span className="text-sm font-bold text-white font-mono">{factors.gap ?? "—"}</span>
                                    </div>
                                    <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="text-[10px] text-slate-500 uppercase block">Page Importance</span>
                                      <span className="text-sm font-bold text-white font-mono">{factors.page_importance ?? "—"}</span>
                                    </div>
                                    <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="text-[10px] text-slate-500 uppercase block">Template Scope</span>
                                      <span className="text-sm font-bold text-white font-mono">{factors.template_scope ?? "—"}</span>
                                    </div>
                                    <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="text-[10px] text-slate-500 uppercase block">Tech Severity</span>
                                      <span className="text-sm font-bold text-white font-mono">{factors.technical_severity ?? "—"}</span>
                                    </div>
                                    <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="text-[10px] text-slate-500 uppercase block">CTR Headroom</span>
                                      <span className="text-sm font-bold text-white font-mono">{factors.ctr_headroom ?? "—"}</span>
                                    </div>
                                    <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                                      <span className="text-[10px] text-slate-500 uppercase block">Link Gap</span>
                                      <span className="text-sm font-bold text-white font-mono">{factors.link_gap ?? "—"}</span>
                                    </div>
                                  </div>
                                </div>

                                {/* Feedback Actions Bar */}
                                <div className="pt-4 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                                  <div className="text-xs text-slate-400">
                                    Current Verdict: <strong className="text-white">{opp.feedback ? opp.feedback.toUpperCase() : "UNREVIEWED"}</strong>
                                  </div>

                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="text-xs text-slate-500 mr-2">Set Feedback:</span>
                                    <button
                                      disabled={submittingFeedback === opp.id}
                                      onClick={() => handleFeedback(opp, "fixed")}
                                      className={`px-3 py-1 rounded text-xs font-semibold transition ${
                                        opp.feedback === "fixed"
                                          ? "bg-emerald-600 text-white"
                                          : "bg-slate-800 hover:bg-emerald-950 hover:text-emerald-300 text-slate-300"
                                      }`}
                                    >
                                      Fixed
                                    </button>

                                    <button
                                      disabled={submittingFeedback === opp.id}
                                      onClick={() => handleFeedback(opp, "false_positive")}
                                      className={`px-3 py-1 rounded text-xs font-semibold transition ${
                                        opp.feedback === "false_positive"
                                          ? "bg-rose-600 text-white"
                                          : "bg-slate-800 hover:bg-rose-950 hover:text-rose-300 text-slate-300"
                                      }`}
                                    >
                                      False Positive
                                    </button>

                                    <button
                                      disabled={submittingFeedback === opp.id}
                                      onClick={() => handleFeedback(opp, "accepted")}
                                      className={`px-3 py-1 rounded text-xs font-semibold transition ${
                                        opp.feedback === "accepted"
                                          ? "bg-sky-600 text-white"
                                          : "bg-slate-800 hover:bg-sky-950 hover:text-sky-300 text-slate-300"
                                      }`}
                                    >
                                      Accepted
                                    </button>

                                    <button
                                      disabled={submittingFeedback === opp.id}
                                      onClick={() => handleFeedback(opp, "wont_fix")}
                                      className={`px-3 py-1 rounded text-xs font-semibold transition ${
                                        opp.feedback === "wont_fix"
                                          ? "bg-slate-700 text-white"
                                          : "bg-slate-800 hover:bg-slate-700 text-slate-400"
                                      }`}
                                    >
                                      Won&apos;t Fix
                                    </button>
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
