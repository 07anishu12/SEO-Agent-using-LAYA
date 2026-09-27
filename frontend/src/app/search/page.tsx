"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import { searchContent } from "@/lib/api";
import { SearchResponse, SearchResultItem } from "@/types/api";
import { Search, AlertCircle, FileCode, HelpCircle, Loader2, ArrowLeft } from "lucide-react";

function SearchPageContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [activeCategory, setActiveCategory] = useState<"all" | "findings" | "blueprints" | "queries">("all");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);

  const performSearch = async (term: string) => {
    if (!term.trim()) {
      setResults(null);
      return;
    }
    setLoading(true);
    try {
      const data = await searchContent(term.trim());
      setResults(data);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialQuery) {
      performSearch(initialQuery);
    }
  }, [initialQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    performSearch(query);
  };

  const getFilteredItems = (): SearchResultItem[] => {
    if (!results) return [];
    if (activeCategory === "findings") return results.results.findings;
    if (activeCategory === "blueprints") return results.results.blueprints;
    if (activeCategory === "queries") return results.results.queries;
    return [
      ...results.results.findings,
      ...results.results.blueprints,
      ...results.results.queries,
    ].sort((a, b) => b.score - a.score);
  };

  const filteredItems = getFilteredItems();

  const getCategoryBadge = (cat: string) => {
    switch (cat.toLowerCase()) {
      case "findings":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold uppercase px-2.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <AlertCircle className="w-3 h-3" /> Findings
          </span>
        );
      case "blueprints":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold uppercase px-2.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/30">
            <FileCode className="w-3 h-3" /> Blueprint
          </span>
        );
      case "queries":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold uppercase px-2.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <HelpCircle className="w-3 h-3" /> GSC Query
          </span>
        );
      default:
        return (
          <span className="text-xs font-semibold uppercase px-2.5 py-0.5 rounded bg-slate-800 text-slate-400">
            {cat}
          </span>
        );
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/sites"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-sky-400 mb-4 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Sites</span>
        </Link>
        <h1 className="text-2xl font-bold text-white tracking-tight">Full-Text Search</h1>
        <p className="text-sm text-slate-400 mt-1">
          PostgreSQL tsvector-ranked search across technical findings, optimization blueprints, and search queries.
        </p>
      </div>

      {/* Search Input Bar */}
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="relative flex items-center">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search findings, opportunities, blueprints, search queries..."
            className="w-full bg-slate-900 text-slate-100 text-sm pl-12 pr-28 py-3 rounded-xl border border-slate-700 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition shadow-inner"
          />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-2 px-5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold transition flex items-center gap-1.5 shadow"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            <span>Search</span>
          </button>
        </div>
      </form>

      {/* Category Tabs */}
      {results && (
        <div className="flex items-center gap-2 mb-6 border-b border-slate-800 pb-3 overflow-x-auto">
          <button
            onClick={() => setActiveCategory("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeCategory === "all"
                ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            All Results ({results.total_matches})
          </button>
          <button
            onClick={() => setActiveCategory("findings")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeCategory === "findings"
                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Findings ({results.results.findings.length})
          </button>
          <button
            onClick={() => setActiveCategory("blueprints")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeCategory === "blueprints"
                ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Blueprints ({results.results.blueprints.length})
          </button>
          <button
            onClick={() => setActiveCategory("queries")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeCategory === "queries"
                ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Queries ({results.results.queries.length})
          </button>
        </div>
      )}

      {/* Results Content */}
      {loading ? (
        <div className="py-20 text-center text-sm text-slate-400 flex flex-col items-center justify-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
          <span>Searching PostgreSQL index...</span>
        </div>
      ) : results ? (
        filteredItems.length > 0 ? (
          <div className="space-y-4">
            {filteredItems.map((item) => (
              <Link
                key={item.id}
                href={item.target_url}
                className="block p-5 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl transition group"
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex items-center gap-3 flex-wrap">
                    {getCategoryBadge(item.category)}
                    <h3 className="text-base font-semibold text-slate-100 group-hover:text-sky-400 transition">
                      {item.title}
                    </h3>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      Relevance: {item.score.toFixed(3)}
                    </span>
                  </div>
                </div>

                {item.excerpt && (
                  <div
                    className="text-xs text-slate-300 leading-relaxed mt-2 [&>mark]:bg-sky-500/30 [&>mark]:text-sky-200 [&>mark]:font-medium [&>mark]:px-1 [&>mark]:rounded"
                    dangerouslySetInnerHTML={{ __html: item.excerpt }}
                  />
                )}

                <div className="flex items-center justify-between text-xs text-slate-500 mt-4 pt-3 border-t border-slate-800/60">
                  <div className="flex items-center gap-4">
                    {item.run_id && <span>Run: <code className="font-mono text-slate-400">{item.run_id}</code></span>}
                    {item.metadata?.url && (
                      <span className="truncate max-w-md">URL: {item.metadata.url}</span>
                    )}
                    {item.metadata?.clicks !== undefined && (
                      <span>Clicks: <strong className="text-slate-300">{item.metadata.clicks}</strong> | Imp: <strong className="text-slate-300">{item.metadata.impressions}</strong></span>
                    )}
                  </div>
                  <span className="text-sky-400 group-hover:translate-x-0.5 transition-transform flex items-center gap-1 font-medium">
                    Open object &rarr;
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="py-16 text-center bg-slate-900/50 rounded-xl border border-slate-800">
            <p className="text-slate-300 font-medium text-sm">No results found for &quot;{results.query}&quot;</p>
            <p className="text-slate-500 text-xs mt-1">Try another search term or inspect specific categories.</p>
          </div>
        )
      ) : (
        <div className="py-20 text-center text-slate-500 text-sm">
          Enter a search query above to search findings, blueprints, and search performance data.
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<div className="p-8 text-center text-slate-500 text-xs">Loading search...</div>}>
        <SearchPageContent />
      </Suspense>
    </ProtectedRoute>
  );
}
