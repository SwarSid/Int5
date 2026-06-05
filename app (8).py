"""
HCP Conversion Atlas — Streamlit app
Flat file structure for Streamlit Cloud compatibility.
All view modules at root level, imported directly.
"""
import streamlit as st
import pandas as pd
import sys, os, tempfile

# Ensure the app directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_engine import DataEngine
import view_overview
import view_integrated
import view_clusters
import view_qualitative
import view_envelope

st.set_page_config(
    page_title="HCP Conversion Atlas",
    page_icon="🧬", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.stApp{background:#F8FAFC}
.block-container{padding-top:1.2rem;padding-bottom:2rem}
.mcard{background:white;border:1px solid #E2E8F0;border-radius:12px;padding:16px 12px;text-align:center}
.mlabel{font-size:9px;text-transform:uppercase;letter-spacing:.18em;color:#64748B;font-weight:600;margin-bottom:4px}
.mval{font-size:32px;font-weight:700;color:#0F4C5C;font-family:'DM Serif Display',serif;line-height:1.1}
.msub{font-size:10px;color:#94A3B8;margin-top:2px}
div[data-testid="stExpander"]{border:1px solid #E2E8F0;border-radius:10px;background:white}
/* Fix selectbox and filter label visibility */
label[data-testid="stSelectboxLabel"], .stSelectbox label,
div[data-testid="stSelectbox"] label p {color:#1E293B !important;font-weight:600 !important}
div[data-testid="stSelectbox"] > div > div {color:#1E293B !important}
p, .stMarkdown p {color:#334155}
</style>""", unsafe_allow_html=True)

TEAL="#0F4C5C"; MGRAY="#E2E8F0"; DGRAY="#64748B"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
<div style="background:{TEAL};border-radius:10px;padding:14px 16px;margin-bottom:16px">
  <div style="font-size:9px;color:rgba(255,255,255,.45);text-transform:uppercase;letter-spacing:.2em">IDH-MUTANT GLIOMA</div>
  <div style="font-size:16px;color:white;font-weight:600;font-family:'DM Serif Display',serif;margin-top:2px">HCP Conversion Atlas</div>
  <div style="font-size:9px;color:rgba(255,255,255,.45);margin-top:3px">ICI v3.0 · 8 dimensions · Zero API cost</div>
</div>""", unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:10px;font-weight:600;color:{DGRAY};margin-bottom:6px;text-transform:uppercase;letter-spacing:.1em">UPLOAD DATA FILES</div>', unsafe_allow_html=True)
    atu_file = st.file_uploader("ATU Workbook (.xlsx)", type=['xlsx'])
    pet_file = st.file_uploader("PET Workbook (.xlsx)", type=['xlsx'])

    st.markdown("---")
    st.markdown(f"""
<div style="font-size:10px;color:{DGRAY};line-height:1.7">
  <b>Filters in every tab:</b><br>
  • Specialty<br>
  • Practice Setting<br>
  • On-List / Off-List / Co-Loc<br><br>
  <b>Fully dynamic:</b> Upload any quarter's workbooks — all scores, clusters, and charts recompute.<br><br>
  <b>Zero API cost.</b>
</div>""", unsafe_allow_html=True)


# ── Engine load ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Computing ICI scores…")
def _load(atu_bytes, pet_bytes):
    eng = DataEngine()
    if atu_bytes and pet_bytes:
        eng.load_from_bytes(atu_bytes, pet_bytes)
    else:
        eng.load_project()
    return eng

atu_bytes = atu_file.read() if atu_file else None
pet_bytes = pet_file.read() if pet_file else None
eng  = _load(atu_bytes, pet_bytes)
hcps = eng.hcps_df

if hcps is None or hcps.empty:
    st.warning("Upload ATU and PET workbooks in the sidebar to begin.")
    st.stop()


# ── Filter bar ────────────────────────────────────────────────────────────────
def filter_bar(df, key_pfx="g"):
    if df is None or df.empty:
        return df
    # All filters live in the sidebar — never block main content
    with st.sidebar:
        st.markdown(f'''<div style="font-size:10px;font-weight:600;color:{DGRAY};
text-transform:uppercase;letter-spacing:.1em;margin-top:8px;margin-bottom:6px">
FILTERS</div>''', unsafe_allow_html=True)
        specs = ["All"] + sorted(df['specialty'].dropna().unique().tolist())
        sel_spec = st.selectbox("Specialty", specs, key=f"{key_pfx}_spec")
        setts = ["All"] + sorted(df['setting'].dropna().unique().tolist())
        sel_sett = st.selectbox("Practice Setting", setts, key=f"{key_pfx}_sett")
        tts = ["All"] + (sorted(df['target_type'].dropna().unique().tolist())
                         if 'target_type' in df.columns else [])
        sel_tt = st.selectbox("On/Off List", tts, key=f"{key_pfx}_tt")

    out = df.copy()
    if sel_spec != "All": out = out[out['specialty']==sel_spec]
    if sel_sett != "All": out = out[out['setting']==sel_sett]
    if sel_tt   != "All" and 'target_type' in out.columns:
        out = out[out['target_type']==sel_tt]

    n_f = len(out); n_t = len(df)
    # Show filter summary in sidebar, not in main content
    with st.sidebar:
        label = f"{n_f} of {n_t} HCPs shown"
        if sel_spec != "All": label += f"\n· {sel_spec}"
        if sel_sett != "All": label += f"\n· {sel_sett}"
        if sel_tt   != "All": label += f"\n· {sel_tt}"
        st.caption(label)
    return out


# ── Nav ───────────────────────────────────────────────────────────────────────
VIEWS = {
    "overview":   ("📊 Overview",               view_overview),
    "integrated": ("🔗 Interaction — Intent",   view_integrated),
    "clusters":   ("🗂 HCP Segmentation",       view_clusters),
    "qualitative":("🔍 Qualitative Deep-Dive",  view_qualitative),
    "envelope":   ("📋 Rep Support Card",       view_envelope),
}

if "view" not in st.session_state:
    st.session_state["view"] = "overview"

nav_cols = st.columns(len(VIEWS))
for col, (vid, (label, _)) in zip(nav_cols, VIEWS.items()):
    with col:
        if st.button(label, key=f"nav_{vid}", use_container_width=True,
                     type="primary" if st.session_state["view"]==vid else "secondary"):
            st.session_state["view"] = vid
            st.rerun()

st.markdown(f'<div style="border-bottom:1px solid {MGRAY};margin:6px 0 14px"></div>',
            unsafe_allow_html=True)

# ── Render ────────────────────────────────────────────────────────────────────
cur_view = st.session_state.get("view", "overview")
_, view_mod = VIEWS.get(cur_view, VIEWS["overview"])
view_mod.render(eng, hcps, filter_bar)
