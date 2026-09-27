"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { getSite, getSiteTrends } from "@/lib/api";
import { Site, SiteTrendsResponse, TrendPoint } from "@/types/api";
import {
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  ArrowLeft,
  Calendar,
  Layers,
  RefreshCw,
  BarChart3,
  CheckCircle,
} from "lucide-react";

export default function SiteTrendsPage() {
  const params = useParams();
  const siteId = params.id as string;

  const [site, setSite] = useState<Site | null>(null);
  const [trends, setTrends] = useState<SiteTrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const [siteData, trendsData] = await Promise.all([
        getSite(siteId),
        getSiteTrends(siteId),
      ]);
      setSite(siteData);
      setTrends(trendsData);
    } catch (err: any) {
      setError(err.message || "Failed to load historical trend data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (siteId) {
      fetchTrends();
    }
  }, [siteId]);

  const issuePoints = trends?.trends?.issue_count || [];
  const oppPoints = trends?.trends?.opportunity_count || [];

  const latestIssue = issuePoints.length > 0 ? issuePoints[issuePoints.length - 1].value : null;
  const prevIssue = issuePoints.length > 1 ? issuePoints[issuePoints.length - 2].value : null;

  const latestOpp = oppPoints.length > 0 ? oppPoints[oppPoints.length - 1].value : null;
  const prevOpp = oppPoints.length > 1 ? oppPoints[oppPoints.length - 2].value : null;

  return (
    <ProtectedRoute>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between">
          <Link
            href="/sites"
            className="inline-flex items-center space-x-2 text-sm text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Monitored Sites</span>
          </Link>
          <div className="flex items-center space-x-3 text-xs text-slate-400">
            <span className="font-mono bg-slate-900 border border-slate-800 px-2 py-1 rounded">
              Site: {siteId}
            </span>
          </div>
        </div>

        {/* Header */}
        <div className="pb-6 border-b border-slate-800 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                <span>Historical Trends</span>
                {site && (
                  <span className="text-sm font-normal font-mono px-2.5 py-0.5 rounded-full bg-slate-800 text-sky-300 border border-slate-700">
                    {site.domain}
                  </span>
                )}
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                Time-series tracking of technical issue resolution and opportunity discovery trajectory.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => fetchTrends()}
              disabled={loading}
              className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="rounded-xl bg-rose-500/10 border border-rose-500/30 p-4 text-rose-300 text-sm flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Summary Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
              <span>Latest Issue Count</span>
              <AlertTriangle className="w-4 h-4 text-rose-400" />
            </div>
            <div className="mt-3 flex items-baseline space-x-3">
              <span className="text-3xl font-extrabold text-white">
                {latestIssue !== null ? latestIssue : "—"}
              </span>
              {prevIssue !== null && latestIssue !== null && (
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    latestIssue < prevIssue
                      ? "bg-emerald-500/20 text-emerald-400"
                      : latestIssue > prevIssue
                      ? "bg-rose-500/20 text-rose-400"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {latestIssue < prevIssue
                    ? `↓ ${prevIssue - latestIssue} resolved`
                    : latestIssue > prevIssue
                    ? `↑ ${latestIssue - prevIssue} new`
                    : "No change"}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-2">Active defects from latest crawl audit</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
              <span>Latest Opportunities</span>
              <Lightbulb className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-3 flex items-baseline space-x-3">
              <span className="text-3xl font-extrabold text-white">
                {latestOpp !== null ? latestOpp : "—"}
              </span>
              {prevOpp !== null && latestOpp !== null && (
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    latestOpp > prevOpp
                      ? "bg-emerald-500/20 text-emerald-400"
                      : latestOpp < prevOpp
                      ? "bg-slate-800 text-slate-400"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {latestOpp > prevOpp
                    ? `↑ ${latestOpp - prevOpp} discovered`
                    : latestOpp < prevOpp
                    ? `↓ ${prevOpp - latestOpp} actioned`
                    : "No change"}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-2">High-ICE impact recommendations identified</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
              <span>Audits Tracked</span>
              <BarChart3 className="w-4 h-4 text-sky-400" />
            </div>
            <div className="mt-3 flex items-baseline space-x-3">
              <span className="text-3xl font-extrabold text-white">
                {Math.max(issuePoints.length, oppPoints.length)}
              </span>
              <span className="text-xs text-slate-400">snapshots</span>
            </div>
            <p className="text-xs text-slate-500 mt-2">Completed crawl and audit data points</p>
          </div>
        </div>

        {/* Time-series Chart & History Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="border-b border-slate-800 pb-4 flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-sky-400" />
              <span>Metric Trajectory Over Time</span>
            </h2>
            <div className="flex items-center space-x-4 text-xs">
              <div className="flex items-center space-x-1.5">
                <span className="w-3 h-3 rounded-full bg-rose-500"></span>
                <span className="text-slate-300">Issue Count</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="w-3 h-3 rounded-full bg-amber-400"></span>
                <span className="text-slate-300">Opportunity Count</span>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3">
              <RefreshCw className="w-6 h-6 text-sky-400 animate-spin" />
              <span className="text-xs text-slate-400">Loading historical trend data...</span>
            </div>
          ) : issuePoints.length === 0 && oppPoints.length === 0 ? (
            <div className="py-16 px-4 rounded-xl bg-slate-950/40 border border-slate-800 text-center space-y-3">
              <div className="inline-flex p-3 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
                <TrendingUp className="w-8 h-8" />
              </div>
              <h3 className="text-sm font-bold text-white">No Historical Trend Data Yet</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Completed crawl audits for this site will automatically populate time-series issue counts and opportunity trajectories.
              </p>
              <div className="pt-2">
                <Link
                  href={`/runs/new?site_id=${siteId}`}
                  className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold transition"
                >
                  <span>Start Audit Run</span>
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Visual Data Points Row */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 overflow-x-auto">
                <div className="min-w-[600px] flex items-end justify-between gap-4 h-48 pt-6 px-4 border-b border-slate-800">
                  {issuePoints.map((pt, idx) => {
                    const oppPt = oppPoints[idx];
                    const maxVal = Math.max(
                      ...issuePoints.map((p) => p.value),
                      ...oppPoints.map((p) => p.value),
                      10
                    );
                    const issueHeight = Math.max(12, Math.round((pt.value / maxVal) * 140));
                    const oppHeight = oppPt ? Math.max(12, Math.round((oppPt.value / maxVal) * 140)) : 0;

                    return (
                      <div key={pt.id || idx} className="flex-1 flex flex-col items-center gap-2 group">
                        <div className="flex items-end gap-1.5 h-36">
                          {/* Issue bar */}
                          <div
                            style={{ height: `${issueHeight}px` }}
                            className="w-6 rounded-t bg-rose-500/80 hover:bg-rose-400 transition flex items-center justify-center relative cursor-pointer"
                            title={`Issues: ${pt.value} on ${pt.date}`}
                          >
                            <span className="text-[10px] font-bold text-white -top-5 absolute">
                              {pt.value}
                            </span>
                          </div>
                          {/* Opportunity bar */}
                          {oppPt && (
                            <div
                              style={{ height: `${oppHeight}px` }}
                              className="w-6 rounded-t bg-amber-400/80 hover:bg-amber-300 transition flex items-center justify-center relative cursor-pointer"
                              title={`Opportunities: ${oppPt.value} on ${oppPt.date}`}
                            >
                              <span className="text-[10px] font-bold text-slate-900 -top-5 absolute">
                                {oppPt.value}
                              </span>
                            </div>
                          )}
                        </div>
                        <span className="text-[11px] font-mono text-slate-400 truncate max-w-[80px]">
                          {pt.date}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Data Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/70 border-b border-slate-800 text-[11px] text-slate-400 uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Date</th>
                      <th className="py-3 px-4">Run ID</th>
                      <th className="py-3 px-4">Issue Count</th>
                      <th className="py-3 px-4">Opportunity Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {issuePoints.map((pt, i) => {
                      const opp = oppPoints[i];
                      return (
                        <tr key={pt.id || i} className="hover:bg-slate-800/30 transition">
                          <td className="py-3 px-4 text-slate-200">{pt.date}</td>
                          <td className="py-3 px-4 text-sky-400">
                            {pt.run_id ? (
                              <Link href={`/runs/${pt.run_id}`} className="hover:underline">
                                {pt.run_id}
                              </Link>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="py-3 px-4 text-rose-400 font-bold">{pt.value}</td>
                          <td className="py-3 px-4 text-amber-300 font-bold">{opp ? opp.value : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
