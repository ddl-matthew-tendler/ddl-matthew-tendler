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
