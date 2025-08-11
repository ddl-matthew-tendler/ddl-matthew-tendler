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
