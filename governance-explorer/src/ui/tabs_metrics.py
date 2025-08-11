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
