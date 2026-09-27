"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { getSites, createSite } from "@/lib/api";
import { Site } from "@/types/api";
import {
  Globe,
  Plus,
  Play,
  History,
  AlertCircle,
  ExternalLink,
  Layers,
  Calendar,
  Bell,
} from "lucide-react";

export default function SitesPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add Site Form state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newVertical, setNewVertical] = useState("generic");
  const [newDomain, setNewDomain] = useState("");
  const [addingSite, setAddingSite] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const fetchSites = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSites();
      setSites(data);
    } catch (err: any) {
      setError(err.message || "Failed to load sites");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSites();
  }, []);

  const handleCreateSite = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddError(null);
    setAddingSite(true);

    try {
      const created = await createSite({
        url: newUrl,
        vertical: newVertical,
        domain: newDomain || undefined,
      });
      setSites((prev) => [created, ...prev.filter((s) => s.id !== created.id)]);
      setNewUrl("");
      setNewDomain("");
      setNewVertical("generic");
      setShowAddModal(false);
    } catch (err: any) {
      setAddError(err.message || "Failed to add site");
    } finally {
      setAddingSite(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Globe className="w-6 h-6 text-sky-400" />
              <span>Monitored Sites</span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Manage target domains, trigger crawl audits, and track search performance
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold shadow-md shadow-sky-600/20 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Add Site</span>
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-6 rounded-lg bg-rose-500/10 border border-rose-500/30 p-4 flex items-center justify-between text-rose-300 text-sm">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
            <button
              onClick={fetchSites}
              className="text-xs underline hover:text-rose-200 font-semibold"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="mt-12 flex flex-col items-center justify-center py-16 space-y-4">
            <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm text-slate-400">Loading sites for your organization...</p>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && sites.length === 0 && (
          <div className="mt-12 border border-dashed border-slate-800 rounded-2xl p-12 text-center bg-slate-900/40">
            <div className="mx-auto w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400 mb-4">
              <Globe className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-white">No sites added yet</h3>
            <p className="text-sm text-slate-400 max-w-sm mx-auto mt-1 mb-6">
              Add a target website or staging environment to start deep crawling, template clustering, and opportunity analysis.
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold transition"
            >
              <Plus className="w-4 h-4" />
              <span>Add Your First Site</span>
            </button>
          </div>
        )}

        {/* Sites Grid */}
        {!loading && !error && sites.length > 0 && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sites.map((site) => (
              <div
                key={site.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-xs uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono font-medium">
                        {site.vertical || "generic"}
                      </span>
                      <h3 className="text-lg font-bold text-white mt-2 truncate" title={site.domain}>
                        {site.domain}
                      </h3>
                    </div>
                    <a
                      href={site.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition"
                      title="Open URL"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>

                  <p className="text-xs text-slate-400 mt-1 truncate" title={site.url}>
                    {site.url}
                  </p>

                  <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                    <span className="font-mono text-[11px]">{site.id}</span>
                    {site.created_at && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {new Date(site.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between gap-2">
                  <Link
                    href={`/sites/${site.id}/watch`}
                    className="flex-1 flex items-center justify-center space-x-1.5 py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-400 text-xs font-semibold border border-slate-700/60 transition"
                  >
                    <Bell className="w-3.5 h-3.5" />
                    <span>Watch & Alerts</span>
                  </Link>

                  <Link
                    href={`/runs?site_id=${site.id}`}
                    className="flex-1 flex items-center justify-center space-x-1.5 py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
                  >
                    <History className="w-3.5 h-3.5" />
                    <span>Runs</span>
                  </Link>

                  <Link
                    href={`/runs/new?site_id=${site.id}`}
                    className="flex-1 flex items-center justify-center space-x-1.5 py-2 px-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-sm transition"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>New Run</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add Site Modal */}
        {showAddModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-800 max-w-lg w-full rounded-2xl p-6 shadow-2xl">
              <h2 className="text-xl font-bold text-white mb-1">Add Target Site</h2>
              <p className="text-sm text-slate-400 mb-6">
                Register a new domain to enable automated technical SEO crawling and analysis.
              </p>

              {addError && (
                <div className="mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 p-3 text-rose-300 text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{addError}</span>
                </div>
              )}

              <form onSubmit={handleCreateSite} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Target URL *
                  </label>
                  <input
                    type="text"
                    required
                    value={newUrl}
                    onChange={(e) => setNewUrl(e.target.value)}
                    placeholder="https://example.com or http://127.0.0.1:8944/"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Domain (Optional)
                  </label>
                  <input
                    type="text"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    placeholder="example.com (auto-derived if blank)"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Vertical / Industry
                  </label>
                  <select
                    value={newVertical}
                    onChange={(e) => setNewVertical(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  >
                    <option value="generic">Generic Website</option>
                    <option value="ecommerce">E-Commerce</option>
                    <option value="automotive">Automotive Dealership</option>
                    <option value="saas">SaaS / Software</option>
                    <option value="realestate">Real Estate</option>
                    <option value="healthcare">Healthcare</option>
                  </select>
                </div>

                <div className="pt-4 flex items-center justify-end space-x-3 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 text-sm font-semibold transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={addingSite}
                    className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold shadow-md shadow-sky-600/20 disabled:opacity-50 transition"
                  >
                    {addingSite ? "Registering..." : "Add Site"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
