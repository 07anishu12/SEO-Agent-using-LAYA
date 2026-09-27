"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import RunNavTabs from "@/components/RunNavTabs";
import { getBlueprintDetail, getRun } from "@/lib/api";
import { BlueprintDetail, Run } from "@/types/api";
import {
  FileCode,
  ArrowLeft,
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Layers,
  Link2,
  Cpu,
  Sparkles,
  Bot,
  ExternalLink,
  Code,
} from "lucide-react";

function BlueprintDetailContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const runId = params.id as string;
  const targetUrl = searchParams.get("url") || "";

  const [run, setRun] = useState<Run | null>(null);
  const [data, setData] = useState<BlueprintDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"dimensions" | "markdown">("dimensions");

  const fetchBlueprint = useCallback(async () => {
    if (!targetUrl) return;
    setLoading(true);
    setError(null);
    try {
      const [bpData, rData] = await Promise.all([
        getBlueprintDetail(runId, targetUrl),
        getRun(runId),
      ]);
      setData(bpData);
      setRun(rData);
    } catch (err: any) {
      setError(err.message || "Failed to load blueprint details");
    } finally {
      setLoading(false);
    }
  }, [runId, targetUrl]);

  useEffect(() => {
    fetchBlueprint();
  }, [fetchBlueprint]);

  const bp = data?.blueprint || {};
  const d1Identity = bp.dimension_1_identity || {};
  const d2Template = bp.dimension_2_template || {};
  const d3Indexation = bp.dimension_3_indexation || {};
  const d4Intent = bp.dimension_4_search_intent || {};
  const d5Queries = bp.dimension_5_target_queries || [];
  const d6Meta = bp.dimension_6_core_metadata || {};
  const d7Headings = bp.dimension_7_heading_outline || {};
  const d8Entities = bp.dimension_8_entity_coverage || {};
  const d9Gaps = bp.dimension_9_content_gaps || [];
  const d10Schema = bp.dimension_10_structured_data || {};
  const d11Inlinks = bp.dimension_11_internal_links_in || [];
  const d12Outlinks = bp.dimension_12_internal_links_out || [];
  const d13RecInlinks = bp.dimension_13_recommended_inbound_links || [];
  const d16Aeo = bp.dimension_16_aeo_readiness || {};
  const d17Geo = bp.dimension_17_geo_readiness || {};
  const d20WorkOrders = bp.dimension_20_touching_work_orders || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div>
        <Link
          href={`/runs/${runId}/blueprints`}
          className="inline-flex items-center space-x-2 text-sm text-slate-400 hover:text-white transition mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Blueprints Index</span>
        </Link>

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-xl font-bold tracking-tight text-white font-mono flex items-center gap-2">
                <FileCode className="w-6 h-6 text-purple-400" />
                <span className="truncate max-w-xl" title={targetUrl}>{targetUrl}</span>
              </h1>
            </div>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Run ID: {runId} {run && `• Site: ${run.site_id}`}
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab("dimensions")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                activeTab === "dimensions"
                  ? "bg-purple-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Diagnostic Dimensions
            </button>
            <button
              onClick={() => setActiveTab("markdown")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                activeTab === "markdown"
                  ? "bg-purple-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Raw Blueprint Markdown
            </button>
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

      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm text-slate-400">Synthesizing 20-dimension blueprint from crawl data...</p>
        </div>
      ) : !data ? (
        <div className="text-center py-12 text-slate-500 text-sm">
          Blueprint data could not be generated.
        </div>
      ) : activeTab === "markdown" ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed overflow-x-auto">
            {data.markdown || "No markdown rendered."}
          </pre>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-500 uppercase font-semibold">Template ID</span>
              <div className="text-lg font-bold text-white mt-1 font-mono">
                {d2Template.template_id || "—"}
              </div>
              <span className="text-[10px] text-slate-400">{d2Template.page_type || "GENERIC"}</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-500 uppercase font-semibold">Indexability</span>
              <div className="text-lg font-bold mt-1">
                {d3Indexation.is_indexable ? (
                  <span className="text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" /> Indexable
                  </span>
                ) : (
                  <span className="text-rose-400 flex items-center gap-1">
                    <XCircle className="w-4 h-4" /> Blocked
                  </span>
                )}
              </div>
              <span className="text-[10px] text-slate-400 font-mono truncate block">{d3Indexation.meta_robots || "index, follow"}</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-500 uppercase font-semibold">Entity Coverage</span>
              <div className="text-lg font-bold text-sky-400 mt-1 font-mono">
                {d8Entities.coverage_score_pct !== undefined ? `${d8Entities.coverage_score_pct}%` : "—"}
              </div>
              <span className="text-[10px] text-slate-400">{d8Entities.extracted_count || 0} attributes extracted</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-500 uppercase font-semibold">AEO Extractability</span>
              <div className="text-lg font-bold text-purple-400 mt-1 font-mono">
                {d16Aeo.extractability_score !== undefined ? `${d16Aeo.extractability_score}/100` : "—"}
              </div>
              <span className="text-[10px] text-slate-400">GEO Structural: {d17Geo.structural_readiness_score || 0}/100</span>
            </div>
          </div>

          {/* Section 1: Search Intent & Target Queries */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider text-sky-400 flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              <span>Query Fit & Search Intent</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                <span className="text-slate-400 block font-semibold">Primary Search Intent</span>
                <p className="text-white font-medium text-sm">{d4Intent.primary_intent || "Commercial / Informational"}</p>
                <p className="text-slate-400">
                  Landing Page Fit: <strong className="text-emerald-300">{d4Intent.landing_page_fit_verdict || "CORRECT_LANDING"}</strong>
                </p>
              </div>

              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                <span className="text-slate-400 block font-semibold">Target Queries ({d5Queries.length})</span>
                {d5Queries.length === 0 ? (
                  <p className="text-slate-500">No targeted queries mapped in crawl index.</p>
                ) : (
                  <ul className="space-y-1">
                    {d5Queries.slice(0, 5).map((q: any, i: number) => (
                      <li key={i} className="text-slate-200 font-mono text-[11px]">
                        • {typeof q === "string" ? q : q.query || JSON.stringify(q)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>

          {/* Section 2: Core Metadata & Entity Coverage */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider text-purple-400">
                Core Metadata & Headings
              </h3>
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-500 font-semibold block">Title Tag</span>
                  <p className="text-slate-200 font-medium">{d6Meta.title || "—"}</p>
                </div>
                <div>
                  <span className="text-slate-500 font-semibold block">Meta Description</span>
                  <p className="text-slate-300">{d6Meta.description || "—"}</p>
                </div>
                <div>
                  <span className="text-slate-500 font-semibold block">Primary H1</span>
                  <p className="text-slate-200 font-medium">{d7Headings.h1?.[0] || d6Meta.h1_text || "—"}</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider text-emerald-400">
                Extracted Entities & Specifications
              </h3>
              <div className="space-y-2 text-xs max-h-56 overflow-y-auto">
                {d8Entities.attributes && d8Entities.attributes.length > 0 ? (
                  <table className="w-full text-left">
                    <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                      {d8Entities.attributes.map((attr: any, i: number) => (
                        <tr key={i}>
                          <td className="py-1 text-slate-400">{attr.attribute_name}</td>
                          <td className="py-1 text-white font-semibold text-right">{attr.attribute_value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="text-slate-500 text-xs py-4">No structured entity specifications extracted.</p>
                )}
              </div>
            </div>
          </div>

          {/* Section 3: Structured Data & Internal Links */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider text-sky-400">
                Structured Data Schema
              </h3>
              <div className="text-xs space-y-2">
                <p className="text-slate-300">
                  Status:{" "}
                  <strong className={d10Schema.is_valid ? "text-emerald-400" : "text-amber-400"}>
                    {d10Schema.is_valid ? "Valid Structured Data" : "Missing / Needs Validation"}
                  </strong>
                </p>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {d10Schema.types && d10Schema.types.length > 0 ? (
                    d10Schema.types.map((st: string, idx: number) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-sky-300">
                        {st}
                      </span>
                    ))
                  ) : (
                    <span className="text-slate-500 text-xs">No Schema.org markup identified.</span>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider text-amber-400">
                Internal Link Graph Signals
              </h3>
              <div className="text-xs space-y-2">
                <div className="flex items-center justify-between text-slate-300">
                  <span>Inbound Links Count:</span>
                  <span className="font-mono font-bold text-white">{d11Inlinks.length}</span>
                </div>
                <div className="flex items-center justify-between text-slate-300">
                  <span>Outbound Links Count:</span>
                  <span className="font-mono font-bold text-white">{d12Outlinks.length}</span>
                </div>
                <div className="flex items-center justify-between text-slate-300">
                  <span>Recommended Inlink Targets:</span>
                  <span className="font-mono font-bold text-sky-400">{d13RecInlinks.length}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 4: Exact Actions & Touching Work Orders */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-3">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider text-rose-400">
              Touching Work Orders & Optimization Actions ({d20WorkOrders.length})
            </h3>
            {d20WorkOrders.length === 0 ? (
              <p className="text-xs text-slate-500">No active work orders pending for this page.</p>
            ) : (
              <div className="divide-y divide-slate-800 border border-slate-800 rounded-lg overflow-hidden">
                {d20WorkOrders.map((wo: any, idx: number) => (
                  <div key={idx} className="p-3 bg-slate-950/60 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-mono font-bold text-sky-400 mr-2">{wo.display_id || wo.id}</span>
                      <span className="text-slate-200">{wo.title || wo.required_change}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-slate-800 text-slate-300 font-mono">
                      {wo.order_type || "TECH"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function BlueprintDetailPage() {
  return (
    <ProtectedRoute>
      <Suspense
        fallback={
          <div className="py-16 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        }
      >
        <BlueprintDetailContent />
      </Suspense>
    </ProtectedRoute>
  );
}
