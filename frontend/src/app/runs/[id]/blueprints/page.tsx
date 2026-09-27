"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import RunNavTabs from "@/components/RunNavTabs";
import { getRunBlueprintPages, getRun } from "@/lib/api";
import { BlueprintPage, Run } from "@/types/api";
import {
  FileCode,
  ArrowLeft,
  ArrowRight,
  Search,
  AlertCircle,
  ExternalLink,
  Layers,
  Link2,
} from "lucide-react";

export default function BlueprintsPage() {
  const params = useParams();
  const runId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [pages, setPages] = useState<BlueprintPage[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState<string>("");
  const [templateFilter, setTemplateFilter] = useState<string>("");

  const fetchPages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pData, rData] = await Promise.all([
        getRunBlueprintPages(runId, search || undefined, templateFilter || undefined),
        getRun(runId),
      ]);
      setPages(pData);
      setRun(rData);
    } catch (err: any) {
      setError(err.message || "Failed to load blueprint pages");
    } finally {
      setLoading(false);
    }
  }, [runId, search, templateFilter]);

  useEffect(() => {
    fetchPages();
  }, [fetchPages]);

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
                <FileCode className="w-6 h-6 text-purple-400" />
                <span>Page Optimization Blueprints</span>
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

        {/* Search Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="relative w-full max-w-md">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search crawled URLs or page titles..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 w-full"
            />
          </div>

          <span className="text-xs text-slate-400 font-mono">
            Pages available: <strong>{pages.length}</strong>
          </span>
        </div>

        {/* Pages Table */}
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm text-slate-400">Loading crawled page index...</p>
          </div>
        ) : pages.length === 0 ? (
          <div className="border border-dashed border-slate-800 rounded-2xl p-12 text-center bg-slate-900/40">
            <FileCode className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white">No pages found</h3>
            <p className="text-sm text-slate-400 max-w-sm mx-auto mt-1">
              No crawled pages match the search criteria for this run.
            </p>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4">Page URL</th>
                    <th className="px-6 py-4">Title</th>
                    <th className="px-6 py-4">Template</th>
                    <th className="px-6 py-4">Inlinks</th>
                    <th className="px-6 py-4">Word Count</th>
                    <th className="px-6 py-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {pages.map((p, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/40 transition">
                      <td className="px-6 py-4 max-w-xs sm:max-w-sm">
                        <Link
                          href={`/runs/${runId}/blueprints/detail?url=${encodeURIComponent(p.url)}`}
                          className="font-mono text-xs text-sky-400 hover:underline truncate block"
                          title={p.url}
                        >
                          {p.url}
                        </Link>
                      </td>
                      <td className="px-6 py-4 max-w-xs text-xs text-slate-300 truncate" title={p.title || "—"}>
                        {p.title || <span className="text-slate-600">—</span>}
                      </td>
                      <td className="px-6 py-4">
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          {p.template_id || "—"}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-400">
                        {p.inlinks_count}
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-400">
                        {p.word_count || "—"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={`/runs/${runId}/blueprints/detail?url=${encodeURIComponent(p.url)}`}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-purple-400 hover:text-purple-300 font-semibold transition"
                        >
                          <span>Inspect Blueprint</span>
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
    </ProtectedRoute>
  );
}
