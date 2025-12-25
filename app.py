from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st


APP_TITLE = "SDS Extractor — Drag & Drop Tester"
APP_SUBTITLE = "Upload an SDS PDF → run your extractor → view JSON + warnings → download result"


def run_extractor(pdf_path: str) -> Tuple[Dict[str, Any], str]:
    """
    Runs your existing CLI extractor and returns (parsed_json, raw_stdout).
    Assumes: python src/main.py <pdf_path>
    """
    cmd = ["python", str(Path("src") / "main.py"), pdf_path]

    # Ensure the working directory is project root (where app.py is)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    
    if stderr.strip():
        st.code(stderr, language="text")    

    if proc.returncode != 0:
        # Show stderr + any stdout for debugging
        raise RuntimeError(f"Extractor failed.\n\nSTDERR:\n{stderr}\n\nSTDOUT:\n{stdout}")

    # Your extractor should print JSON to stdout
    try:
        data = json.loads(stdout)
    except Exception as e:
        raise RuntimeError(f"Extractor output was not valid JSON.\n\nError: {e}\n\nSTDOUT:\n{stdout}")

    return data, stdout


def get_warnings(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    meta = data.get("meta") if isinstance(data, dict) else None
    if isinstance(meta, dict):
        w = meta.get("validation_warnings", [])
        if isinstance(w, list):
            return [x for x in w if isinstance(x, dict)]
    return []


st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

with st.sidebar:
    st.header("Run options")
    keep_uploaded_files = st.toggle("Keep uploaded PDFs on disk (debug)", value=False)
    st.divider()
    st.write("**How it works**")
    st.write("- Saves uploaded PDF(s) to a temp folder")
    st.write("- Runs: `python src/main.py <pdf>`")
    st.write("- Captures JSON output + displays warnings")
    st.divider()
    st.write("If you see environment prompts in VS Code:")
    st.write("✅ Select the `.venv` environment for this workspace.")

uploaded = st.file_uploader(
    "Drag and drop one or more SDS PDFs here",
    type=["pdf"],
    accept_multiple_files=True,
)

if not uploaded:
    st.info("Upload a PDF to begin.")
    st.stop()

run = st.button("Run extraction", type="primary")

if not run:
    st.stop()

results: List[Tuple[str, Dict[str, Any], List[Dict[str, Any]]]] = []

with st.spinner("Running extraction..."):
    for uf in uploaded:
        # Save uploaded file to temp location
        suffix = Path(uf.name).suffix.lower() or ".pdf"
        tmp_dir = tempfile.mkdtemp(prefix="sds_ui_")
        tmp_pdf = str(Path(tmp_dir) / f"upload{suffix}")
        with open(tmp_pdf, "wb") as f:
            f.write(uf.getbuffer())

        try:
            data, _raw = run_extractor(tmp_pdf)
            warnings = get_warnings(data)
            results.append((uf.name, data, warnings))
        finally:
            if not keep_uploaded_files:
                try:
                    Path(tmp_pdf).unlink(missing_ok=True)
                    Path(tmp_dir).rmdir()
                except Exception:
                    pass

# UI: one section per file
st.success(f"Done. Processed {len(results)} file(s).")

for filename, data, warnings in results:
    st.divider()
    st.subheader(filename)

    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        st.markdown("### JSON output")
        st.json(data, expanded=False)

        # Download
        json_bytes = json.dumps(data, indent=2).encode("utf-8")
        out_name = Path(filename).stem + ".json"
        st.download_button(
            label=f"Download {out_name}",
            data=json_bytes,
            file_name=out_name,
            mime="application/json",
        )

    with col2:
        st.markdown("### Format warnings")
        if warnings:
            st.write(f"⚠️ {len(warnings)} warning(s)")
            st.dataframe(warnings, use_container_width=True, hide_index=True)
        else:
            st.write("✅ No warnings detected")

        st.markdown("### Quick stats")
        # Minimal stats without assumptions
        ingredient_count = 0
        comp = data.get("composition", {}) if isinstance(data, dict) else {}
        if isinstance(comp, dict):
            ings = comp.get("ingredients", [])
            if isinstance(ings, list):
                ingredient_count = len(ings)
        st.write(f"- Ingredients parsed: **{ingredient_count}**")
