"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import { getRuns } from "@/lib/api";
import { Run } from "@/types/api";
import {
  History,
  Play,
  ArrowRight,
  Clock,
  CheckCircle2,
  RefreshCw,
  XCircle,
  Square,
  Filter,
} from "lucide-react";

function RunsHistoryTable() {
  const searchParams = useSearchParams();
  const siteFilter = searchParams.get("site_id");

  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRuns(siteFilter || undefined);
      setRuns(data);
    } catch (err: any) {
      setError(err.message || "Failed to load runs history");
    } finally {
      setLoading(false);
    }
  }, [siteFilter]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "queued":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            <Clock className="w-3 h-3" />
            Queued
          </span>
        );
      case "running":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-950 text-sky-300 border border-sky-800 animate-pulse">
            <RefreshCw className="w-3 h-3 animate-spin" />
            Running
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
            <CheckCircle2 className="w-3 h-3" />
            Completed
          </span>
        );
      case "cancelled":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <Square className="w-3 h-3" />
            Cancelled
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950 text-rose-300 border border-rose-800">
            <XCircle className="w-3 h-3" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <History className="w-6 h-6 text-sky-400" />
            <span>Audit Runs History</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            View audit execution logs, real-time progress, and downloadable reports
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {siteFilter && (
            <Link
              href="/runs"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
            >
              <Filter className="w-3.5 h-3.5" />
              <span>Clear Site Filter</span>
            </Link>
          )}
          <Link
            href="/runs/new"
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold shadow-md shadow-sky-600/20 transition"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>New Run</span>
          </Link>
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
          <p className="text-sm text-slate-400">Loading audit history...</p>
        </div>
      ) : runs.length === 0 ? (
        <div className="border border-dashed border-slate-800 rounded-2xl p-12 text-center bg-slate-900/40">
          <History className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-white">No audit runs found</h3>
          <p className="text-sm text-slate-400 max-w-sm mx-auto mt-1 mb-6">
            Launch your first technical SEO crawl to generate root-cause opportunities and work orders.
          </p>
          <Link
            href="/runs/new"
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold transition"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>Start First Run</span>
          </Link>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-4">Run Identifier</th>
                  <th className="px-6 py-4">Site ID</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Current Pass</th>
                  <th className="px-6 py-4">Progress</th>
                  <th className="px-6 py-4">Crawled / Issues</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-6 py-4 font-mono font-medium text-white">
                      <Link href={`/runs/${r.id}`} className="hover:text-sky-400 transition">
                        {r.id}
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-xs font-mono text-slate-400">
                      {r.site_id}
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(r.status)}</td>
                    <td className="px-6 py-4 font-mono text-xs text-sky-400">
                      {r.current_pass || "—"}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-sky-500 h-full"
                            style={{ width: `${Math.min(100, Math.max(0, r.progress_pct))}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-mono">{Math.round(r.progress_pct)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs">
                      <span className="font-semibold text-white">{r.urls_crawled}</span>
                      <span className="text-slate-500"> / </span>
                      <span className="text-sky-400 font-semibold">{r.total_issues}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/runs/${r.id}`}
                        className="inline-flex items-center space-x-1 text-xs text-sky-400 hover:text-sky-300 font-semibold transition"
                      >
                        <span>View Detail</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RunsHistoryPage() {
  return (
    <ProtectedRoute>
      <Suspense
        fallback={
          <div className="py-16 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        }
      >
        <RunsHistoryTable />
      </Suspense>
    </ProtectedRoute>
  );
}
