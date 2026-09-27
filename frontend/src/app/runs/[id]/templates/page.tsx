"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import RunNavTabs from "@/components/RunNavTabs";
import { getRunTemplates, getRun } from "@/lib/api";
import { TemplateSummary, Run } from "@/types/api";
import {
  Layers,
  ArrowLeft,
  ArrowRight,
  Search,
  AlertCircle,
  FileText,
  Link2,
} from "lucide-react";

export default function TemplatesListPage() {
  const params = useParams();
  const runId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>("");

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tData, rData] = await Promise.all([
        getRunTemplates(runId, search || undefined),
        getRun(runId),
      ]);
      setTemplates(tData);
      setRun(rData);
    } catch (err: any) {
      setError(err.message || "Failed to load templates");
    } finally {
      setLoading(false);
    }
  }, [runId, search]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

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
                <Layers className="w-6 h-6 text-emerald-400" />
                <span>Structural Templates Explorer</span>
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

        {/* Filter Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div className="relative w-full max-w-md">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search by template ID or page type..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 w-full"
            />
          </div>
          <span className="text-xs text-slate-400 font-mono ml-4">
            Total Templates: <strong>{templates.length}</strong>
          </span>
        </div>

        {/* Templates Grid / Table */}
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm text-slate-400">Loading clustered templates...</p>
          </div>
        ) : templates.length === 0 ? (
          <div className="border border-dashed border-slate-800 rounded-2xl p-12 text-center bg-slate-900/40">
            <Layers className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white">No templates found</h3>
            <p className="text-sm text-slate-400 max-w-sm mx-auto mt-1">
              No SimHash structural template clusters match the search query for this run.
            </p>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4">Template ID</th>
                    <th className="px-6 py-4">Dominant Page Type</th>
                    <th className="px-6 py-4">Member Pages</th>
                    <th className="px-6 py-4">Associated Issues</th>
                    <th className="px-6 py-4">Avg Word Count</th>
                    <th className="px-6 py-4">Avg Inlinks</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {templates.map((tpl) => (
                    <tr key={tpl.id} className="hover:bg-slate-800/40 transition">
                      <td className="px-6 py-4 font-mono font-bold text-white">
                        <Link
                          href={`/runs/${runId}/templates/${encodeURIComponent(tpl.template_id)}`}
                          className="hover:text-sky-400 transition"
                        >
                          {tpl.template_id}
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-sky-300 border border-slate-700 uppercase tracking-wider font-mono">
                          {tpl.page_type || "GENERIC"}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono font-semibold text-white">
                        {tpl.page_count}
                      </td>
                      <td className="px-6 py-4 font-mono">
                        <span
                          className={`font-semibold ${
                            tpl.issue_count > 0 ? "text-rose-400" : "text-emerald-400"
                          }`}
                        >
                          {tpl.issue_count}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs font-mono text-slate-400">
                        {tpl.avg_word_count !== null && tpl.avg_word_count !== undefined
                          ? Math.round(tpl.avg_word_count)
                          : "—"}
                      </td>
                      <td className="px-6 py-4 text-xs font-mono text-slate-400">
                        {tpl.avg_inlinks !== null && tpl.avg_inlinks !== undefined
                          ? tpl.avg_inlinks.toFixed(1)
                          : "—"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={`/runs/${runId}/templates/${encodeURIComponent(tpl.template_id)}`}
                          className="inline-flex items-center space-x-1 text-xs text-sky-400 hover:text-sky-300 font-semibold transition"
                        >
                          <span>Inspect Template</span>
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
