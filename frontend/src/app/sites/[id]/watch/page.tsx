"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { getSite, getWatchConfig, updateWatchConfig, getSiteAlerts, resolveAlert } from "@/lib/api";
import { Site, WatchConfig, Alert, NotificationChannel } from "@/types/api";
import {
  Bell,
  ShieldAlert,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  Clock,
  ArrowLeft,
  Save,
  Send,
  Mail,
  Slack,
  Globe,
  Radio,
  ExternalLink,
  RefreshCw,
  Sliders,
  Filter,
} from "lucide-react";

export default function WatchAlertsPage() {
  const params = useParams();
  const router = useRouter();
  const siteId = params.id as string;

  const [site, setSite] = useState<Site | null>(null);
  const [watchConfig, setWatchConfig] = useState<WatchConfig | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [totalAlerts, setTotalAlerts] = useState(0);

  const [loading, setLoading] = useState(true);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Filter state
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Editable watch config form
  const [cronExpression, setCronExpression] = useState("0 0 * * *");
  const [isActive, setIsActive] = useState(true);
  const [timezone, setTimezone] = useState("UTC");
  const [checks, setChecks] = useState<string[]>([
    "robots_txt",
    "sitemap",
    "top_pages",
    "template_drift",
  ]);
  const [slackUrl, setSlackUrl] = useState("");
  const [emailRecipients, setEmailRecipients] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [siteData, configData, alertData] = await Promise.all([
        getSite(siteId),
        getWatchConfig(siteId),
        getSiteAlerts(siteId),
      ]);
      setSite(siteData);
      setWatchConfig(configData);
      setAlerts(alertData.alerts);
      setTotalAlerts(alertData.total);

      // Populate form
      setCronExpression(configData.cron_expression || "0 0 * * *");
      setIsActive(configData.is_active ?? true);
      setTimezone(configData.timezone || "UTC");
      setChecks(configData.checks || ["robots_txt", "sitemap", "top_pages", "template_drift"]);

      // Populate notification channels
      const channels = configData.notification_channels || [];
      const slackCh = channels.find((c) => c.type === "slack");
      const emailCh = channels.find((c) => c.type === "email");
      const webhookCh = channels.find((c) => c.type === "webhook");

      setSlackUrl(slackCh?.webhook_url || slackCh?.url || "");
      setEmailRecipients(emailCh?.recipients?.join(", ") || "");
      setWebhookUrl(webhookCh?.url || webhookCh?.webhook_url || "");
    } catch (err: any) {
      setError(err.message || "Failed to load watch and alerts data");
    } finally {
      setLoading(false);
    }
  };

  const fetchFilteredAlerts = async () => {
    setAlertsLoading(true);
    try {
      const data = await getSiteAlerts(siteId, {
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
      });
      setAlerts(data.alerts);
      setTotalAlerts(data.total);
    } catch (err: any) {
      console.error("Failed to filter alerts:", err);
    } finally {
      setAlertsLoading(false);
    }
  };

  useEffect(() => {
    if (siteId) {
      fetchData();
    }
  }, [siteId]);

  useEffect(() => {
    if (!loading && siteId) {
      fetchFilteredAlerts();
    }
  }, [severityFilter, statusFilter]);

  const handleToggleCheck = (checkName: string) => {
    setChecks((prev) =>
      prev.includes(checkName) ? prev.filter((c) => c !== checkName) : [...prev, checkName]
    );
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    setError(null);

    const notificationChannels: NotificationChannel[] = [];
    if (slackUrl.trim()) {
      notificationChannels.push({ type: "slack", webhook_url: slackUrl.trim() });
    }
    if (emailRecipients.trim()) {
      const recips = emailRecipients
        .split(",")
        .map((r) => r.trim())
        .filter(Boolean);
      if (recips.length > 0) {
        notificationChannels.push({ type: "email", recipients: recips });
      }
    }
    if (webhookUrl.trim()) {
      notificationChannels.push({ type: "webhook", url: webhookUrl.trim() });
    }

    try {
      const updated = await updateWatchConfig(siteId, {
        cron_expression: cronExpression,
        is_active: isActive,
        timezone,
        checks,
        notification_channels: notificationChannels,
      });
      setWatchConfig(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to save watch configuration");
    } finally {
      setSaving(false);
    }
  };

  const handleResolveAlert = async (alertId: string) => {
    try {
      const updated = await resolveAlert(siteId, alertId);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
    } catch (err: any) {
      alert("Failed to resolve alert: " + (err.message || "Unknown error"));
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";
      case "high":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      case "medium":
        return "bg-yellow-500/20 text-yellow-300 border-yellow-500/40";
      default:
        return "bg-slate-500/20 text-slate-300 border-slate-500/40";
    }
  };

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
          <div>
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400">
                <Bell className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                  <span>Watch & Alerts Center</span>
                  {site && (
                    <span className="text-sm font-normal font-mono px-2.5 py-0.5 rounded-full bg-slate-800 text-sky-300 border border-slate-700">
                      {site.domain}
                    </span>
                  )}
                </h1>
                <p className="text-sm text-slate-400 mt-1">
                  Automated lightweight health checks, critical regression classification, and multi-channel dispatch.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => fetchData()}
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

        {/* Success toast */}
        {saveSuccess && (
          <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-4 text-emerald-300 text-sm flex items-center space-x-3">
            <CheckCircle className="w-5 h-5 flex-shrink-0 text-emerald-400" />
            <span>Watch schedule configuration saved and activated successfully.</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Watch Schedule Configuration */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center space-x-2.5">
                  <Sliders className="w-5 h-5 text-sky-400" />
                  <h2 className="text-base font-bold text-white">Watch Schedule Config</h2>
                </div>
                <label className="flex items-center cursor-pointer space-x-2">
                  <span className="text-xs font-semibold text-slate-300">
                    {isActive ? "Active" : "Paused"}
                  </span>
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-sky-600 relative"></div>
                </label>
              </div>

              <form onSubmit={handleSaveConfig} className="space-y-5">
                {/* Cron Expression */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Cron Schedule *
                    </label>
                    <span className="text-[11px] font-mono text-slate-400">5-part cron syntax</span>
                  </div>
                  <input
                    type="text"
                    required
                    value={cronExpression}
                    onChange={(e) => setCronExpression(e.target.value)}
                    placeholder="0 0 * * * or */5 * * * *"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  />

                  {/* Presets */}
                  <div className="flex flex-wrap gap-2 mt-2">
                    {[
                      { label: "Every 5 min", cron: "*/5 * * * *" },
                      { label: "Hourly", cron: "0 * * * *" },
                      { label: "Every 6h", cron: "0 */6 * * *" },
                      { label: "Daily (00:00)", cron: "0 0 * * *" },
                    ].map((p) => (
                      <button
                        type="button"
                        key={p.cron}
                        onClick={() => setCronExpression(p.cron)}
                        className="text-[11px] px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition font-mono"
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Telemetry info */}
                {watchConfig && (
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-2">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-sky-400" />
                        <span>Next Scheduled Run:</span>
                      </span>
                      <span className="text-slate-200 font-mono">
                        {watchConfig.next_run_at
                          ? new Date(watchConfig.next_run_at).toLocaleString()
                          : "Scheduled upon save"}
                      </span>
                    </div>
                    {watchConfig.last_run_at && (
                      <div className="flex items-center justify-between text-slate-400">
                        <span>Last Check Executed:</span>
                        <span className="text-slate-300 font-mono">
                          {new Date(watchConfig.last_run_at).toLocaleString()}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Enabled Checks */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5">
                    Lightweight Verification Passes
                  </label>
                  <div className="space-y-2.5">
                    {[
                      {
                        id: "robots_txt",
                        label: "Robots.txt Directives",
                        desc: "Detects 5xx/404 fetch errors and rogue Disallow: / rules blocking all search crawlers.",
                      },
                      {
                        id: "sitemap",
                        label: "XML Sitemap Integrity",
                        desc: "Monitors sitemap.xml availability and detects critical URL drops (>20% loss).",
                      },
                      {
                        id: "top_pages",
                        label: "Top-Page Health & Directives",
                        desc: "Monitors critical landing pages for 5xx spikes, accidental noindex directives, and canonical wipes.",
                      },
                      {
                        id: "template_drift",
                        label: "Template Structure Drift",
                        desc: "Evaluates structural DOM integrity across template layouts.",
                      },
                    ].map((item) => (
                      <label
                        key={item.id}
                        className={`flex items-start space-x-3 p-3 rounded-xl border cursor-pointer transition ${
                          checks.includes(item.id)
                            ? "bg-sky-950/20 border-sky-800/60"
                            : "bg-slate-950/40 border-slate-800 hover:border-slate-700"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checks.includes(item.id)}
                          onChange={() => handleToggleCheck(item.id)}
                          className="mt-1 rounded bg-slate-900 border-slate-700 text-sky-600 focus:ring-sky-500"
                        />
                        <div>
                          <div className="text-xs font-bold text-white">{item.label}</div>
                          <div className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                            {item.desc}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Notification Channels */}
                <div className="pt-2 border-t border-slate-800 space-y-3.5">
                  <div className="flex items-center space-x-2">
                    <Send className="w-4 h-4 text-sky-400" />
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Notification Dispatcher Channels
                    </span>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">
                      Slack Incoming Webhook URL
                    </label>
                    <input
                      type="url"
                      value={slackUrl}
                      onChange={(e) => setSlackUrl(e.target.value)}
                      placeholder="https://hooks.slack.com/services/..."
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs font-mono focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">
                      Alert Email Recipients (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={emailRecipients}
                      onChange={(e) => setEmailRecipients(e.target.value)}
                      placeholder="seo-alerts@domain.com, tech@domain.com"
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">
                      Generic Outgoing Webhook URL
                    </label>
                    <input
                      type="url"
                      value={webhookUrl}
                      onChange={(e) => setWebhookUrl(e.target.value)}
                      placeholder="https://api.yourdomain.com/webhooks/seojev"
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs font-mono focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={saving}
                  className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold shadow-md shadow-sky-600/20 transition disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  <span>{saving ? "Saving Schedule..." : "Save Schedule Configuration"}</span>
                </button>
              </form>
            </div>
          </div>

          {/* Right Column: Alert History Ledger */}
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
              {/* Ledger Header & Filter Controls */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-4">
                <div className="flex items-center space-x-3">
                  <ShieldAlert className="w-5 h-5 text-amber-400" />
                  <div>
                    <h2 className="text-base font-bold text-white flex items-center gap-2">
                      <span>Alert History Ledger</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono border border-slate-700">
                        {totalAlerts}
                      </span>
                    </h2>
                  </div>
                </div>

                {/* Filter controls */}
                <div className="flex items-center space-x-2">
                  <select
                    value={severityFilter}
                    onChange={(e) => setSeverityFilter(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  >
                    <option value="">All Severities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>

                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  >
                    <option value="">All Statuses</option>
                    <option value="open">Open</option>
                    <option value="resolved">Resolved</option>
                  </select>
                </div>
              </div>

              {/* Alerts List */}
              {alertsLoading ? (
                <div className="py-12 flex flex-col items-center justify-center space-y-3">
                  <RefreshCw className="w-6 h-6 text-sky-400 animate-spin" />
                  <span className="text-xs text-slate-400">Filtering alert records...</span>
                </div>
              ) : alerts.length === 0 ? (
                <div className="py-16 px-4 rounded-xl bg-slate-950/40 border border-slate-800 text-center space-y-3">
                  <div className="inline-flex p-3 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <ShieldCheck className="w-8 h-8" />
                  </div>
                  <h3 className="text-sm font-bold text-white">No Alerts Recorded</h3>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    All lightweight checks and continuous regression verifications are clean. No critical SEO anomalies detected.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-4 rounded-xl border transition ${
                        alert.status === "resolved"
                          ? "bg-slate-950/30 border-slate-800/60 opacity-70"
                          : "bg-slate-950 border-slate-800 shadow-sm"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1.5 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${getSeverityBadge(
                                alert.severity
                              )}`}
                            >
                              {alert.severity}
                            </span>
                            <span className="text-xs font-mono font-semibold text-sky-400">
                              {alert.alert_type}
                            </span>
                            <span className="text-[11px] text-slate-500 font-mono">
                              {alert.detected_at
                                ? new Date(alert.detected_at).toLocaleString()
                                : "Just now"}
                            </span>
                          </div>

                          <h4 className="text-sm font-bold text-white">{alert.title}</h4>
                          <p className="text-xs text-slate-300 leading-relaxed">{alert.message}</p>
                        </div>

                        {alert.status !== "resolved" ? (
                          <button
                            onClick={() => handleResolveAlert(alert.id)}
                            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition flex-shrink-0"
                          >
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Resolve</span>
                          </button>
                        ) : (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-950/50 text-emerald-400 text-[11px] font-medium border border-emerald-800/40">
                            <CheckCircle className="w-3 h-3" />
                            <span>Resolved</span>
                          </span>
                        )}
                      </div>

                      {/* Affected URLs */}
                      {alert.affected_urls && alert.affected_urls.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-800/70 space-y-1">
                          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                            Affected URLs:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {alert.affected_urls.map((u, i) => (
                              <a
                                key={i}
                                href={u}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center space-x-1 text-[11px] font-mono text-sky-400 bg-sky-950/40 hover:bg-sky-900/40 px-2 py-0.5 rounded border border-sky-800/40 transition truncate max-w-full"
                              >
                                <span className="truncate">{u}</span>
                                <ExternalLink className="w-2.5 h-2.5 flex-shrink-0" />
                              </a>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Channel delivery footer */}
                      <div className="mt-3 pt-2.5 border-t border-slate-800/50 flex items-center justify-between text-[11px] text-slate-400">
                        <div className="flex items-center space-x-3">
                          <span className="text-slate-500">Dispatched:</span>
                          <span
                            className={`flex items-center gap-1 ${
                              alert.dispatched ? "text-emerald-400" : "text-amber-400"
                            }`}
                          >
                            <Radio className="w-3 h-3" />
                            <span className="capitalize">{alert.dispatch_status || "Pending"}</span>
                          </span>
                        </div>
                        <span className="font-mono text-[10px] text-slate-500">{alert.id}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
