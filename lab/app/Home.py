from __future__ import annotations

import streamlit as st

from lab.core.settings import load_settings
from lab.core.workspace import WorkspaceManager


st.set_page_config(page_title="Nass — Intelligent PDF Content Extraction", layout="wide")
settings = load_settings()
manager = WorkspaceManager(settings)
manager.sweep_expired()

st.title("Nass")
st.caption("Intelligent PDF Content Extraction")

if "workspace_id" not in st.session_state:
    st.session_state.workspace_id = manager.create().workspace_id

workspace = manager.attach(st.session_state.workspace_id)
st.code(workspace.workspace_id)
st.text(f"Created: {workspace.created_at.isoformat()}")
st.text(f"Last activity: {workspace.updated_at.isoformat()}")
st.info("Nass runs on this computer. Uploaded files and extracted text stay local; only the page and region images you choose to process with OCR are sent, to the Qari service you configure.")

col1, col2 = st.columns(2)
if col1.button("New workspace"):
    st.session_state.workspace_id = manager.create().workspace_id
    st.rerun()
if col2.button("End workspace (delete everything)", type="secondary"):
    manager.end(workspace.workspace_id)
    st.session_state.clear()
    st.rerun()

recent = manager.list_recent()
choices = [
    item.workspace_id for item in recent if item.workspace_id != workspace.workspace_id
]
if choices:
    selected = st.selectbox("Attach to a recent workspace", choices)
    if st.button("Attach"):
        manager.attach(selected)
        st.session_state.workspace_id = selected
        st.rerun()

st.markdown(
    "Use **Documents** to upload a PDF, **Run Text Extraction** to run the four local extractors, "
    "then **Compare** to inspect raw output beside the rendered source page."
)
