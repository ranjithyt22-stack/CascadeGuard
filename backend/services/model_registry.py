"""
backend/services/model_registry.py
==================================
Phase 20 — Continuous Learning, Adaptive AI & Predictive Maintenance Intelligence

Model Registry managing model lifecycle, version control, evaluation metrics,
safe model activation, and rollback capabilities.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "model_registry.json"


class ModelRegistry:
    """Manages model metadata persistence, active status, and rollback."""

    def __init__(self, registry_path: Path = DEFAULT_REGISTRY_PATH):
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.models: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self._load_from_disk()

    def _load_from_disk(self):
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.models = data.get("models", {})
                    self.audit_log = data.get("audit_log", [])
            except Exception as e:
                print(f"Error loading model registry: {e}")
                self.models = {}
                self.audit_log = []
        else:
            self._save_to_disk()

    def _save_to_disk(self):
        try:
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump({
                    "models": self.models,
                    "audit_log": self.audit_log,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving model registry: {e}")

    def register_model(
        self,
        model_id: str,
        version: str,
        model_type: str,
        dataset_version: str,
        features: List[str],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Registers a newly trained and evaluated ML model."""
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "model_id": model_id,
            "version": version,
            "model_type": model_type,
            "training_dataset_version": dataset_version,
            "features": features,
            "metrics": metrics,
            "status": "VALIDATED",
            "created_at": now_str,
            "activated_at": None,
            "retired_at": None
        }

        self.models[model_id] = record
        self.log_audit_event("MODEL_REGISTERED", model_id, "MLTrainingEngine", f"Registered model {version} with F1={metrics.get('f1', 0.0)}")
        self._save_to_disk()
        return record

    def get_active_model(self) -> Optional[Dict[str, Any]]:
        """Returns the currently active prediction model."""
        for m in self.models.values():
            if m.get("status") == "ACTIVE":
                return m
        return None

    def get_all_models(self) -> List[Dict[str, Any]]:
        """Returns all registered models sorted by creation time."""
        res = list(self.models.values())
        res.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return res

    def activate_model(self, model_id: str, actor: str = "Operator") -> bool:
        """Activates a target model and retires the currently active model."""
        if model_id not in self.models:
            return False

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        # Retire existing active model
        for m in self.models.values():
            if m.get("status") == "ACTIVE":
                m["status"] = "RETIRED"
                m["retired_at"] = now_str

        # Activate target model
        target = self.models[model_id]
        target["status"] = "ACTIVE"
        target["activated_at"] = now_str

        self.log_audit_event("MODEL_ACTIVATED", model_id, actor, f"Activated model {target.get('version')}")
        self._save_to_disk()
        return True

    def rollback_model(self, actor: str = "Operator") -> Optional[Dict[str, Any]]:
        """Rolls back to the most recently retired/validated model."""
        active = self.get_active_model()
        retired_models = [
            m for m in self.models.values()
            if m.get("status") in ["RETIRED", "VALIDATED"] and (not active or m["model_id"] != active["model_id"])
        ]

        if not retired_models:
            return None

        # Sort by creation time descending
        retired_models.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        prev_model = retired_models[0]

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        if active:
            active["status"] = "RETIRED"
            active["retired_at"] = now_str

        prev_model["status"] = "ACTIVE"
        prev_model["activated_at"] = now_str

        self.log_audit_event("MODEL_ROLLED_BACK", prev_model["model_id"], actor, f"Rolled back to model {prev_model.get('version')}")
        self._save_to_disk()
        return prev_model

    def log_audit_event(self, operation: str, model_id: str, actor: str, details: str):
        self.audit_log.insert(0, {
            "event_id": f"EVT-{int(time.time()*1000)}",
            "operation": operation,
            "model_id": model_id,
            "actor": actor,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        if len(self.audit_log) > 100:
            self.audit_log.pop()


model_registry = ModelRegistry()
