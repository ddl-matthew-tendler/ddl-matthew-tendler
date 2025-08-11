from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd

def parse_dt(val) -> Optional[pd.Timestamp]:
    if val is None or val == "": return None
    try:
        ts = pd.to_datetime(val, utc=True)
        if isinstance(ts, pd.Timestamp) and ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return ts
    except Exception:
        return None

def order_stages_like_humans(names: List[str]) -> List[str]:
    seen, out = set(), []
    for n in names:
        if n and n not in seen:
            out.append(n); seen.add(n)
    return out

def stage_assignee_for_name(stages: List[Dict[str,Any]], stage_name: str) -> str:
    for s in stages:
        nm = (s.get("stage") or {}).get("name")
        if nm == stage_name:
            a = s.get("assignee") or {}
            return a.get("name") or "Unassigned"
    return "Unassigned"

def compute_last_updated(bundle: Dict[str,Any]):
    cands = [parse_dt(bundle.get("createdAt"))]
    for att in bundle.get("attachments", []):
        cands.append(parse_dt(att.get("createdAt")))
    cands = [c for c in cands if c is not None]
    return max(cands) if cands else None

def current_stage_assignee(bundle: Dict[str,Any]) -> str:
    target = bundle.get("stage")
    for s in bundle.get("stages", []):
        if (s.get("stage") or {}).get("name") == target:
            a = s.get("assignee") or {}
            return a.get("name") or "Unassigned"
    return "Unassigned"

def days_in_current_stage(bundle: Dict[str,Any]) -> int:
    ts = compute_last_updated(bundle)
    if not ts: return -1
    return int((pd.Timestamp.utcnow().tz_localize("UTC") - ts).days)

def safe_branch_from_attachments(atts: List[Dict[str,Any]]) -> str:
    # find most recent report attachment with a branch field
    if not atts: return ""
    def key(a):
        t = parse_dt(a.get("createdAt"))
        return t if t is not None else pd.Timestamp.min.tz_localize("UTC")
    for a in sorted(atts, key=key, reverse=True):
        ident = a.get("identifier") or {}
        b = ident.get("branch")
        if b: return b
    return ""
