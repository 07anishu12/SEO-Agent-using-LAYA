"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, X, Loader2, FileCode, AlertCircle, HelpCircle, ArrowRight } from "lucide-react";
import { searchContent } from "@/lib/api";
import { SearchResponse, SearchResultItem } from "@/types/api";

export default function GlobalSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<"all" | "findings" | "blueprints" | "queries">("all");
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search
  useEffect(() => {
    if (!query.trim() || query.trim().length < 2) {
      setResults(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const res = await searchContent(query.trim());
        setResults(res);
      } catch (err) {
        console.error("Search error:", err);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Escape key listener
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleKeyDownInput = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && query.trim()) {
      setIsOpen(false);
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  const getFilteredItems = (): SearchResultItem[] => {
    if (!results) return [];
    if (selectedCategory === "findings") return results.results.findings;
    if (selectedCategory === "blueprints") return results.results.blueprints;
    if (selectedCategory === "queries") return results.results.queries;
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
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <AlertCircle className="w-2.5 h-2.5" /> Findings
          </span>
        );
      case "blueprints":
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/30">
            <FileCode className="w-2.5 h-2.5" /> Blueprint
          </span>
        );
      case "queries":
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <HelpCircle className="w-2.5 h-2.5" /> GSC Query
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400">
            {cat}
          </span>
        );
    }
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-xs md:max-w-sm lg:max-w-md">
      <div className="relative flex items-center">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDownInput}
          placeholder="Search findings, blueprints, queries..."
          className="w-full bg-slate-800/80 hover:bg-slate-800 text-slate-200 text-xs pl-9 pr-8 py-1.5 rounded-lg border border-slate-700 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition placeholder:text-slate-500"
        />
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 text-sky-400 animate-spin absolute right-2.5" />
        ) : query ? (
          <button
            onClick={() => {
              setQuery("");
              setResults(null);
            }}
            className="text-slate-400 hover:text-white absolute right-2.5"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        ) : null}
      </div>

      {/* Dropdown Results Box */}
      {isOpen && query.trim().length >= 2 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-100">
          {/* Category Tabs */}
          {results && results.total_matches > 0 && (
            <div className="flex items-center gap-1 p-2 border-b border-slate-800 bg-slate-950/60 text-xs overflow-x-auto">
              <button
                onClick={() => setSelectedCategory("all")}
                className={`px-2.5 py-1 rounded-md font-medium transition ${
                  selectedCategory === "all"
                    ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                All ({results.total_matches})
              </button>
              <button
                onClick={() => setSelectedCategory("findings")}
                className={`px-2.5 py-1 rounded-md font-medium transition ${
                  selectedCategory === "findings"
                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Findings ({results.results.findings.length})
              </button>
              <button
                onClick={() => setSelectedCategory("blueprints")}
                className={`px-2.5 py-1 rounded-md font-medium transition ${
                  selectedCategory === "blueprints"
                    ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Blueprints ({results.results.blueprints.length})
              </button>
              <button
                onClick={() => setSelectedCategory("queries")}
                className={`px-2.5 py-1 rounded-md font-medium transition ${
                  selectedCategory === "queries"
                    ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Queries ({results.results.queries.length})
              </button>
            </div>
          )}

          {/* Results List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60">
            {loading && !results ? (
              <div className="p-6 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
                Searching index...
              </div>
            ) : filteredItems.length > 0 ? (
              filteredItems.map((item) => (
                <Link
                  key={item.id}
                  href={item.target_url}
                  onClick={() => setIsOpen(false)}
                  className="block p-3 hover:bg-slate-800/60 transition group"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2 overflow-hidden">
                      {getCategoryBadge(item.category)}
                      <span className="text-xs font-semibold text-slate-200 group-hover:text-sky-400 truncate transition">
                        {item.title}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 shrink-0">
                      Score: {item.score.toFixed(3)}
                    </span>
                  </div>

                  {item.excerpt && (
                    <div
                      className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed [&>mark]:bg-sky-500/25 [&>mark]:text-sky-300 [&>mark]:font-medium [&>mark]:px-0.5 [&>mark]:rounded"
                      dangerouslySetInnerHTML={{ __html: item.excerpt }}
                    />
                  )}

                  {item.metadata?.clicks !== undefined && (
                    <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-500">
                      <span>Clicks: {item.metadata.clicks}</span>
                      <span>Impressions: {item.metadata.impressions}</span>
                      <span>Pos: {item.metadata.position}</span>
                    </div>
                  )}
                </Link>
              ))
            ) : (
              <div className="p-6 text-center text-xs text-slate-400">
                No matching findings, blueprints, or queries found for &quot;{query}&quot;.
              </div>
            )}
          </div>

          {/* Footer View All */}
          {results && results.total_matches > 0 && (
            <div className="p-2 border-t border-slate-800 bg-slate-950/80 text-center">
              <Link
                href={`/search?q=${encodeURIComponent(query.trim())}`}
                onClick={() => setIsOpen(false)}
                className="inline-flex items-center gap-1 text-xs font-medium text-sky-400 hover:text-sky-300 transition"
              >
                <span>View all {results.total_matches} results in search page</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
