"""
backend/services/notification_engine.py
========================================
Phase 19 — Resilience Orchestration, Incident Management & Automated Alerting

Notification Engine providing an extensible provider architecture.
Implements InAppNotificationProvider for Phase 19, managing in-app notifications
with UNREAD, READ, and DISMISSED statuses.
"""

import time
from typing import Dict, Any, List, Optional


class NotificationProvider:
    """Base interface for notification dispatchers."""
    def send(self, notification_data: Dict[str, Any]) -> bool:
        raise NotImplementedError


class InAppNotificationProvider(NotificationProvider):
    """In-App Notification Dispatcher & Management Engine."""

    def __init__(self):
        self.notifications: List[Dict[str, Any]] = []

    def send(self, notification_data: Dict[str, Any]) -> bool:
        self.notifications.insert(0, notification_data)
        if len(self.notifications) > 200:
            self.notifications.pop()
        return True

    def create_notification(
        self,
        incident_id: str,
        site_id: str,
        recipient_role: str,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "HIGH"
    ) -> Dict[str, Any]:
        notif = {
            "notification_id": f"NOTIF-{int(time.time() * 1000)}",
            "incident_id": incident_id,
            "site_id": site_id,
            "recipient_role": recipient_role,
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "severity": severity,
            "status": "UNREAD",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "read_at": None
        }
        self.send(notif)
        return notif

    def get_all_notifications(self, unread_only: bool = False, site_id: str = None) -> List[Dict[str, Any]]:
        res = self.notifications
        if unread_only:
            res = [n for n in res if n["status"] == "UNREAD"]
        if site_id and site_id != "ALL":
            res = [n for n in res if n["site_id"] == site_id]
        return res

    def mark_as_read(self, notification_id: str) -> bool:
        for n in self.notifications:
            if n["notification_id"] == notification_id:
                n["status"] = "READ"
                n["read_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                return True
        return False

    def mark_all_read(self) -> int:
        count = 0
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        for n in self.notifications:
            if n["status"] == "UNREAD":
                n["status"] = "READ"
                n["read_at"] = now_str
                count += 1
        return count


notification_engine = InAppNotificationProvider()
