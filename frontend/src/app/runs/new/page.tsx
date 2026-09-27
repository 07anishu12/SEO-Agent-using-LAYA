"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { getSites, createRun } from "@/lib/api";
import { Site } from "@/types/api";
import {
  Play,
  ArrowLeft,
  AlertCircle,
  Globe,
} from "lucide-react";

function NewRunForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedSiteId = searchParams.get("site_id");

  const [sites, setSites] = useState<Site[]>([]);
  const [loadingSites, setLoadingSites] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [selectedSiteId, setSelectedSiteId] = useState<string>(preselectedSiteId || "");
  const [maxPages, setMaxPages] = useState<number>(50);
  const [concurrency, setConcurrency] = useState<number>(2);
  const [renderJs, setRenderJs] = useState<boolean>(false);
  const [freshCrawl, setFreshCrawl] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getSites();
        setSites(data);
        if (!selectedSiteId && data.length > 0) {
          if (preselectedSiteId && data.some((s) => s.id === preselectedSiteId)) {
            setSelectedSiteId(preselectedSiteId);
          } else {
            setSelectedSiteId(data[0].id);
          }
        }
      } catch (err: any) {
        setError(err.message || "Failed to load sites");
      } finally {
        setLoadingSites(false);
      }
    }
    load();
  }, [preselectedSiteId, selectedSiteId]);

  const selectedSite = sites.find((s) => s.id === selectedSiteId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSiteId) {
      setError("Please select a target site");
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const res = await createRun({
        site_id: selectedSiteId,
        max_pages: Number(maxPages),
        concurrency: Number(concurrency),
        render: Boolean(renderJs),
        fresh: Boolean(freshCrawl),
      });

      // Redirect directly to the live run detail page
      router.push(`/runs/${res.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to start run");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link
        href="/sites"
        className="inline-flex items-center space-x-2 text-sm text-slate-400 hover:text-white transition mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Sites</span>
      </Link>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl">
        <div className="flex items-center space-x-3 pb-6 border-b border-slate-800">
          <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400">
            <Play className="w-6 h-6 fill-current" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Start New Crawl & Audit</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Launch a 6-pass search intelligence pipeline with live SSE telemetry
            </p>
          </div>
        </div>

        {error && (
          <div className="mt-6 rounded-lg bg-rose-500/10 border border-rose-500/30 p-4 flex items-center space-x-3 text-rose-300 text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {loadingSites ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <div className="w-6 h-6 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-xs text-slate-400">Loading available sites...</p>
          </div>
        ) : sites.length === 0 ? (
          <div className="py-12 text-center">
            <Globe className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-300 font-medium">No sites registered yet</p>
            <p className="text-xs text-slate-500 mt-1 mb-4">
              You must add at least one site before starting a crawl.
            </p>
            <Link
              href="/sites"
              className="inline-flex items-center px-4 py-2 rounded-lg bg-sky-600 text-white text-xs font-semibold hover:bg-sky-500 transition"
            >
              Go to Sites
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 space-y-6">
            {/* Site Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Target Website *
              </label>
              <select
                value={selectedSiteId}
                onChange={(e) => setSelectedSiteId(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                {sites.map((site) => (
                  <option key={site.id} value={site.id}>
                    {site.domain} ({site.url}) — {site.vertical}
                  </option>
                ))}
              </select>

              {selectedSite && (
                <div className="mt-2 text-xs text-slate-400 flex items-center gap-3">
                  <span>
                    Target URL: <strong className="text-slate-200">{selectedSite.url}</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Vertical: <strong className="text-slate-200">{selectedSite.vertical}</strong>
                  </span>
                </div>
              )}
            </div>

            {/* Crawl Limits */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-slate-800">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Max Pages to Crawl
                </label>
                <input
                  type="number"
                  min={1}
                  max={10000}
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Default: 50 pages (bounded memory crawl)
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Concurrency (Workers)
                </label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={concurrency}
                  onChange={(e) => setConcurrency(Number(e.target.value))}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Default: 2 parallel asynchronous workers
                </span>
              </div>
            </div>

            {/* Engine Options */}
            <div className="pt-4 border-t border-slate-800 space-y-3">
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Crawl Engine Options
              </label>

              <div className="flex items-center space-x-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <input
                  id="fresh"
                  type="checkbox"
                  checked={freshCrawl}
                  onChange={(e) => setFreshCrawl(e.target.checked)}
                  className="w-4 h-4 text-sky-600 bg-slate-900 border-slate-700 rounded focus:ring-sky-500"
                />
                <label htmlFor="fresh" className="text-xs text-slate-300 cursor-pointer">
                  <span className="font-semibold block text-white">Fresh Crawl Frontier</span>
                  Discard prior crawl database and discover site from scratch
                </label>
              </div>

              <div className="flex items-center space-x-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <input
                  id="render"
                  type="checkbox"
                  checked={renderJs}
                  onChange={(e) => setRenderJs(e.target.checked)}
                  className="w-4 h-4 text-sky-600 bg-slate-900 border-slate-700 rounded focus:ring-sky-500"
                />
                <label htmlFor="render" className="text-xs text-slate-300 cursor-pointer">
                  <span className="font-semibold block text-white">
                    Playwright Headless Rendering
                  </span>
                  Execute client-side JavaScript for React / Next / Vue single-page apps
                </label>
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-6 border-t border-slate-800 flex items-center justify-end space-x-4">
              <Link
                href="/sites"
                className="px-4 py-2 text-sm text-slate-400 hover:text-white transition"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={submitting || !selectedSiteId}
                className="inline-flex items-center space-x-2 px-6 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold shadow-md shadow-sky-600/20 disabled:opacity-50 transition"
              >
                {submitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Enqueuing Run...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>Start Audit Run</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default function NewRunPage() {
  return (
    <ProtectedRoute>
      <Suspense
        fallback={
          <div className="py-16 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        }
      >
        <NewRunForm />
      </Suspense>
    </ProtectedRoute>
  );
}
