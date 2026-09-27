"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import RunNavTabs from "@/components/RunNavTabs";
import { getTemplateDetail, getRun } from "@/lib/api";
import { TemplateDetail, Run } from "@/types/api";
import {
  Layers,
  ArrowLeft,
  Globe,
  AlertCircle,
  ExternalLink,
  FileText,
  Link2,
} from "lucide-react";

export default function TemplateDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const templateId = decodeURIComponent(params.template_id as string);

  const [run, setRun] = useState<Run | null>(null);
  const [detail, setDetail] = useState<TemplateDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tDetail, rData] = await Promise.all([
        getTemplateDetail(runId, templateId),
        getRun(runId),
      ]);
      setDetail(tDetail);
      setRun(rData);
    } catch (err: any) {
      setError(err.message || "Failed to load template detail");
    } finally {
      setLoading(false);
    }
  }, [runId, templateId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const tpl = detail?.template;

  return (
    <ProtectedRoute>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div>
          <Link
            href={`/runs/${runId}/templates`}
            className="inline-flex items-center space-x-2 text-sm text-slate-400 hover:text-white transition mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Templates List</span>
          </Link>

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center space-x-3">
                <h1 className="text-2xl font-bold tracking-tight text-white font-mono flex items-center gap-2">
                  <Layers className="w-6 h-6 text-emerald-400" />
                  <span>{templateId}</span>
                </h1>
                {tpl && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-950 text-sky-300 border border-sky-800 uppercase font-mono">
                    {tpl.page_type || "GENERIC"}
                  </span>
                )}
              </div>
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

        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm text-slate-400">Loading template architecture...</p>
          </div>
        ) : !detail ? (
          <div className="text-center py-12 text-slate-500 text-sm">
            Template details not found.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Template Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Member Pages
                </span>
                <div className="text-2xl font-bold text-white mt-1">
                  {tpl?.page_count || detail.member_urls.length}
                </div>
                <span className="text-[11px] text-slate-500">Clustered URLs</span>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Associated Issues
                </span>
                <div className="text-2xl font-bold text-rose-400 mt-1">
                  {tpl?.issue_count || detail.associated_findings.length}
                </div>
                <span className="text-[11px] text-slate-500">Root-cause findings</span>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Avg Word Count
                </span>
                <div className="text-2xl font-bold text-emerald-400 mt-1">
                  {tpl?.avg_word_count ? Math.round(tpl.avg_word_count) : "—"}
                </div>
                <span className="text-[11px] text-slate-500">Words per page</span>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  Avg Internal Links
                </span>
                <div className="text-2xl font-bold text-sky-400 mt-1">
                  {tpl?.avg_inlinks ? tpl.avg_inlinks.toFixed(1) : "—"}
                </div>
                <span className="text-[11px] text-slate-500">Inbound links</span>
              </div>
            </div>

            {/* Affected Member URLs */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-2 flex items-center justify-between">
                <span>Sample Affected Member URLs ({detail.member_urls.length})</span>
                <span className="text-xs text-slate-500 font-mono font-normal">Real Crawled URLs</span>
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                Pages sharing this structural DOM layout and component hierarchy.
              </p>

              {detail.member_urls.length === 0 ? (
                <div className="text-xs text-slate-500 py-4">No member URLs recorded for this template.</div>
              ) : (
                <div className="divide-y divide-slate-800 border border-slate-800 rounded-lg overflow-hidden max-h-80 overflow-y-auto">
                  {detail.member_urls.map((url, idx) => (
                    <div key={idx} className="p-3 bg-slate-950/60 hover:bg-slate-850 flex items-center justify-between text-xs">
                      <span className="font-mono text-slate-300 truncate mr-3" title={url}>
                        {url}
                      </span>
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <Link
                          href={`/runs/${runId}/blueprints/detail?url=${encodeURIComponent(url)}`}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-sky-400 hover:text-sky-300 text-[11px] font-semibold transition"
                        >
                          View Blueprint
                        </Link>
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 text-slate-500 hover:text-white transition"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Associated Findings */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-2">
                Associated Findings for this Template ({detail.associated_findings.length})
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                Systemic issues originating from this template&apos;s reusable component design.
              </p>

              {detail.associated_findings.length === 0 ? (
                <div className="text-xs text-emerald-400 py-4">
                  ✓ No defects or findings associated with this template layout.
                </div>
              ) : (
                <div className="divide-y divide-slate-800 border border-slate-800 rounded-lg overflow-hidden">
                  {detail.associated_findings.map((f, idx) => (
                    <div key={idx} className="p-4 bg-slate-950/60 hover:bg-slate-850 transition">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono font-bold text-sky-400 text-xs">{f.display_id || f.rule_id}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-slate-800 text-slate-300">
                          {f.severity || "MEDIUM"}
                        </span>
                      </div>
                      <p className="text-xs text-slate-200">{f.message}</p>
                      {f.recommended_action && (
                        <p className="text-[11px] text-emerald-300 mt-1">
                          Fix: {f.recommended_action}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
