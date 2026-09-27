"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import RunNavTabs from "@/components/RunNavTabs";
import { getRunGsc, importRunGsc, getRun } from "@/lib/api";
import { GscData, Run } from "@/types/api";
import {
  BarChart3,
  ArrowLeft,
  Search,
  Upload,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Layers,
  ArrowUpRight,
  ExternalLink,
  CheckCircle2,
} from "lucide-react";

export default function GscAnalysisPage() {
  const params = useParams();
  const runId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [data, setData] = useState<GscData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [importing, setImporting] = useState<boolean>(false);

  const fetchGsc = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [gData, rData] = await Promise.all([
        getRunGsc(runId),
        getRun(runId),
      ]);
      setData(gData);
      setRun(rData);
    } catch (err: any) {
      setError(err.message || "Failed to load GSC search analytics");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchGsc();
  }, [fetchGsc]);

  const handleGenerateSynthetic = async () => {
    setImporting(true);
    try {
      await importRunGsc(runId, { generate_synthetic: true });
      await fetchGsc();
    } catch (err: any) {
      alert(err.message || "Failed to generate synthetic GSC dataset");
    } finally {
      setImporting(false);
    }
  };

  const maxImpression = Math.max(
    ...(data?.impression_trends?.map((t) => t.impressions || 0) || [1]),
    1
  );
  const maxClick = Math.max(
    ...(data?.click_trends?.map((t) => t.clicks || 0) || [1]),
    1
  );

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
                <BarChart3 className="w-6 h-6 text-sky-400" />
                <span>Search Console & Query Intelligence</span>
              </h1>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Run ID: {runId} {run && `• Site: ${run.site_id}`}
              </p>
            </div>

            {(!data || !data.has_data) && (
              <button
                onClick={handleGenerateSynthetic}
                disabled={importing}
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-md transition disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4" />
                <span>{importing ? "Importing Search Data..." : "Load Sample GSC Dataset"}</span>
              </button>
            )}
          </div>

          <div className="mt-6">
            <RunNavTabs runId={runId} />
          </div>
        </div>

        {error && (
          <div className="rounded-lg bg-rose-500/10 border border-rose-500/30 p-4 text-rose-300 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm text-slate-400">Loading Search Console performance data...</p>
          </div>
        ) : !data || !data.has_data ? (
          /* Explicit Clean Empty State */
          <div className="border border-dashed border-slate-800 rounded-2xl p-12 text-center bg-slate-900/40">
            <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-white">Ranking Data Unavailable</h3>
            <p className="text-sm text-slate-400 max-w-md mx-auto mt-1 mb-6">
              Google Search Console performance data has not been connected for this run. Connect real search performance or import a synthetic test dataset to analyze striking-distance queries and cannibalization.
            </p>
            <button
              onClick={handleGenerateSynthetic}
              disabled={importing}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-md transition disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>{importing ? "Ingesting Data..." : "Connect Sample Search Data"}</span>
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Aggregate Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Total Queries
                </span>
                <div className="text-2xl font-bold text-white mt-1 font-mono">
                  {data.total_queries.toLocaleString()}
                </div>
                <span className="text-[11px] text-slate-500">Search phrases</span>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Organic Clicks
                </span>
                <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">
                  {data.total_clicks.toLocaleString()}
                </div>
                <span className="text-[11px] text-slate-500">Tracked clicks</span>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Impressions
                </span>
                <div className="text-2xl font-bold text-sky-400 mt-1 font-mono">
                  {data.total_impressions.toLocaleString()}
                </div>
                <span className="text-[11px] text-slate-500">SERP appearances</span>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Avg Position
                </span>
                <div className="text-2xl font-bold text-purple-400 mt-1 font-mono">
                  {data.avg_position}
                </div>
                <span className="text-[11px] text-slate-500">Mean SERP rank</span>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Striking Distance
                </span>
                <div className="text-2xl font-bold text-amber-400 mt-1 font-mono">
                  {data.striking_distance_count}
                </div>
                <span className="text-[11px] text-slate-500">Positions 11–20</span>
              </div>
            </div>

            {/* Real Search Trend Charts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Impression Distribution Chart */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-sky-400" />
                  <span>Impression Trends by Ranking Bracket</span>
                </h3>
                <div className="space-y-3">
                  {data.impression_trends.map((t, idx) => {
                    const widthPct = Math.round(((t.impressions || 0) / maxImpression) * 100);
                    return (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between text-xs text-slate-300">
                          <span className="font-medium">{t.bracket}</span>
                          <span className="font-mono text-sky-400">
                            {(t.impressions || 0).toLocaleString()} imp ({t.query_count} queries)
                          </span>
                        </div>
                        <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                          <div
                            className="bg-sky-500 h-full rounded-full transition-all duration-500"
                            style={{ width: `${Math.max(5, widthPct)}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Click Distribution Chart */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  <span>Click Trends by Ranking Bracket</span>
                </h3>
                <div className="space-y-3">
                  {data.click_trends.map((t, idx) => {
                    const widthPct = Math.round(((t.clicks || 0) / maxClick) * 100);
                    return (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between text-xs text-slate-300">
                          <span className="font-medium">{t.bracket}</span>
                          <span className="font-mono text-emerald-400">
                            {(t.clicks || 0).toLocaleString()} clicks ({t.query_count} queries)
                          </span>
                        </div>
                        <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                          <div
                            className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                            style={{ width: `${Math.max(5, widthPct)}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Striking-Distance Queries Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white">
                    Striking-Distance Opportunities (Positions 11–20)
                  </h3>
                  <p className="text-xs text-slate-400">
                    High-impression queries ranking on page 2 capable of rapid traffic growth with content or link updates.
                  </p>
                </div>
                <span className="px-2.5 py-1 rounded bg-amber-950 text-amber-300 text-xs font-mono font-bold border border-amber-800">
                  {data.striking_distance_queries.length} Targets
                </span>
              </div>

              <div className="overflow-x-auto border border-slate-800 rounded-xl">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 uppercase font-semibold text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="px-4 py-3">Search Query</th>
                      <th className="px-4 py-3">Ranking Page URL</th>
                      <th className="px-4 py-3">Position</th>
                      <th className="px-4 py-3">Impressions</th>
                      <th className="px-4 py-3">Clicks</th>
                      <th className="px-4 py-3">CTR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 font-mono">
                    {data.striking_distance_queries.map((q, idx) => (
                      <tr key={idx} className="hover:bg-slate-850">
                        <td className="px-4 py-3 font-semibold text-white">{q.query}</td>
                        <td className="px-4 py-3 text-slate-400 truncate max-w-xs" title={q.url}>{q.url}</td>
                        <td className="px-4 py-3 font-bold text-amber-400">{q.position.toFixed(1)}</td>
                        <td className="px-4 py-3 text-sky-400">{q.impressions.toLocaleString()}</td>
                        <td className="px-4 py-3 text-emerald-400">{q.clicks}</td>
                        <td className="px-4 py-3 text-slate-400">{(q.ctr * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Cannibalization Evidence Section */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-rose-400" />
                    <span>Keyword Cannibalization Evidence</span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Queries where multiple distinct pages compete in Google results, causing split clicks and rank instability.
                  </p>
                </div>
                <span className="px-2.5 py-1 rounded bg-rose-950 text-rose-300 text-xs font-mono font-bold border border-rose-800">
                  {data.cannibalization_queries.length} Competing Queries
                </span>
              </div>

              {data.cannibalization_queries.length === 0 ? (
                <div className="p-4 bg-slate-950 rounded-lg text-xs text-emerald-400">
                  ✓ No severe keyword cannibalization detected across tracked search queries.
                </div>
              ) : (
                <div className="space-y-3">
                  {data.cannibalization_queries.map((cq, idx) => (
                    <div key={idx} className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-white">&quot;{cq.query}&quot;</span>
                        <span className="text-xs text-rose-400 font-mono font-semibold">
                          {cq.pages_count} Competing URLs ({cq.total_impressions.toLocaleString()} imp)
                        </span>
                      </div>
                      <div className="divide-y divide-slate-850 border border-slate-800 rounded-lg overflow-hidden">
                        {cq.pages.map((p, pIdx) => (
                          <div key={pIdx} className="p-2.5 flex items-center justify-between text-xs font-mono bg-slate-900/60">
                            <span className="text-slate-300 truncate max-w-md" title={p.url}>{p.url}</span>
                            <div className="flex items-center space-x-4 flex-shrink-0">
                              <span className="text-slate-400">Pos: <strong className="text-white">{p.position.toFixed(1)}</strong></span>
                              <span className="text-sky-400">{p.impressions} imp</span>
                              <span className="text-emerald-400">{p.clicks} clicks</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Query Clusters */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-purple-400" />
                <span>Intent & Search Query Clusters</span>
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {data.query_clusters.map((c, idx) => (
                  <div key={idx} className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-sm capitalize">{c.cluster_name}</span>
                      <span className="font-mono text-purple-400 font-bold">{c.query_count} queries</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-400 font-mono text-[11px] pt-1">
                      <span>{c.impressions.toLocaleString()} imp</span>
                      <span>{c.clicks.toLocaleString()} clicks</span>
                      <span>Avg Pos: {c.avg_position}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
