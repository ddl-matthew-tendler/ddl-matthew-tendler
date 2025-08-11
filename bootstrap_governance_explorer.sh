#!/usr/bin/env bash
set -euo pipefail

# Root folder (use "." to put files at repo root)
APP_DIR="governance-explorer"

mkdir -p "$APP_DIR"/{src/ui,data}
cd "$APP_DIR"

# ----------------------------- small files -----------------------------
cat > README.md <<'MD'
# Governance Explorer App

Streamlit app with three tabs: **All Bundles**, **Bundle History**, **Metrics**.
Works locally (Cursor) and on Domino (DFS/Git-based).
MD

cat > requirements.txt <<'REQ'
streamlit==1.36.0
pandas>=2.0
requests>=2.31
python-dateutil>=2.9
REQ

cat > .env.example <<'ENV'
API_HOST=https://govqcexploratory.domino.tech
DOMINO_USER_API_KEY=YOUR_LOCAL_TOKEN_HERE
OFFLINE=false
ENV

cat > .gitignore <<'GI'
__pycache__/
*.pyc
.venv/
.env
.streamlit/
GI

cat > .cursorignore <<'CI'
data/sample_bundles.json
data/sample_events.json
.venv/
.streamlit/
CI

cat > .cursorrules <<'CR'
You’re helping maintain a Streamlit app called “Governance Explorer”.
- Entry: src/app.py
- HTTP goes only in src/api.py
- Data-only helpers in src/transforms.py
- UI tabs live in src/ui/*
- Config/env logic in src/config.py
- OFFLINE=true reads fixtures from ./data
Keep functions small and pure.
CR

cat > Makefile <<'MK'
.PHONY: setup dev run
setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install -U pip -r requirements.txt
dev:
	. .venv/bin/activate && streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
run:
	streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
MK

cat > run_local.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [ -f .env ]; then export $(grep -v '^#' .env | xargs -d '\n'); fi
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
SH
chmod +x run_local.sh

cat > run_domino.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
streamlit run src/app.py --server.port="${DOMINO_APP_PORT:-8888}" --server.address=0.0.0.0
SH
chmod +x run_domino.sh

# ----------------------------- python files -----------------------------
cat > src/config.py <<'PY'
import os
def get_api_host() -> str:
    return os.getenv("API_HOST", "https://govqcexploratory.domino.tech")
def get_api_key() -> str:
    return os.getenv("DOMINO_USER_API_KEY", "")
def offline_mode() -> bool:
    return os.getenv("OFFLINE", "false").lower() == "true"
PY

cat > src/api.py <<'PY'
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
PY

cat > src/transforms.py <<'PY'
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
PY

cat > src/ui/tabs_all_bundles.py <<'PY'
import pandas as pd
import streamlit as st
from typing import List, Dict, Any
from ..api import fetch_bundles
from ..transforms import (
    parse_dt, order_stages_like_humans, stage_assignee_for_name,
    current_stage_assignee, compute_last_updated, days_in_current_stage,
    safe_branch_from_attachments
)

def render():
    st.caption("Current state of all governance bundles.")
    bundles = fetch_bundles(limit=1000)
    if not bundles:
        st.info("No bundles returned."); return

    bundles_sorted = sorted(bundles, key=lambda b: (b.get("name") or "").lower())
    rows: List[Dict[str,Any]] = []

    for b in bundles_sorted:
        name = b.get("name","")
        state = b.get("state","")
        curr_stage = b.get("stage","")
        curr_assignee = current_stage_assignee(b)
        last_updated = compute_last_updated(b)
        project = b.get("projectName","")
        policy = b.get("policyName","")
        created = parse_dt(b.get("createdAt"))
        owner = b.get("projectOwner") or (b.get("createdBy") or {}).get("userName") or ""
        stage_names_present = [(s.get("stage") or {}).get("name") for s in b.get("stages", []) if (s.get("stage") or {}).get("name")]
        ordered_names = order_stages_like_humans(stage_names_present)[:4]
        s1, s2, s3, s4 = (ordered_names + ["","","",""])[:4]

        rows.append({
            "Bundle Name": name,
            "State": state,
            "Current Stage": curr_stage,
            "Current Stage Assignee": curr_assignee,
            "Last Updated": last_updated.isoformat().replace("+00:00","Z") if last_updated else "",
            "Project Name": project,
            "Policy Name": policy,
            "Date bundle created": created.isoformat().replace("+00:00","Z") if created else "",
            "Owner of bundle": owner,
            "Stage 1 Name": s1,
            "Stage 1 Assignee": stage_assignee_for_name(b.get("stages", []), s1) if s1 else "Unassigned",
            "Stage 2 Name": s2,
            "Stage 2 Assignee": stage_assignee_for_name(b.get("stages", []), s2) if s2 else "Unassigned",
            "Stage 3 Name": s3,
            "Stage 3 Assignee": stage_assignee_for_name(b.get("stages", []), s3) if s3 else "Unassigned",
            "Stage 4 Name": s4,
            "Stage 4 Assignee": stage_assignee_for_name(b.get("stages", []), s4) if s4 else "Unassigned",
            "Repo Branch": safe_branch_from_attachments(b.get("attachments", [])),
            "Bundle ID": b.get("id",""),
            "_days_in_stage": days_in_current_stage(b)
        })

    df_all = pd.DataFrame(rows)
    st.dataframe(df_all.drop(columns=["_days_in_stage"]), use_container_width=True)
PY

cat > src/ui/tabs_history.py <<'PY'
import json
import pandas as pd
import streamlit as st
from typing import Any, Dict, List, Tuple
from ..api import fetch_bundles, fetch_audit_events
from ..transforms import parse_dt

EVENT_CATALOG = [
    "Create Governance Bundle",
    "Change Governance Bundle Stage",
    "Change Governance Bundle State",
    "Create Governance Bundle Stage Approval Request",
    "Accept Governance Bundle Stage Approval Request",
    "Update Governance Bundle Stage Assignee",
    "Add Policy to Governance Bundle",
    "Deactivate Policy in Governance Bundle",
    "Add Attachment to Bundle",
    "Remove Attachment from Bundle",
    "Submit Results in a Bundle",
    "Copy Governance Bundle results from another Bundle",
]

def _pull_stage_name(e: Dict[str,Any]) -> str:
    for a in e.get("affecting", []):
        if a.get("entityType") == "governancePolicyStage" and a.get("name"):
            return a["name"]
    for t in e.get("targets", []):
        for fc in t.get("fieldChanges", []):
            if fc.get("fieldName") == "stage":
                return f'{fc.get("before") or ""} → {fc.get("after") or ""}'
    return ""

def _before_after(e: Dict[str,Any]):
    for t in e.get("targets", []):
        for fc in t.get("fieldChanges", []):
            field = fc.get("fieldName")
            if field in ("stage","state"):
                return str(fc.get("before") or ""), str(fc.get("after") or ""), field
            if field == "assignee":
                added = fc.get("added") or []
                removed = fc.get("removed") or []
                b = removed[0].get("name") if removed and removed[0].get("name") else "Unassigned"
                a = added[0].get("name") if added and added[0].get("name") else "Unassigned"
                return b, a, "assignee"
    return "", "", ""

def render():
    st.caption("Audit history for a selected bundle (governance-related events only).")
    bundles = fetch_bundles(limit=1000)
    names = sorted({b.get("name","") for b in bundles if b.get("name")}, key=str.lower)
    selected_name = st.selectbox("Select bundle", options=names, index=0 if names else None, placeholder="Choose a bundle…")

    col_ev, col_proj = st.columns([3,3])
    with col_ev:
        ev_choices = st.multiselect("Event filter (optional)", options=EVENT_CATALOG, default=[], placeholder="Leave empty to show all")
    with col_proj:
        projects = sorted({b.get("projectName","") for b in bundles if b.get("projectName")})
        proj_filter = st.multiselect("Project filter (optional)", options=projects, default=[])

    start_iso = st.text_input("Start (UTC)", placeholder="YYYY/MM/DD")
    end_iso   = st.text_input("End (UTC)",   placeholder="YYYY/MM/DD")

    if not selected_name:
        st.info("Pick a bundle to see its audit trail."); return

    cand = [b for b in bundles if b.get("name")==selected_name]
    cand.sort(key=lambda x: parse_dt(x.get("createdAt")) or pd.Timestamp.min.tz_localize("UTC"), reverse=True)
    bundle_id = cand[0].get("id") if cand else None
    if not bundle_id: st.warning("Couldn't find that bundle."); return

    params = {"targetType":"governanceBundle","targetId":bundle_id,"limit":500,"sort":"-timestamp"}
    if start_iso:
        try: pd.to_datetime(start_iso); params["since"] = start_iso if "T" in start_iso else start_iso+"T00:00:00Z"
        except: pass
    if end_iso:
        try: pd.to_datetime(end_iso); params["until"] = end_iso if "T" in end_iso else end_iso+"T23:59:59Z"
        except: pass

    raw = fetch_audit_events(params)
    events = raw.get("events", [])

    def keep(e):
        ok = True
        if ev_choices: ok = ok and ((e.get("action") or {}).get("eventName") in ev_choices)
        if proj_filter: ok = ok and ((e.get("in") or {}).get("name") in proj_filter)
        return ok

    filtered = [e for e in events if keep(e)]
    rows = []
    for e in filtered:
        ts = parse_dt(e.get("timestamp"))
        b, a, field = _before_after(e)
        bundle_nm = ""
        for t in e.get("targets", []):
            ent = t.get("entity") or {}
            if ent.get("entityType") == "governanceBundle":
                bundle_nm = ent.get("name") or bundle_nm

        rows.append({
            "Time (UTC)": ts.isoformat().replace("+00:00","Z") if ts else "",
            "Action": (e.get("action") or {}).get("eventName") or "",
            "Stage": _pull_stage_name(e),
            "User": (e.get("actor") or {}).get("name") or "",
            "Project": (e.get("in") or {}).get("name") or "",
            "Bundle": bundle_nm,
            "Before": b, "After": a, "Change": field, "Notes": "",
            "_raw_fieldChanges": json.dumps([(t.get("fieldChanges") or []) for t in e.get("targets", [])], indent=2)
        })

    if not rows:
        st.info("No audit trail events found for this bundle with the current filters."); return

    df = pd.DataFrame(rows)
    st.dataframe(df.drop(columns=["_raw_fieldChanges"]), use_container_width=True, height=380)
    with st.expander("Show raw field changes for each row"):
        st.dataframe(df[["_raw_fieldChanges"]], use_container_width=True, height=240)
PY

cat > src/ui/tabs_metrics.py <<'PY'
import pandas as pd
import streamlit as st
from typing import List, Dict, Any
from ..api import fetch_bundles
from ..transforms import current_stage_assignee, days_in_current_stage

def render():
    st.caption("Which bundles have been sitting in the same stage the longest?")
    bundles = fetch_bundles(limit=1000)
    rows: List[Dict[str,Any]] = []
    for b in bundles:
        rows.append({
            "Bundle Name": b.get("name",""),
            "Project Name": b.get("projectName",""),
            "Policy Name": b.get("policyName",""),
            "Current Stage": b.get("stage",""),
            "Current Stage Assignee": current_stage_assignee(b),
            "Days in Current Stage": days_in_current_stage(b),
        })
    if not rows:
        st.info("No bundles available."); return
    df = pd.DataFrame(rows)
    df["Days in Current Stage"] = pd.to_numeric(df["Days in Current Stage"], errors="coerce").fillna(-1)
    st.dataframe(df.sort_values("Days in Current Stage", ascending=False, na_position="last"), use_container_width=True)
    top = df[df["Days in Current Stage"] >= 0].nlargest(15, "Days in Current Stage")
    if not top.empty:
        st.bar_chart(top.set_index("Bundle Name")["Days in Current Stage"], use_container_width=True)
PY

cat > src/app.py <<'PY'
import streamlit as st
from ui.tabs_all_bundles import render as render_all
from ui.tabs_history import render as render_history
from ui.tabs_metrics import render as render_metrics

st.set_page_config(page_title="Governance Explorer App", layout="wide")
st.title("Governance Explorer App")
tab1, tab2, tab3 = st.tabs(["All Bundles", "Bundle History", "Metrics"])
with tab1: render_all()
with tab2: render_history()
with tab3: render_metrics()
PY

# ----------------------------- sample fixtures -----------------------------
cat > data/sample_bundles.json <<'J'
{"data":[]}
J
cat > data/sample_events.json <<'J'
{"events":[],"estimatedMatches":0}
J

# ----------------------------- git add/commit ------------------------------
cd ..
git add "$APP_DIR"
git commit -m "Scaffold Governance Explorer (auto-generated)"
echo "Done. Files created under: $APP_DIR"
