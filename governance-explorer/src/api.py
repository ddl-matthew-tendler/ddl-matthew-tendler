from __future__ import annotations
import json, os
from typing import Any, Dict, List, Optional
import requests
from .config import get_api_host, get_api_key, offline_mode

HEADERS = lambda: {"X-Domino-Api-Key": get_api_key(), "Accept": "application/json"}
HOST = lambda: get_api_host()

def _get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(url, headers=HEADERS(), params=params or {}, timeout=30)
        if r.status_code != 200: return None
        return r.json()
    except Exception:
        return None

def fetch_bundles(limit: int = 1000):
    if offline_mode():
        with open(os.path.join("data","sample_bundles.json")) as f:
            return json.load(f)["data"]
    data = _get(f"{HOST()}/api/governance/v1/bundles", {"limit": limit}) or {}
    return data.get("data") or data.get("bundles") or []

def fetch_audit_events(params: Dict[str, Any]):
    if offline_mode():
        with open(os.path.join("data","sample_events.json")) as f:
            return json.load(f)
    return _get(f"{HOST()}/api/audittrail/v1/auditevents", params) or {"events": [], "estimatedMatches": 0}
