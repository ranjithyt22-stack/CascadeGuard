"""
CascadeGuard AI — Automated Alert Webhook Manager
Phase 13: Incident Intelligence + Automated Alerting + Executive Report

Manages webhook alert notifications for CRITICAL & WARNING incidents.
Fails safely without breaking core system API execution if webhook endpoint is unreachable.
"""

import os
import requests
import json
import time


class AlertManager:
    def __init__(self):
        self.webhook_url = os.environ.get("ALERT_WEBHOOK_URL", None)
        env_enabled = os.environ.get("ALERT_WEBHOOK_ENABLED", "False").lower()
        self.enabled = env_enabled in ["true", "1", "yes"]

    def set_webhook_config(self, url, enabled=True):
        self.webhook_url = url
        self.enabled = enabled

    def get_status(self):
        return {
            "webhook_url": self.webhook_url if self.webhook_url else "NOT_CONFIGURED",
            "enabled": self.enabled,
            "status": "ACTIVE" if (self.enabled and self.webhook_url) else "DISABLED"
        }

    def dispatch_alert(self, incident):
        """
        Dispatches alert JSON payload to configured webhook endpoint.
        Returns dictionary indicating notification status.
        """
        if not self.enabled or not self.webhook_url:
            return {
                "notification_status": "SKIPPED",
                "reason": "Alert webhook is disabled or URL not configured"
            }

        payload = {
            "alert_type": "CASCADEGUARD_INFRASTRUCTURE_INCIDENT",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "incident_id": incident.get("incident_id"),
            "severity": incident.get("severity"),
            "system_risk": incident.get("system_risk"),
            "most_vulnerable_asset": incident.get("most_vulnerable_asset"),
            "trigger": incident.get("trigger"),
            "data_sources": incident.get("data_sources"),
            "recommended_actions": incident.get("recommended_actions", {}).get("actions", [])
        }

        try:
            res = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=3.0
            )
            if res.status_code in [200, 201, 202]:
                return {
                    "notification_status": "DELIVERED",
                    "status_code": res.status_code
                }
            else:
                return {
                    "notification_status": "FAILED",
                    "reason": f"Webhook returned HTTP status {res.status_code}"
                }
        except Exception as e:
            # Must NOT crash system operation on webhook failure
            print(f"[AlertManager] Webhook dispatch warning: {e}")
            return {
                "notification_status": "FAILED",
                "reason": str(e)
            }
