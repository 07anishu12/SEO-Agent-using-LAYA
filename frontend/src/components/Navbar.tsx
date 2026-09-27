"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Globe, Play, History, LogOut, ShieldCheck } from "lucide-react";
import GlobalSearch from "@/components/GlobalSearch";

export default function Navbar() {
  const { user, logout, isEditor, isViewer, isAdmin } = useAuth();
  const pathname = usePathname();

  if (!user) return null;

  const roleLabel = (user.role || "viewer").toUpperCase();

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-8 shrink-0">
            <Link href="/sites" className="flex items-center space-x-3 group">
              <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center text-white font-bold shadow-md shadow-sky-500/20 group-hover:bg-sky-400 transition">
                S
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-lg font-bold tracking-tight text-white">SEOJEV</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-sky-950 text-sky-400 border border-sky-800 font-mono">
                  Platform
                </span>
              </div>
            </Link>

            {/* Navigation links */}
            <nav className="hidden md:flex items-center space-x-1">
              <Link
                href="/sites"
                className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition ${
                  pathname === "/sites" || pathname === "/"
                    ? "bg-slate-800 text-sky-400"
                    : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
                }`}
              >
                <Globe className="w-4 h-4" />
                <span>Sites</span>
              </Link>
              <Link
                href="/runs"
                className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition ${
                  pathname.startsWith("/runs") && pathname !== "/runs/new"
                    ? "bg-slate-800 text-sky-400"
                    : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
                }`}
              >
                <History className="w-4 h-4" />
                <span>Runs</span>
              </Link>
            </nav>
          </div>

          {/* Unified Global Search Bar */}
          <div className="flex-1 max-w-md hidden sm:block">
            <GlobalSearch />
          </div>

          {/* Right actions & user profile */}
          <div className="flex items-center space-x-4 shrink-0">
            {isEditor ? (
              <Link
                href="/runs/new"
                className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 text-white text-sm font-medium shadow-sm transition"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>New Run</span>
              </Link>
            ) : (
              <span className="text-[11px] px-2.5 py-1 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60">
                Viewer (Read-Only)
              </span>
            )}

            <div className="hidden sm:flex items-center space-x-3 pl-3 border-l border-slate-800">
              <div className="flex flex-col text-right">
                <div className="flex items-center justify-end gap-1.5">
                  <span className="text-xs text-slate-200 font-medium">{user.email}</span>
                  <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase ${
                    isAdmin ? "bg-amber-500/20 text-amber-300 border border-amber-500/40" :
                    isEditor ? "bg-sky-500/20 text-sky-300 border border-sky-500/40" :
                    "bg-slate-800 text-slate-400 border border-slate-700"
                  }`}>
                    {roleLabel}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 font-mono">{user.org_id}</span>
              </div>
            </div>

            <button
              onClick={logout}
              title="Sign Out"
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-md transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
