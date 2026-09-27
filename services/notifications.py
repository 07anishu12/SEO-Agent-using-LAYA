"""
SEOJEV Stage 9 Notification Dispatcher:
Fans out events (run.completed, run.failed, regression.detected, watch.alert)
to Slack incoming webhooks, Email sinks (SMTP or InMemory for testing), and Generic outgoing webhooks.
Enforces channel-level delivery isolation (failure in one channel does not prevent delivery to others).
Persists delivery confirmation back to PostgreSQL alerts ledger.
"""
import os
import json
import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from psycopg.types.json import Jsonb

from database.connection import get_connection

logger = logging.getLogger("seojev.notifications")


class InMemoryEmailSink:
    """Thread-safe email sink for tests and local verification."""
    def __init__(self):
        self._lock = threading.Lock()
        self._messages: List[Dict[str, Any]] = []

    def record(self, message: Dict[str, Any]):
        with self._lock:
            self._messages.append(message)

    def get_messages(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._messages)

    def clear(self):
        with self._lock:
            self._messages.clear()


# Global in-memory email sink for test verification
global_test_email_sink = InMemoryEmailSink()


class NotificationDispatcher:
    def __init__(
        self,
        db_url: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
        email_sink: Optional[InMemoryEmailSink] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None
    ):
        self.db_url = db_url
        self.http_client = http_client or httpx.Client(timeout=10.0)
        self.email_sink = email_sink or global_test_email_sink
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "25"))

    def get_channels_for_site(self, org_id: str, site_id: str) -> List[Dict[str, Any]]:
        """Retrieves configured notification channels from watch_configs, with env fallback."""
        channels = []
        try:
            with get_connection(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT notification_channels_json FROM watch_configs WHERE org_id = %s AND site_id = %s",
                        (org_id, site_id)
                    )
                    row = cur.fetchone()
                    if row and row.get("notification_channels_json"):
                        raw = row["notification_channels_json"]
                        channels = raw if isinstance(raw, list) else json.loads(raw)
        except Exception as exc:
            logger.warning(f"Error fetching watch notification channels: {exc}")

        # Check environment fallbacks if no channels configured on site
        if not channels:
            slack_url = os.environ.get("SLACK_WEBHOOK_URL")
            if slack_url:
                channels.append({"type": "slack", "webhook_url": slack_url})
            email_recipients = os.environ.get("ALERT_EMAIL_RECIPIENTS")
            if email_recipients:
                recips = [r.strip() for r in email_recipients.split(",") if r.strip()]
                channels.append({"type": "email", "recipients": recips})
            webhook_url = os.environ.get("OUTGOING_WEBHOOK_URL")
            if webhook_url:
                channels.append({"type": "webhook", "url": webhook_url})

        return channels

    def _send_slack(self, webhook_url: str, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches formatted message to Slack incoming webhook."""
        title = data.get("title") or f"SEOJEV Notification: {event_type}"
        message = data.get("message") or data.get("summary") or json.dumps(data)
        severity = (data.get("severity") or "info").upper()

        color = "#e11d48" if severity == "CRITICAL" else ("#f59e0b" if severity == "HIGH" else "#0ea5e9")

        payload = {
            "text": f"[{severity}] {title}: {message}",
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "fields": [
                        {"title": "Event", "value": event_type, "short": True},
                        {"title": "Severity", "value": severity, "short": True},
                        {"title": "Site", "value": data.get("site_id", "N/A"), "short": True},
                        {"title": "Timestamp", "value": data.get("detected_at") or datetime.now(timezone.utc).isoformat(), "short": True}
                    ]
                }
            ]
        }
        resp = self.http_client.post(webhook_url, json=payload, headers={"Content-Type": "application/json"})
        if resp.status_code >= 400:
            raise RuntimeError(f"Slack webhook returned HTTP {resp.status_code}: {resp.text}")
        return {"status_code": resp.status_code, "body": resp.text}

    def _send_email(self, recipients: List[str], event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches notification to email recipients via SMTP or InMemoryEmailSink."""
        if not recipients:
            return {"status": "skipped", "reason": "no_recipients"}

        title = data.get("title") or f"SEOJEV Notification: {event_type}"
        severity = (data.get("severity") or "info").upper()
        subject = f"[SEOJEV {severity}] {title}"
        body = (
            f"Event: {event_type}\n"
            f"Severity: {severity}\n"
            f"Site ID: {data.get('site_id', 'N/A')}\n"
            f"Message: {data.get('message', '')}\n\n"
            f"Affected URLs: {json.dumps(data.get('affected_urls', data.get('affected_urls_json', [])))}\n"
            f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
        )

        # Record in test sink
        self.email_sink.record({
            "recipients": recipients,
            "subject": subject,
            "body": body,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # If live SMTP host configured, attempt SMTP send
        if self.smtp_host:
            msg = MIMEMultipart()
            msg["From"] = os.environ.get("SMTP_FROM", "alerts@seojev.io")
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5) as server:
                server.send_message(msg)

        return {"status": "delivered", "recipients": recipients, "subject": subject}

    def _send_webhook(self, url: str, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches structured JSON to generic outgoing webhook."""
        envelope = {
            "event": event_type,
            "event_id": f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SEOJEV-Notification-Dispatcher/2.0",
            "X-SEOJEV-Event": event_type
        }
        resp = self.http_client.post(url, json=envelope, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Outgoing webhook returned HTTP {resp.status_code}: {resp.text}")
        return {"status_code": resp.status_code}

    def dispatch_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        channels: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Dispatches an event across channels with delivery isolation.
        Supported events: run.completed, run.failed, regression.detected, watch.alert
        """
        org_id = payload.get("org_id", "")
        site_id = payload.get("site_id", "")

        active_channels = channels
        if not active_channels and org_id and site_id:
            active_channels = self.get_channels_for_site(org_id, site_id)

        results: Dict[str, Any] = {"slack": [], "email": [], "webhook": []}
        errors: List[str] = []

        for ch in (active_channels or []):
            ch_type = ch.get("type", "").lower()
            try:
                if ch_type == "slack":
                    url = ch.get("webhook_url") or ch.get("url")
                    if url:
                        res = self._send_slack(url, event_type, payload)
                        results["slack"].append({"success": True, "details": res})
                elif ch_type == "email":
                    recipients = ch.get("recipients", [])
                    if isinstance(recipients, str):
                        recipients = [r.strip() for r in recipients.split(",") if r.strip()]
                    res = self._send_email(recipients, event_type, payload)
                    results["email"].append({"success": True, "details": res})
                elif ch_type == "webhook":
                    url = ch.get("url") or ch.get("webhook_url")
                    if url:
                        res = self._send_webhook(url, event_type, payload)
                        results["webhook"].append({"success": True, "details": res})
            except Exception as exc:
                err_msg = f"{ch_type} channel error: {str(exc)}"
                logger.error(err_msg)
                errors.append(err_msg)
                results.setdefault(ch_type, []).append({"success": False, "error": str(exc)})

        # Update alerts ledger if an alert ID was included
        alert_id = payload.get("id") or payload.get("alert_id")
        if alert_id:
            dispatched_ok = len(errors) == 0
            status_val = "delivered" if dispatched_ok else "partial_failure"
            err_text = "; ".join(errors) if errors else None
            try:
                with get_connection(self.db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE alerts
                            SET dispatched = %s,
                                dispatch_status = %s,
                                dispatch_error = %s
                            WHERE id = %s
                            """,
                            (dispatched_ok, status_val, err_text, alert_id)
                        )
                    conn.commit()
            except Exception as db_err:
                logger.warning(f"Failed to update alert dispatch status: {db_err}")

        return {
            "event": event_type,
            "delivered": len(errors) == 0,
            "channel_results": results,
            "errors": errors
        }

    def dispatch_alert(self, alert: Dict[str, Any], channels: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Convenience method to dispatch a watch.alert or regression.detected."""
        event_name = "regression.detected" if alert.get("source") == "regression" or alert.get("alert_type") in (
            "NOINDEX_LEAK", "CANONICAL_CHANGE", "STATUS_5XX_SPIKE", "SITEMAP_DROP"
        ) else "watch.alert"
        return self.dispatch_event(event_name, alert, channels=channels)


_dispatcher_instance: Optional[NotificationDispatcher] = None

def get_notification_dispatcher() -> NotificationDispatcher:
    global _dispatcher_instance
    if _dispatcher_instance is None:
        _dispatcher_instance = NotificationDispatcher()
    return _dispatcher_instance
