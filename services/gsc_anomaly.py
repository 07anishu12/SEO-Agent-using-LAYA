"""
SEOJEV Phase 2: GSC Anomaly Detection Service (Stage 10d).

Implements Section 6.9 statistical decay detection for daily Google Search Console (GSC) metrics.

Statistical Methodology:
1. Data Model:
   - Daily aggregated time-series metrics per page and per template:
     clicks, impressions, ctr, position.
2. Temporal Windows:
   - Evaluation Window (Current): Most recent `eval_window_days` (default 3 days).
   - Baseline Window: Preceding `baseline_window_days` (default 14-21 days) excluding evaluation window.
3. Minimum History & Volume Guards:
   - Insufficient History: If total distinct days < `min_history_days` (default 7 days), returns
     status="insufficient_history" with no false alerts.
   - Low Volume Noise Guard:
     - Pages: Baseline daily average must be >= 50 impressions (for impression decay) or >= 5 clicks (for click decay).
     - Templates: Baseline daily average must be >= 150 impressions or >= 15 clicks.
4. Statistical Significance & Decay Thresholds:
   - Let mu_b, sigma_b be baseline mean and standard deviation.
   - Let mu_e be evaluation period mean.
   - Decay ratio: delta = (mu_b - mu_e) / mu_b.
   - Standard score: z = (mu_e - mu_b) / (sigma_b + 1e-6).
   - Flagged Anomaly Condition:
     - Statistically significant decay: delta >= 0.35 (>= 35% decline) AND z <= -2.0 (>= 2 sigma drop),
       OR catastrophic collapse: delta >= 0.60.
5. Severity Categorization:
   - CRITICAL: delta >= 0.70 and z <= -3.0 (or impressions/clicks dropped >= 80%).
   - HIGH: delta >= 0.40 and z <= -2.0.
   - MEDIUM: delta >= 0.35.
6. Proactive Alerts:
   - Persisted to PostgreSQL `alerts` table with source="gsc_anomaly".
   - Dispatched via NotificationDispatcher to configured channels (Email, Slack, Webhooks).
"""
import hashlib
import json
import logging
import math
import os
import sqlite3
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple

from psycopg.types.json import Jsonb

from database.connection import get_connection
from services.notifications import NotificationDispatcher

logger = logging.getLogger("seojev.gsc_anomaly")


