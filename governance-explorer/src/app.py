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