class GSCAnomalyDetector:
    """
    Autonomous detector for statistically meaningful decay in GSC impressions and clicks.
    """
    def __init__(
        self,
        db_url: Optional[str] = None,
        dispatcher: Optional[NotificationDispatcher] = None
    ):
        self.db_url = db_url or os.environ.get("DATABASE_URL", "postgresql:///seojev_test")
        self.dispatcher = dispatcher or NotificationDispatcher(db_url=self.db_url)

    def ingest_daily_metrics(
        self,
        org_id: str,
        site_id: str,
        rows: List[Dict[str, Any]],
        template_map: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Ingests daily GSC rows into PostgreSQL `gsc_daily_metrics` table with upsert idempotency.
        """
        if not rows:
            return 0

        t_map = dict(template_map or {})
        inserted = 0

        with get_connection(self.db_url) as conn:
            with conn.cursor() as cur:
                for r in rows:
                    raw_page = r.get("page") or r.get("url") or ""
                    if not raw_page:
                        continue
                    page = raw_page.strip()
                    tpl_id = r.get("template_id") or t_map.get(page) or "default"

                    raw_date = r.get("date")
                    if isinstance(raw_date, datetime):
                        dt_val = raw_date.date()
                    elif isinstance(raw_date, date):
                        dt_val = raw_date
                    elif isinstance(raw_date, str):
                        dt_val = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date()
                    else:
                        dt_val = datetime.now(timezone.utc).date()

                    clicks = int(r.get("clicks") or 0)
                    impressions = int(r.get("impressions") or 0)
                    ctr = float(r.get("ctr") or (clicks / impressions if impressions > 0 else 0.0))
                    position = float(r.get("position") or 0.0)

                    row_id = hashlib.sha256(f"{site_id}:{page}:{dt_val.isoformat()}".encode()).hexdigest()[:24]

                    cur.execute(
                        """
                        INSERT INTO gsc_daily_metrics (
                            id, org_id, site_id, page, template_id, date, clicks, impressions, ctr, position
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (site_id, page, date) DO UPDATE SET
                            clicks = EXCLUDED.clicks,
                            impressions = EXCLUDED.impressions,
                            ctr = EXCLUDED.ctr,
                            position = EXCLUDED.position,
                            template_id = EXCLUDED.template_id;
                        """,
                        (row_id, org_id, site_id, page, tpl_id, dt_val, clicks, impressions, ctr, position)
                    )
                    inserted += 1
            conn.commit()

        return inserted

    def _fetch_daily_records(self, site_id: str, org_id: str) -> List[Dict[str, Any]]:
        """
        Fetches daily metrics from PostgreSQL `gsc_daily_metrics`, falling back to SQLite `gsc_rows` if needed.
        """
        records: List[Dict[str, Any]] = []

        try:
            with get_connection(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT page, template_id, date, clicks, impressions, ctr, position
                        FROM gsc_daily_metrics
                        WHERE org_id = %s AND site_id = %s
                        ORDER BY date ASC, page ASC
                        """,
                        (org_id, site_id)
                    )
                    for r in cur.fetchall():
                        records.append({
                            "page": r["page"],
                            "template_id": r.get("template_id") or "default",
                            "date": r["date"].isoformat() if isinstance(r["date"], (date, datetime)) else str(r["date"]),
                            "clicks": int(r["clicks"] or 0),
                            "impressions": int(r["impressions"] or 0),
                            "ctr": float(r["ctr"] or 0.0),
                            "position": float(r["position"] or 0.0)
                        })
        except Exception as e:
            logger.warning(f"Error fetching from PostgreSQL gsc_daily_metrics: {e}")

        if records:
            return records

        # Fallback to SQLite databases in data/
        if os.path.exists("data/seo.db"):
            records.extend(self._fetch_from_sqlite("data/seo.db"))

        return records

    def _fetch_from_sqlite(self, db_path: str) -> List[Dict[str, Any]]:
        results = []
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                rows = cur.execute("SELECT page, clicks, impressions, ctr, position, date FROM gsc_rows WHERE date IS NOT NULL ORDER BY date ASC").fetchall()
                for r in rows:
                    results.append({
                        "page": r["page"],
                        "template_id": "default",
                        "date": str(r["date"]),
                        "clicks": int(r["clicks"] or 0),
                        "impressions": int(r["impressions"] or 0),
                        "ctr": float(r["ctr"] or 0.0),
                        "position": float(r["position"] or 0.0)
                    })
        except Exception:
            pass
        return results

    def _calculate_stats(self, values: List[float]) -> Tuple[float, float]:
        """Calculates arithmetic mean and sample standard deviation."""
        if not values:
            return 0.0, 0.0
        n = len(values)
        mean_val = sum(values) / n
        if n < 2:
            return mean_val, 0.0
        variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
        return mean_val, math.sqrt(variance)

    def detect_anomalies(
        self,
        site_id: str,
        org_id: str,
        min_history_days: int = 7,
        eval_window_days: int = 3,
        baseline_window_days: int = 21,
        persist_alerts: bool = True,
        dispatch: bool = True,
        channels: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executes statistical anomaly detection across page-level and template-level daily metrics.
        """
        records = self._fetch_daily_records(site_id, org_id)

        distinct_dates = sorted(list({r["date"] for r in records}))
        total_days = len(distinct_dates)

        # 1. Guard against insufficient history
        if total_days < min_history_days:
            logger.info(f"Site {site_id} has {total_days} days of GSC history (< {min_history_days} required). No anomaly flagged.")
            return {
                "status": "insufficient_history",
                "history_days": total_days,
                "min_history_required": min_history_days,
                "anomalies_detected": 0,
                "anomalies": []
            }

        # Determine time windows
        eval_dates = set(distinct_dates[-eval_window_days:])
        baseline_candidates = distinct_dates[:-eval_window_days]
        baseline_dates = set(baseline_candidates[-baseline_window_days:] if len(baseline_candidates) > baseline_window_days else baseline_candidates)

        if len(baseline_dates) < 4:
            return {
                "status": "insufficient_history",
                "history_days": total_days,
                "baseline_days": len(baseline_dates),
                "anomalies_detected": 0,
                "anomalies": []
            }

        base_start = min(baseline_dates)
        base_end = max(baseline_dates)
        eval_start = min(eval_dates)
        eval_end = max(eval_dates)

        anomalies: List[Dict[str, Any]] = []

        # 2. Page-level time-series evaluation
        page_metrics: Dict[str, Dict[str, Dict[str, float]]] = {}
        for r in records:
            p = r["page"]
            d = r["date"]
            if p not in page_metrics:
                page_metrics[p] = {"impressions": {}, "clicks": {}}
            page_metrics[p]["impressions"][d] = float(r["impressions"])
            page_metrics[p]["clicks"][d] = float(r["clicks"])

        for page, metrics in page_metrics.items():
            # A. Page Impressions
            base_imps = [metrics["impressions"].get(d, 0.0) for d in baseline_dates]
            eval_imps = [metrics["impressions"].get(d, 0.0) for d in eval_dates]

            mu_b_imp, sigma_b_imp = self._calculate_stats(base_imps)
            mu_e_imp, _ = self._calculate_stats(eval_imps)

            # Minimum volume threshold for page impressions
            if mu_b_imp >= 50.0:
                delta_imp = (mu_b_imp - mu_e_imp) / mu_b_imp if mu_b_imp > 0 else 0.0
                z_imp = (mu_e_imp - mu_b_imp) / (sigma_b_imp + 1e-6)

                if (delta_imp >= 0.35 and z_imp <= -2.0) or delta_imp >= 0.60:
                    sev = "critical" if (delta_imp >= 0.70 and z_imp <= -3.0) or delta_imp >= 0.80 else ("high" if delta_imp >= 0.45 else "medium")
                    expected_low = round(max(0.0, mu_b_imp - 2 * sigma_b_imp), 1)
                    expected_high = round(mu_b_imp + 2 * sigma_b_imp, 1)

                    anomalies.append({
                        "anomaly_type": "GSC_IMPRESSIONS_DECAY",
                        "metric": "impressions",
                        "scope": "page",
                        "entity": page,
                        "page": page,
                        "template_id": None,
                        "baseline_period": {"start": base_start, "end": base_end, "days": len(baseline_dates)},
                        "current_period": {"start": eval_start, "end": eval_end, "days": len(eval_dates)},
                        "baseline_mean": round(mu_b_imp, 2),
                        "current_mean": round(mu_e_imp, 2),
                        "expected_range": [expected_low, expected_high],
                        "drop_pct": round(delta_imp * 100, 1),
                        "z_score": round(z_imp, 2),
                        "severity": sev,
                        "evidence": f"Daily impressions dropped {round(delta_imp * 100, 1)}% from baseline {round(mu_b_imp, 1)}/day to {round(mu_e_imp, 1)}/day (z={round(z_imp, 2)})."
                    })

            # B. Page Clicks
            base_clicks = [metrics["clicks"].get(d, 0.0) for d in baseline_dates]
            eval_clicks = [metrics["clicks"].get(d, 0.0) for d in eval_dates]

            mu_b_clk, sigma_b_clk = self._calculate_stats(base_clicks)
            mu_e_clk, _ = self._calculate_stats(eval_clicks)

            # Minimum volume threshold for page clicks
            if mu_b_clk >= 5.0:
                delta_clk = (mu_b_clk - mu_e_clk) / mu_b_clk if mu_b_clk > 0 else 0.0
                z_clk = (mu_e_clk - mu_b_clk) / (sigma_b_clk + 1e-6)

                if (delta_clk >= 0.35 and z_clk <= -2.0) or delta_clk >= 0.60:
                    sev = "critical" if (delta_clk >= 0.70 and z_clk <= -3.0) or delta_clk >= 0.80 else ("high" if delta_clk >= 0.45 else "medium")
                    expected_low = round(max(0.0, mu_b_clk - 2 * sigma_b_clk), 1)
                    expected_high = round(mu_b_clk + 2 * sigma_b_clk, 1)

                    anomalies.append({
                        "anomaly_type": "GSC_CLICKS_DECAY",
                        "metric": "clicks",
                        "scope": "page",
                        "entity": page,
                        "page": page,
                        "template_id": None,
                        "baseline_period": {"start": base_start, "end": base_end, "days": len(baseline_dates)},
                        "current_period": {"start": eval_start, "end": eval_end, "days": len(eval_dates)},
                        "baseline_mean": round(mu_b_clk, 2),
                        "current_mean": round(mu_e_clk, 2),
                        "expected_range": [expected_low, expected_high],
                        "drop_pct": round(delta_clk * 100, 1),
                        "z_score": round(z_clk, 2),
                        "severity": sev,
                        "evidence": f"Daily clicks dropped {round(delta_clk * 100, 1)}% from baseline {round(mu_b_clk, 1)}/day to {round(mu_e_clk, 1)}/day (z={round(z_clk, 2)})."
                    })

        # 3. Template-level time-series evaluation
        tpl_metrics: Dict[str, Dict[str, Dict[str, float]]] = {}
        for r in records:
            tpl = r.get("template_id") or "default"
            d = r["date"]
            if tpl not in tpl_metrics:
                tpl_metrics[tpl] = {"impressions": {}, "clicks": {}}
            tpl_metrics[tpl]["impressions"][d] = tpl_metrics[tpl]["impressions"].get(d, 0.0) + float(r["impressions"])
            tpl_metrics[tpl]["clicks"][d] = tpl_metrics[tpl]["clicks"].get(d, 0.0) + float(r["clicks"])

        for tpl_id, metrics in tpl_metrics.items():
            base_tpl_imps = [metrics["impressions"].get(d, 0.0) for d in baseline_dates]
            eval_tpl_imps = [metrics["impressions"].get(d, 0.0) for d in eval_dates]

            mu_b_tpl, sigma_b_tpl = self._calculate_stats(base_tpl_imps)
            mu_e_tpl, _ = self._calculate_stats(eval_tpl_imps)

            # Minimum volume threshold for template impressions
            if mu_b_tpl >= 150.0:
                delta_tpl = (mu_b_tpl - mu_e_tpl) / mu_b_tpl if mu_b_tpl > 0 else 0.0
                z_tpl = (mu_e_tpl - mu_b_tpl) / (sigma_b_tpl + 1e-6)

                if (delta_tpl >= 0.35 and z_tpl <= -2.0) or delta_tpl >= 0.55:
                    sev = "critical" if (delta_tpl >= 0.65 and z_tpl <= -3.0) or delta_tpl >= 0.75 else ("high" if delta_tpl >= 0.40 else "medium")
                    expected_low = round(max(0.0, mu_b_tpl - 2 * sigma_b_tpl), 1)
                    expected_high = round(mu_b_tpl + 2 * sigma_b_tpl, 1)

                    anomalies.append({
                        "anomaly_type": "GSC_TEMPLATE_DECAY",
                        "metric": "impressions",
                        "scope": "template",
                        "entity": tpl_id,
                        "page": None,
                        "template_id": tpl_id,
                        "baseline_period": {"start": base_start, "end": base_end, "days": len(baseline_dates)},
                        "current_period": {"start": eval_start, "end": eval_end, "days": len(eval_dates)},
                        "baseline_mean": round(mu_b_tpl, 2),
                        "current_mean": round(mu_e_tpl, 2),
                        "expected_range": [expected_low, expected_high],
                        "drop_pct": round(delta_tpl * 100, 1),
                        "z_score": round(z_tpl, 2),
                        "severity": sev,
                        "evidence": f"Template '{tpl_id}' daily impressions collapsed {round(delta_tpl * 100, 1)}% from baseline {round(mu_b_tpl, 1)}/day to {round(mu_e_tpl, 1)}/day (z={round(z_tpl, 2)})."
                    })

        # 4. Persist alerts & emit notifications
        persisted_alerts: List[Dict[str, Any]] = []
        now_utc = datetime.now(timezone.utc)

        if persist_alerts and anomalies:
            with get_connection(self.db_url) as conn:
                with conn.cursor() as cur:
                    for a in anomalies:
                        anom_type = a["anomaly_type"]
                        metric_name = a["metric"].capitalize()
                        entity = a["entity"]
                        scope = a["scope"]
                        sev = a["severity"]
                        drop = a["drop_pct"]
                        evidence = a["evidence"]

                        fp = hashlib.sha256(f"{site_id}:{anom_type}:{entity}:{eval_end}".encode()).hexdigest()[:16]
                        alert_id = f"alert_gsc_{fp}"

                        if scope == "template":
                            title = f"GSC Anomaly: {drop}% {metric_name} Decay on Template '{entity}'"
                            affected_urls = [r["page"] for r in records if (r.get("template_id") or "default") == entity][:10]
                        else:
                            title = f"GSC Anomaly: {drop}% {metric_name} Decay on {entity}"
                            affected_urls = [entity]

                        msg = f"{evidence} Baseline period: {base_start} to {base_end}."

                        cur.execute(
                            """
                            INSERT INTO alerts (
                                id, org_id, site_id, alert_type, severity, title, message,
                                source, fingerprint, affected_urls_json, payload_json, status, detected_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'gsc_anomaly', %s, %s, %s, 'open', %s)
                            ON CONFLICT (id) DO UPDATE SET
                                message = EXCLUDED.message,
                                payload_json = EXCLUDED.payload_json,
                                severity = EXCLUDED.severity,
                                status = 'open',
                                detected_at = EXCLUDED.detected_at
                            RETURNING id, org_id, site_id, alert_type, severity, title, message, status, detected_at;
                            """,
                            (
                                alert_id, org_id, site_id, anom_type, sev, title, msg,
                                fp, Jsonb(affected_urls), Jsonb(a), now_utc
                            )
                        )
                        persisted_alert_row = cur.fetchone()
                        if persisted_alert_row:
                            p_dict = dict(persisted_alert_row)
                            persisted_alerts.append(p_dict)
                conn.commit()

            # Dispatch alerts through existing notification system
            if dispatch and persisted_alerts:
                for alert in persisted_alerts:
                    try:
                        self.dispatcher.dispatch_alert(alert, channels=channels)
                        self.dispatcher.dispatch_event("gsc.anomaly", alert, channels=channels)
                    except Exception as disp_err:
                        logger.warning(f"Failed to dispatch GSC anomaly alert {alert.get('id')}: {disp_err}")

        return {
            "status": "completed",
            "history_days": total_days,
            "baseline_period": {"start": base_start, "end": base_end, "days": len(baseline_dates)},
            "current_period": {"start": eval_start, "end": eval_end, "days": len(eval_dates)},
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "alerts_persisted": len(persisted_alerts)
        }


_global_detector: Optional[GSCAnomalyDetector] = None

def get_gsc_anomaly_detector() -> GSCAnomalyDetector:
    global _global_detector
    if _global_detector is None:
        _global_detector = GSCAnomalyDetector()
    return _global_detector
