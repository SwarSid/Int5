"""
Cross-Tab Repository — 5 data sources consolidated:
1. Visual Aid Used vs Not Used (PET × ATU)
2. High vs Low vs Non-User (Excel segment file)
3. Rep-Driven Attributes: High LTIP vs No Interaction (Excel segment file)
4. ATU Usage & PET Perception combined segments (Excel segment file)
5. ATU Workbook pre-computed data (awareness, familiarity, usage by setting/specialty)

All computations from uploaded files only. Every finding has a full evidence expander.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import mannwhitneyu, kruskal

TEAL="#0F4C5C"; NAVY="#1E293B"; CRIMSON="#832232"; AMBER="#B8860B"; GREEN="#15803D"
LGRAY="#F8FAFC"; MGRAY="#E2E8F0"; DGRAY="#64748B"

ATTRS = [
    "Prolonged PFS","Tumor volume reduction","Prolonged OS","Low grade 3-4 AEs",
    "Low hepatic toxicity","Low hematological toxicity","Low neurotoxicity",
    "Low risk hypermutations","Manageable LFT monitoring","Good patient QoL",
    "Affordable","Manufacturer patient services","Easy to prescribe",
    "Convenient route","Low risk long-term SEs","Ability to preserve fertility",
    "Delays next treatment","Reduces seizures","Fair office compensation",
]
VORA_PERF_COLS = list(range(492, 511))
IMP_ADJ_COLS   = list(range(432, 451))
IMP_FL_COLS    = list(range(451, 470))


# ── Data builders ─────────────────────────────────────────────────────────────
def _build_atu_hcp_base(eng):
    """One row per unique ATU HCP with all performance + importance cols. Vectorised."""
    if not hasattr(eng, 'atu_raw') or eng.atu_raw is None:
        return None
    atu_raw = eng.atu_raw
    atu = atu_raw.iloc[3:].reset_index(drop=True)
    uid_series = pd.to_numeric(atu[1], errors='coerce')
    atu_clean = atu[uid_series.notna()].copy()
    atu_clean['uid'] = uid_series[uid_series.notna()].astype(int).values
    atu_u = atu_clean.drop_duplicates(subset=['uid'], keep='first').reset_index(drop=True)

    cols = {}
    cols['uid'] = atu_u['uid'].values
    for i, col in enumerate(VORA_PERF_COLS):
        if col < atu_u.shape[1]:
            v = pd.to_numeric(atu_u[col].values, errors='coerce')
            cols[f'perf_{i}'] = v
            cols[f't2b_perf_{i}'] = np.where(np.isnan(v), np.nan, (v >= 6).astype(float))
    for i, col in enumerate(IMP_ADJ_COLS):
        if col < atu_u.shape[1]:
            v = pd.to_numeric(atu_u[col].values, errors='coerce')
            cols[f'imp_adj_{i}'] = v
            cols[f't2b_imp_adj_{i}'] = np.where(np.isnan(v), np.nan, (v >= 6).astype(float))
    for i, col in enumerate(IMP_FL_COLS):
        if col < atu_u.shape[1]:
            v = pd.to_numeric(atu_u[col].values, errors='coerce')
            cols[f'imp_fl_{i}'] = v
            cols[f't2b_imp_fl_{i}'] = np.where(np.isnan(v), np.nan, (v >= 6).astype(float))
    return pd.DataFrame(cols)


# ── Confirmed segment definitions (from ZoomRx methodology) ──────────────────
# SEG1 — High vs Low vs Non-Vora User (ATU Q3_60Z_1 to Q3_60Z_12, current usage only)
#   Source question: "Any the study drug (IDH inhibitor)-containing regimen A. Current Usage"
#   across all 12 patient types (offset 14 within each 20-col patient type block).
#   Non-User = 0 patients across all 12 types.
#   Low User  = > 0 AND < panel mean.
#   High User = ≥ panel mean (mean of current the study drug patients across ALL 161 ATU HCPs).
#   The Excel file is AUTHORITATIVE (multi-wave Waves 10-18). When ATU raw is uploaded,
#   segments are recomputed from the definition for that wave.
#
# SEG2 — Rep-Driven (PET C3_35Z)
#   High LTIP = C3_35Z ≥ 6 (top-2 box).
#   No Interaction = no rep visit reported in that PET wave.
#   Other = had interaction AND C3_35Z 1–5.
#
# SEG3 — Usage × PET Perception (cross of SEG1 × SEG2)
#   High Perception = any of Q3_40BZ 17 perception change attrs rated 6 or 7 (top-2 box).
#   Low Perception / No Interaction = all attrs < 6 OR no PET visit.
# ─────────────────────────────────────────────────────────────────────────────

# the study drug Current Usage cols: "THE STUDY DRUG A. Current Usage" within Q3_60Z
# Confirmed by label scan: cols 181,201,221,241,261,281,301,321,339,361,381,399
_VORA_CURR_OFFSETS = [181, 201, 221, 241, 261, 281, 301, 321, 339, 361, 381, 399]

_PATIENT_TYPE_LABELS = [
    "Adjuvant GTR Astrocytoma", "Adjuvant STR/Biopsy Astrocytoma",
    "Adjuvant GTR Oligodendroglioma", "Adjuvant STR/Biopsy Oligodendroglioma",
    "Stable >6mo GTR Astrocytoma", "Stable >6mo STR Astrocytoma",
    "Stable >6mo GTR Oligodendroglioma", "Stable >6mo STR Oligodendroglioma",
    "Recurrent/Progressive (after observation only)",
    "Maintenance within 6mo post-RT/CT",
    "Stable >6mo post-systemic therapy",
    "Recurrent/Progressive (after systemic therapy)",
]


def _compute_seg1_from_raw(atu_raw):
    """Compute High/Low/Non-User from ATU raw data.
    Definition: sum of current the study drug patients across all 12 patient types (Q3_60Z).
    Non-User=0, Low=1 to <mean, High=>=mean. Mean computed across ALL HCPs including zeros."""
    atu_qcodes = atu_raw.iloc[2].values
    atu_sub = atu_raw.iloc[4].values
    atu = atu_raw.iloc[3:].reset_index(drop=True)
    uid_s = pd.to_numeric(atu[1], errors='coerce')
    atu = atu[uid_s.notna()].copy()
    atu['uid'] = uid_s[uid_s.notna()].astype(int).values
    atu_u = atu.drop_duplicates(subset=['uid'], keep='first').reset_index(drop=True)

    # Find exact the study drug Current cols by label (most robust approach)
    q360_cols = [i for i,v in enumerate(atu_qcodes) if str(v).startswith('Q3_60Z')]
    vora_curr_cols = [c for c in q360_cols
                      if 'THE STUDY DRUG' in str(atu_sub[c]).upper() and 'Current Usage' in str(atu_sub[c])]
    # Fallback to hardcoded offsets if label scan fails
    if len(vora_curr_cols) < 12:
        vora_curr_cols = [c for c in _VORA_CURR_OFFSETS if c < atu_u.shape[1]]

    vora_curr = atu_u[vora_curr_cols].apply(pd.to_numeric, errors='coerce').sum(axis=1).fillna(0)
    panel_mean = vora_curr.mean()

    seg = pd.Series('Non Vora User', index=atu_u.index)
    seg[vora_curr > 0] = 'Low Vora Usage'
    seg[vora_curr >= panel_mean] = 'High Vora Usage'

    result = pd.DataFrame({'uid': atu_u['uid'].values, 'seg1': seg.values,
                           'vora_curr_total': vora_curr.values,
                           'panel_mean_curr': panel_mean})
    return result, vora_curr_cols, panel_mean


def _compute_seg2_from_pet(pet_raw):
    """Compute Rep-Driven segment from PET raw data.
    High LTIP = C3_35Z >= 6. No Interaction = no Q1_40Z value. Other = had visit, LTIP 1-5."""
    pet_qcodes = pet_raw.iloc[4].values
    pet = pet_raw.iloc[5:].reset_index(drop=True)
    uid_s = pd.to_numeric(pet[1], errors='coerce')
    pet = pet[uid_s.notna()].copy()
    pet['uid'] = uid_s[uid_s.notna()].astype(int).values
    pet_u = pet.drop_duplicates(subset=['uid'], keep='first').reset_index(drop=True)

    ltip_cols = [i for i,v in enumerate(pet_qcodes) if str(v).startswith('C3_35Z')]
    int_cols  = [i for i,v in enumerate(pet_qcodes) if str(v).startswith('Q1_40Z')]
    q340_cols = [i for i,v in enumerate(pet_qcodes) if str(v).startswith('Q3_40BZ')]

    ltip = pd.to_numeric(pet_u[ltip_cols[0]], errors='coerce') if ltip_cols else pd.Series(np.nan, index=pet_u.index)
    had_int = pet_u[int_cols[0]].notna() if int_cols else pd.Series(False, index=pet_u.index)

    seg = pd.Series('No Interaction', index=pet_u.index)
    seg[had_int & (ltip < 6)] = 'Other'
    seg[had_int & (ltip >= 6)] = 'High LTIP'

    # Perception: any Q3_40BZ >= 6 = High Perception
    if q340_cols:
        perc_t2b = (pet_u[q340_cols].apply(pd.to_numeric, errors='coerce') >= 6).any(axis=1)
    else:
        perc_t2b = pd.Series(False, index=pet_u.index)

    result = pd.DataFrame({'uid': pet_u['uid'].values, 'seg2': seg.values,
                           'high_perception': perc_t2b.values, 'ltip_raw': ltip.values})
    return result


def _load_segments(eng=None):
    """Load segments. Priority: (1) session_state upload, (2) project folder Excel files,
    (3) recompute from raw ATU/PET if available.
    The Excel files are AUTHORITATIVE (multi-wave). Raw recomputation is single-wave only."""
    import io

    def _read_excel_seg(ss_key, project_path, seg_col):
        try:
            if ss_key in st.session_state and st.session_state[ss_key]:
                df = pd.read_excel(io.BytesIO(st.session_state[ss_key]))
                return df.rename(columns={'User Id': 'uid', 'Segment Value': seg_col})[['uid', seg_col]]
        except: pass
        try:
            df = pd.read_excel(project_path)
            return df.rename(columns={'User Id': 'uid', 'Segment Value': seg_col})[['uid', seg_col]]
        except: pass
        return None

    seg1_df = _read_excel_seg('seg_high_low_no_user',
                               '/mnt/project/High_vs_Low_vs_No_User_ATU_PET_Segment.xlsx', 'seg1')
    seg2_df = _read_excel_seg('seg_rep_driven',
                               '/mnt/project/Rep_Driven_Attributes_ATU.xlsx', 'seg2')
    seg3_df = _read_excel_seg('seg_usage_perception',
                               '/mnt/project/ATU_Usage_and_PET_Perception.xlsx', 'seg3')

    # If Excel file missing but raw data available, compute from raw
    if seg1_df is None and eng is not None and hasattr(eng, 'atu_raw') and eng.atu_raw is not None:
        computed, _, _ = _compute_seg1_from_raw(eng.atu_raw)
        seg1_df = computed[['uid', 'seg1']]

    if seg2_df is None and eng is not None and hasattr(eng, 'pet_raw') and eng.pet_raw is not None:
        computed2 = _compute_seg2_from_pet(eng.pet_raw)
        seg2_df = computed2[['uid', 'seg2']]
        # Build seg3 from computed seg1 and seg2
        if seg3_df is None and seg1_df is not None:
            m = seg1_df.merge(computed2[['uid','seg2','high_perception']], on='uid', how='inner')
            m['seg3'] = m.apply(lambda r:
                f"{r['seg1']} and high perception" if r['high_perception'] and r['seg2'] != 'No Interaction'
                else f"{r['seg1']} and no interaction" if r['seg2'] == 'No Interaction'
                else f"{r['seg1']} and low perception", axis=1)
            seg3_df = m[['uid', 'seg3']]

    seg1_df = seg1_df if seg1_df is not None else pd.DataFrame(columns=['uid','seg1'])
    seg2_df = seg2_df if seg2_df is not None else pd.DataFrame(columns=['uid','seg2'])
    seg3_df = seg3_df if seg3_df is not None else pd.DataFrame(columns=['uid','seg3'])
    return seg1_df, seg2_df, seg3_df


def _load_workbook_data():
    """Load ATU Workbook. Checks session_state first, then project folder."""
    import io
    try:
        if 'seg_atu_workbook' in st.session_state and st.session_state['seg_atu_workbook']:
            return pd.read_excel(io.BytesIO(st.session_state['seg_atu_workbook']),
                                 sheet_name=None, header=None)
    except: pass
    try:
        return pd.read_excel('/mnt/project/GLIOMA_Q2_FY26_ATU_Workbook.xlsx',
                             sheet_name=None, header=None)
    except: return {}


# ── Statistics helpers ────────────────────────────────────────────────────────
def _mw2(a, b):
    a = pd.to_numeric(a, errors='coerce').dropna()
    b = pd.to_numeric(b, errors='coerce').dropna()
    if len(a) < 3 or len(b) < 3: return None, False, False
    try:
        _, p = mannwhitneyu(a, b, alternative='two-sided')
        return round(p, 3), p < 0.10, p < 0.05
    except: return None, False, False


def _kw3(groups):
    groups = [pd.to_numeric(g, errors='coerce').dropna() for g in groups]
    valid = [g for g in groups if len(g) >= 3]
    if len(valid) < 2: return None, False, False
    try:
        _, p = kruskal(*valid)
        return round(p, 3), p < 0.10, p < 0.05
    except: return None, False, False


# ── Rendering helpers ─────────────────────────────────────────────────────────
def _sig_chip(p, sig90, sig95):
    if p is None:
        return '<span style="background:#F1F5F9;color:#94A3B8;padding:2px 7px;border-radius:3px;font-size:9px">n/a</span>'
    if sig95:
        return f'<span style="background:#15803D;color:white;padding:2px 7px;border-radius:3px;font-size:10px;font-weight:700">✓ p={p} — 95%</span>'
    if sig90:
        return f'<span style="background:#FBBF24;color:#0F172A;padding:2px 7px;border-radius:3px;font-size:10px;font-weight:700">~ p={p} — 90%</span>'
    return f'<span style="background:#F1F5F9;color:#64748B;padding:2px 7px;border-radius:3px;font-size:10px">p={p} n.s.</span>'


def _cell(pct):
    if pct >= 70: return f"background:#15803D;color:white"
    if pct >= 55: return f"background:#FEF9C3;color:#713F12"
    if pct >= 40: return f"background:#FED7AA;color:#9A3412"
    return f"background:#FEE2E2;color:#991B1B"


def _evidence_expander(attr, groups_data, p, sig90, sig95, split_desc, source_q, metric_desc, key=""):
    with st.expander(f"↳  {attr} — full data source & derivation"):
        border = GREEN if sig95 else (AMBER if sig90 else MGRAY)
        grids = "".join([
            f"<div style='background:white;border-radius:8px;padding:10px 12px;border-top:3px solid {TEAL}'>"
            f"<div style='font-size:9px;text-transform:uppercase;letter-spacing:.12em;color:{TEAL};font-weight:700;margin-bottom:2px'>{label}</div>"
            f"<div style='font-size:22px;font-weight:700;color:#0F172A'>{val:.0f}%</div>"
            f"<div style='font-size:10px;color:{DGRAY}'>n={n}</div></div>"
            for label, val, n in groups_data
        ])
        sig_note = ("✓ Statistically significant." if sig95 else
                    "~ Approaching significance at 90%." if sig90 else
                    "Not statistically significant — treat as directional only.")
        st.markdown(f"""
<div style="background:{LGRAY};border-left:4px solid {border};border-radius:0 12px 12px 0;padding:14px 16px">
  <div style="font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:{border};font-weight:700;margin-bottom:10px">DATA DERIVATION · OBJECTIVE</div>
  <div style="display:grid;grid-template-columns:{'1fr ' * len(groups_data)};gap:8px;margin-bottom:12px">{grids}</div>
  <div style="background:white;border-radius:8px;padding:10px 12px;margin-bottom:8px">
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:{NAVY};font-weight:700;margin-bottom:4px">HOW THE SPLIT WAS DEFINED</div>
    <div style="font-size:12px;color:#334155;line-height:1.6">{split_desc}</div>
  </div>
  <div style="background:white;border-radius:8px;padding:10px 12px;margin-bottom:8px">
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:{NAVY};font-weight:700;margin-bottom:4px">HOW THE METRIC WAS COMPUTED</div>
    <div style="font-size:12px;color:#334155;line-height:1.6">{metric_desc}</div>
    <div style="font-size:10px;color:#94A3B8;margin-top:4px">{source_q}</div>
  </div>
  <div style="background:{'#F0FDF4' if sig95 else '#FFFBEB' if sig90 else '#F8FAFC'};border-radius:8px;padding:8px 12px;border-left:3px solid {border}">
    <div style="font-size:12px;color:#334155"><b>Statistical test:</b> {'Kruskal-Wallis (3+ groups)' if len(groups_data)>2 else 'Mann-Whitney U (2 groups)'} · p={p if p is not None else 'N/A'} · {sig_note}</div>
  </div>
</div>
""", unsafe_allow_html=True)


def _bar_chart_multi(groups_labels, groups_t2b, sig_flags, title, n_attrs=19):
    """Multi-group grouped bar chart for all 19 attributes."""
    fig = go.Figure()
    palette = [TEAL, CRIMSON, AMBER, GREEN, NAVY]
    for gi, (label, t2b_list) in enumerate(zip(groups_labels, groups_t2b)):
        color_list = []
        for i in range(n_attrs):
            s90, s95 = sig_flags[i] if i < len(sig_flags) else (False, False)
            color_list.append(GREEN if s95 else (AMBER if s90 else palette[gi % len(palette)]))
        fig.add_trace(go.Bar(
            name=label, x=ATTRS, y=t2b_list,
            marker_color=palette[gi % len(palette)],
            text=[f"{v:.0f}%" for v in t2b_list],
            textposition="outside", textfont=dict(size=8),
        ))
    fig.update_layout(
        barmode="group", height=420,
        title=dict(text=title, font=dict(family="DM Serif Display", size=15, color="#0F172A")),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter", size=9, color="#0F172A"),
        yaxis=dict(range=[0, 120], showgrid=True, gridcolor="#F1F5F9",
                   title="% Top-2 Box (6 or 7 out of 7)"),
        xaxis_tickangle=-40,
        legend=dict(orientation="h", yanchor="bottom", y=-0.45, font=dict(size=10)),
        margin=dict(l=0, r=0, t=40, b=10),
    )
    return fig


def _full_xt_section(df, groups_def, split_desc, source_q, col_prefix="perf_", t2b_prefix="t2b_perf_",
                     is_3group=False, sig_label="Kruskal-Wallis"):
    """Render full T2B table + bar chart + 10-bullet summary + evidence expanders."""
    group_labels = [g[0] for g in groups_def]
    group_filters = [g[1] for g in groups_def]
    group_subsets = [df[g[1]].copy() for g in groups_def]
    group_ns = [len(s[f'{t2b_prefix}0'].dropna()) for s in group_subsets]

    all_t2b = [[] for _ in range(len(groups_def))]
    sig_flags = []
    rows_html = ""

    for i, attr in enumerate(ATTRS):
        t2b_vals = []
        for gi, sub in enumerate(group_subsets):
            t2b = sub[f'{t2b_prefix}{i}'].dropna().mean() * 100 if len(sub[f'{t2b_prefix}{i}'].dropna()) > 0 else 0
            t2b_vals.append(t2b)
            all_t2b[gi].append(t2b)

        raws = [sub[f'{col_prefix}{i}'].dropna() for sub in group_subsets]
        if is_3group or len(raws) > 2:
            p, sig90, sig95 = _kw3(raws)
        else:
            p, sig90, sig95 = _mw2(raws[0], raws[1])
        sig_flags.append((sig90, sig95))

        border_color = "#15803D" if sig95 else (AMBER if sig90 else MGRAY)
        cells = "".join([f'<td style="padding:7px 8px;text-align:center"><span style="{_cell(v)};padding:3px 9px;border-radius:4px;font-size:12px;font-weight:700">{v:.0f}%</span></td>' for v in t2b_vals])
        delta = max(t2b_vals) - min(t2b_vals) if len(t2b_vals) > 1 else 0
        dc = GREEN if delta >= 20 else (AMBER if delta >= 10 else DGRAY)
        rows_html += f'<tr style="border-bottom:1px solid {MGRAY};border-left:3px solid {border_color}"><td style="padding:7px 10px;font-size:12px;color:#0F172A;font-weight:500">{attr}</td>{cells}<td style="padding:7px 8px;text-align:center;font-size:12px;font-weight:700;color:{dc}">±{delta:.0f}pp</td><td style="padding:7px 8px;text-align:center">{_sig_chip(p,sig90,sig95)}</td></tr>'

    # Table header
    th = "".join([f'<th style="padding:8px 10px;text-align:center;font-size:10px;color:{TEAL};font-weight:700;text-transform:uppercase;letter-spacing:.1em">{lbl}<br><span style="font-weight:400;color:#94A3B8;font-size:9px">n={n}</span></th>'
                  for lbl, n in zip(group_labels, group_ns)])
    header = f'<table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif"><thead><tr style="background:{LGRAY}"><th style="padding:8px 10px;text-align:left;font-size:10px;color:{DGRAY};font-weight:600;text-transform:uppercase;letter-spacing:.1em">Attribute</th>{th}<th style="padding:8px 10px;text-align:center;font-size:10px;color:{DGRAY};font-weight:600;text-transform:uppercase">Max Δ</th><th style="padding:8px 10px;text-align:center;font-size:10px;color:{DGRAY};font-weight:600;text-transform:uppercase">Sig</th></tr></thead><tbody>{rows_html}</tbody></table>'
    st.markdown(header, unsafe_allow_html=True)
    st.markdown(f'<div style="display:flex;gap:10px;margin-top:6px;flex-wrap:wrap;font-size:10px;color:{DGRAY}"><span><span style="background:#15803D;color:white;padding:1px 5px;border-radius:3px;font-size:9px">Green</span> ≥70%</span><span><span style="background:#FEF9C3;color:#713F12;padding:1px 5px;border-radius:3px;font-size:9px">Yellow</span> 55–69%</span><span><span style="background:#FED7AA;color:#9A3412;padding:1px 5px;border-radius:3px;font-size:9px">Orange</span> 40–54%</span><span><span style="background:#FEE2E2;color:#991B1B;padding:1px 5px;border-radius:3px;font-size:9px">Red</span> &lt;40%</span></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Bar chart
    chart_title = f"the study drug Performance Top-2 Box %: {' vs '.join(group_labels)}<br><sup>ATU Q3_120Z the study drug only · 1=Very poor → 7=Excellent · T2B = 6 or 7 out of 7</sup>"
    fig = _bar_chart_multi(group_labels, all_t2b, sig_flags, chart_title)
    st.plotly_chart(fig, use_container_width=True)

    # 10-bullet summary
    sig95_attrs = [ATTRS[i] for i,(s90,s95) in enumerate(sig_flags) if s95]
    sig90_attrs = [ATTRS[i] for i,(s90,s95) in enumerate(sig_flags) if s90 and not s95]
    total_sig = len(sig95_attrs)
    avg_vals = [sum(all_t2b[gi]) / len(all_t2b[gi]) for gi in range(len(groups_def))]
    best_group = group_labels[avg_vals.index(max(avg_vals))]
    worst_group = group_labels[avg_vals.index(min(avg_vals))]
    biggest_gap_attr = ATTRS[max(range(len(ATTRS)), key=lambda i: max(all_t2b[gi][i] for gi in range(len(groups_def))) - min(all_t2b[gi][i] for gi in range(len(groups_def))))]
    biggest_gap_val = round(max(all_t2b[gi][ATTRS.index(biggest_gap_attr)] for gi in range(len(groups_def))) - min(all_t2b[gi][ATTRS.index(biggest_gap_attr)] for gi in range(len(groups_def))))
    high_all = [a for i,a in enumerate(ATTRS) if all(all_t2b[gi][i] >= 60 for gi in range(len(groups_def)))]
    low_all  = [a for i,a in enumerate(ATTRS) if all(all_t2b[gi][i] < 45 for gi in range(len(groups_def)))]

    bullets = [
        f"Overall the study drug performance ratings are highest for {best_group} (avg {max(avg_vals):.0f}% T2B) and lowest for {worst_group} (avg {min(avg_vals):.0f}% T2B) — a {max(avg_vals)-min(avg_vals):.0f}pp overall gap.",
        f"{total_sig} of 19 attributes reach statistical significance at 95% confidence (p<0.05): {', '.join(sig95_attrs) if sig95_attrs else 'none'} — these differences are unlikely due to chance.",
        f"{len(sig90_attrs)} attributes approach significance at 90%: {', '.join(sig90_attrs) if sig90_attrs else 'none'} — directional signal worth monitoring.",
        f"Largest single-attribute gap: '{biggest_gap_attr}' shows {biggest_gap_val}pp spread between highest and lowest scoring group.",
        f"{len(high_all)} attributes score ≥60% T2B across ALL groups: {', '.join(high_all[:4]) if high_all else 'none'} — these are perceived strengths regardless of segment.",
        f"{len(low_all)} attributes score <45% T2B across ALL groups: {', '.join(low_all[:3]) if low_all else 'none'} — these are universal weaknesses needing clinical messaging support.",
        f"Group averages across all 19 attributes: " + " · ".join([f"{lbl} = {v:.0f}%" for lbl, v in zip(group_labels, avg_vals)]) + ".",
        f"Statistical test: {'Kruskal-Wallis (non-parametric, 3+ groups)' if is_3group else 'Mann-Whitney U (non-parametric, 2 groups)'}. Alpha levels: 95% (p<0.05) and 90% (p<0.10) both reported.",
        f"Data source: ATU Q3_120Z the study drug (IDH inhibitor) column only. Temozolomide+RT and Radiation alone are excluded from this view. Ratings 1–7, Top-2 Box = 6 or 7.",
        f"Group definitions sourced from uploaded Excel segment files — these are pre-assigned classifications, not computed from the raw survey responses in this tool.",
    ]

    st.markdown(f'<div style="background:white;border:1px solid {MGRAY};border-radius:12px;padding:18px 20px;margin-bottom:16px"><div style="font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:{TEAL};font-weight:700;margin-bottom:10px">10-POINT DATA SUMMARY</div>', unsafe_allow_html=True)
    for i, b in enumerate(bullets):
        st.markdown(f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px"><div style="width:20px;height:20px;border-radius:50%;background:{TEAL};color:white;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">{i+1}</div><div style="font-size:12px;color:#334155;line-height:1.5">{b}</div></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Evidence expanders per attribute
    st.markdown(f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.18em;color:{DGRAY};font-weight:600;margin-bottom:6px">EXPAND ANY ATTRIBUTE FOR FULL DATA SOURCE</div>', unsafe_allow_html=True)
    for i, attr in enumerate(ATTRS):
        p_e, sig90_e, sig95_e = sig_flags[i] if i < len(sig_flags) else (None, False, False)
        groups_data = [(gl, all_t2b[gi][i], group_ns[gi]) for gi, gl in enumerate(group_labels)]
        _evidence_expander(attr, groups_data, p_e, sig90_e, sig95_e, split_desc, source_q,
                           f"Top-2 Box: % rating the study drug 6 or 7 out of 7 on '{attr}'. "
                           f"ATU Q3_120Z — 'How would you rate the study drug as an adjuvant or first-line treatment?' "
                           f"[1=Very poor → 7=Excellent]. the study drug column only (absolute cols 492–510).")


# ── Main render ───────────────────────────────────────────────────────────────
def render(eng):
    atu_base = _build_atu_hcp_base(eng)
    seg1, seg2, seg3 = _load_segments(eng)
    wb = _load_workbook_data()

    if atu_base is None:
        st.warning("No ATU data loaded."); return

    # Merge all segments into base
    df = atu_base.merge(seg1, on='uid', how='left')
    df = df.merge(seg2, on='uid', how='left')
    df = df.merge(seg3, on='uid', how='left')

    n_total = len(df)
    n_seg1 = df['seg1'].notna().sum()
    n_seg2 = df['seg2'].notna().sum()
    n_seg3 = df['seg3'].notna().sum()

    # ── Header ──
    st.markdown(f"""
<div style="margin-bottom:16px">
  <div style="font-size:10px;text-transform:uppercase;letter-spacing:.28em;color:{CRIMSON};font-weight:600">CROSS-TAB REPOSITORY</div>
  <h1 style="font-family:'DM Serif Display',serif;font-size:44px;font-weight:300;color:#0F172A;line-height:1.05;margin-bottom:10px">
    Five data sources. One view.<br>
    <span style="color:{TEAL}">Every % traceable to a file.</span>
  </h1>
  <p style="font-size:14px;color:#475569;max-width:700px;line-height:1.65">
    the study drug performance Top-2 Box % (ratings 6 or 7 out of 7) and attribute importance across
    all pre-defined segment files. Conditional formatting: green = strong, yellow = moderate, orange/red = weak.
    Both 90% and 95% significance levels shown. Every attribute has an expandable evidence block.
  </p>
</div>
""", unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, label, val, sub in [
        (c1, "ATU HCPs", n_total, "Unique respondents"),
        (c2, "High/Low/Non-User", n_seg1, "From Excel segment file"),
        (c3, "Rep-Driven", n_seg2, "From Excel segment file"),
        (c4, "Usage+Perception", n_seg3, "From Excel segment file"),
        (c5, "Attributes", 19, "the study drug only · no TMZ/RT"),
    ]:
        with col:
            st.markdown(f'<div class="mcard"><div class="mlabel">{label}</div><div class="mval" style="font-size:36px">{val}</div><div class="msub">{sub}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──
    tabs = st.tabs([
        "👥 High vs Low vs Non-User",
        "🎯 Rep-Driven: LTIP vs No Interaction",
        "🔬 Usage × PET Perception",
        "📊 ATU Workbook: Awareness & Familiarity",
        "📈 ATU Workbook: Usage by Segment",
        "💊 VA Used vs Not Used",
        "📋 Download All",
    ])

    # ── TAB 1: High vs Low vs Non-User ────────────────────────────────────
    with tabs[0]:
        groups_s1 = [
            ("High Vora Usage", df['seg1'] == 'High Vora Usage'),
            ("Low Vora Usage",  df['seg1'] == 'Low Vora Usage'),
            ("Non Vora User",   df['seg1'] == 'Non Vora User'),
        ]
        n_hi_s1 = int(df[df['seg1']=='High Vora Usage']['seg1'].count())
        n_lo_s1 = int(df[df['seg1']=='Low Vora Usage']['seg1'].count())
        n_nu_s1 = int(df[df['seg1']=='Non Vora User']['seg1'].count())

        st.markdown(f"""
<div style="background:white;border:1px solid {MGRAY};border-radius:12px;padding:14px 18px;margin-bottom:16px">
  <div style="font-size:14px;font-weight:600;color:#0F172A;margin-bottom:6px">
    High Vora Usage (n={n_hi_s1}) vs Low Vora Usage (n={n_lo_s1}) vs Non Vora User (n={n_nu_s1})
  </div>
  <div style="font-size:12px;color:{DGRAY};margin-bottom:6px">
    <b>Source:</b> High_vs_Low_vs_No_User_ATU_PET_Segment.xlsx — ZoomRx pre-assigned, Waves 10-18. {n_match} of {n_total} matched.
  </div>
  <div style="background:{LGRAY};border-radius:8px;padding:10px 12px;margin-bottom:4px;font-size:11px;color:#334155;line-height:1.65">
    <b>Confirmed segment definition:</b><br>
    <b>Non Vora User</b> = zero current the study drug patients across all 12 patient types (ATU Q3_60Z). Future usage excluded.<br>
    <b>Low Vora Usage</b> = total current the study drug patients &gt; 0 AND below panel mean.<br>
    <b>High Vora Usage</b> = total current the study drug patients ≥ panel mean (mean of all 161 ATU HCPs including zeros).<br>
    <b>Question:</b> ATU Q3_60Z — "Any the study drug (IDH inhibitor)-containing regimen A. Current Usage" across all 12 patient types
    (Adjuvant GTR/STR Astro, Adjuvant GTR/STR Oligo, Stable GTR/STR Astro, Stable GTR/STR Oligo,
    Recurrent/Progressive after observation, Maintenance post-RT/CT, Stable post-systemic, Recurrent post-systemic).
  </div>
  <div style="font-size:10px;color:#94A3B8">Statistical test: Kruskal-Wallis (3-group). p&lt;0.05 = 95% sig · p&lt;0.10 = 90% sig.</div>
</div>
""", unsafe_allow_html=True)

        split_desc = ("Confirmed definition: Non Vora User = 0 current the study drug patients across all 12 patient types (ATU Q3_60Z current usage only, future usage excluded). "
                      "Low Vora Usage = total current the study drug patients > 0 AND < panel mean. "
                      "High Vora Usage = total current the study drug patients >= panel mean (computed across all 161 HCPs). "
                      "Source: High_vs_Low_vs_No_User_ATU_PET_Segment.xlsx (Waves 10-18, authoritative multi-wave file).")
        _full_xt_section(df, groups_s1, split_desc,
                         "ATU Q3_60Z (the study drug current usage, 12 patient types) · Segment file: High_vs_Low_vs_No_User_ATU_PET_Segment.xlsx",
                         "ATU Q3_120Z the study drug col (20–38) · Split from High_vs_Low_vs_No_User_ATU_PET_Segment.xlsx",
                         is_3group=True)

    # ── TAB 2: Rep-Driven ──────────────────────────────────────────────────
    with tabs[1]:
        n_hi  = df[df['seg2']=='High LTIP']['seg2'].count()
        n_no  = df[df['seg2']=='No Interaction']['seg2'].count()
        n_oth = df[df['seg2']=='Other']['seg2'].count()

        st.markdown(f"""
<div style="background:white;border:1px solid {MGRAY};border-radius:12px;padding:14px 18px;margin-bottom:16px">
  <div style="font-size:14px;font-weight:600;color:#0F172A;margin-bottom:4px">
    Rep-Driven Attributes: High LTIP vs No Interaction vs Other
  </div>
  <div style="font-size:12px;color:{DGRAY};margin-bottom:4px">
    <b>Source file:</b> Rep_Driven_Attributes_ATU.xlsx — 'Segment Value' column.
    High LTIP (n={n_hi}): HCPs who reported top-2 box likelihood to increase prescribing after rep visit.
    No Interaction (n={n_no}): HCPs who reported no rep interaction in the PET wave.
    Other (n={n_oth}): Did not qualify for either definition.
    Tests whether rep visit quality (LTIP) connects to ATU the study drug performance perceptions.
  </div>
  <div style="font-size:10px;color:#94A3B8">Statistical test: Kruskal-Wallis (3-group). Mann-Whitney for High LTIP vs No Interaction pairwise shown in chart.</div>
</div>
""", unsafe_allow_html=True)

        groups_s2 = [
            ("High LTIP",       df['seg2'] == 'High LTIP'),
            ("No Interaction",  df['seg2'] == 'No Interaction'),
            ("Other",           df['seg2'] == 'Other'),
        ]
        split_desc2 = ("Confirmed definition: "
                       "High LTIP = PET C3_35Z score 6 or 7 (top-2 box — 'very likely' or 'extremely likely' to increase prescribing the study drug post-visit). "
                       "No Interaction = no rep visit reported in that PET wave (PET Q1_40Z = null / not completed). "
                       "Other = had a rep interaction AND PET C3_35Z scored 1–5 (non-top-2 box). "
                       "Source: Rep_Driven_Attributes_ATU.xlsx — ZoomRx pre-assigned, PET Waves 2–3.")
        _full_xt_section(df, groups_s2, split_desc2,
                         "ATU Q3_120Z the study drug col (20–38) · Split from Rep_Driven_Attributes_ATU.xlsx · PET C3_35Z (LTIP 1–7)",
                         is_3group=True)

        # Also show pairwise High LTIP vs No Interaction for clear contrast
        st.markdown(f'<div style="font-family:\'DM Serif Display\',serif;font-size:20px;color:#0F172A;margin:20px 0 8px">Pairwise: High LTIP vs No Interaction only</div>', unsafe_allow_html=True)
        groups_s2b = [
            ("High LTIP",       df['seg2'] == 'High LTIP'),
            ("No Interaction",  df['seg2'] == 'No Interaction'),
        ]
        split_desc2b = "Same source as above, restricted to High LTIP vs No Interaction for direct comparison. Mann-Whitney U (2-group) test."
        _full_xt_section(df, groups_s2b, split_desc2b,
                         "ATU Q3_120Z · Rep_Driven_Attributes_ATU.xlsx",
                         is_3group=False)

    # ── TAB 3: Usage × PET Perception ─────────────────────────────────────
    with tabs[2]:
        seg3_counts = df['seg3'].value_counts()
        top_segs = seg3_counts[seg3_counts >= 6].index.tolist()

        st.markdown(f"""
<div style="background:white;border:1px solid {MGRAY};border-radius:12px;padding:14px 18px;margin-bottom:16px">
  <div style="font-size:14px;font-weight:600;color:#0F172A;margin-bottom:4px">
    ATU Usage × PET Perception Combined Segments
  </div>
  <div style="font-size:12px;color:{DGRAY};margin-bottom:6px">
    <b>Source:</b> ATU_Usage_and_PET_Perception.xlsx — cross of ATU usage group × PET perception.
    Segments with n&lt;6 excluded. {', '.join([f'{s}: n={c}' for s,c in seg3_counts.items()])}.
  </div>
  <div style="background:{LGRAY};border-radius:8px;padding:10px 12px;font-size:11px;color:#334155;line-height:1.65;margin-bottom:4px">
    <b>Confirmed definition:</b><br>
    <b>Usage group</b> (ATU): High Vora Usage = current the study drug patients ≥ panel mean ·
    Low Vora Usage = 1 to &lt; mean · Non User = 0 patients (ATU Q3_60Z current usage, 12 patient types).<br>
    <b>Perception group</b> (PET): High Perception = any of Q3_40BZ 17 attribute change ratings scored 6 or 7
    (top-2 box, "significant positive impact"). Low Perception / No Interaction = all below 6 or no PET visit.
  </div>
</div>
""", unsafe_allow_html=True)

        # Show key 3-way comparison
        key_segs = [s for s in ['High Vora user and high perception',
                                 'Low Vora User and High perception',
                                 'Non User and High Perception',
                                 'Non User and No interaction'] if s in top_segs]
        if key_segs:
            groups_s3 = [(s.replace(' and ', ' + '), df['seg3'] == s) for s in key_segs]
            split_desc3 = ("ATU_Usage_and_PET_Perception.xlsx, 'Segment Value' column. "
                           "Segments combine ATU the study drug usage level with PET post-visit perception rating. "
                           "High perception = rated the study drug 6 or 7 on overall perception (PET Q3_40BZ avg). "
                           "No interaction = no PET visit reported in that wave. "
                           "Only segments with n≥6 are shown.")
            _full_xt_section(df, groups_s3, split_desc3,
                             "ATU Q3_120Z the study drug col · ATU_Usage_and_PET_Perception.xlsx",
                             is_3group=True)

    # ── TAB 4: ATU Workbook — Awareness & Familiarity ──────────────────────
    with tabs[3]:
        st.markdown(f"""
<div style="font-family:'DM Serif Display',serif;font-size:24px;color:#0F172A;margin-bottom:8px">
  ATU Workbook: Awareness & Familiarity — Pre-computed Data
</div>
<div style="font-size:12px;color:#94A3B8;margin-bottom:16px">
  Source: GLIOMA_Q2_FY26_ATU_Workbook.xlsx · 'ATU Awareness & Familiarity' sheet.
  Data extracted directly from the workbook as-is — no recomputation.
</div>
""", unsafe_allow_html=True)

        if 'ATU Awareness & Familiarity' in wb:
            aw_df = wb['ATU Awareness & Familiarity']

            # Section 1: Overall trended awareness
            st.markdown(f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.18em;color:{TEAL};font-weight:700;margin-bottom:8px">UNAIDED AWARENESS — OVERALL TRENDED (Q2.10)</div>', unsafe_allow_html=True)
            try:
                treatments_row = aw_df.iloc[3].dropna().tolist()
                aware_row = aw_df.iloc[4].dropna().tolist()
                periods_row = aw_df.iloc[5].dropna().tolist()
                ns_row = aw_df.iloc[6].dropna().tolist()

                # Parse into clean display
                treats = [str(t).replace('\u200b','').replace('\n',' ')[:25] for t in treatments_row if t != 'Trended']
                q_vals = [v for v in aware_row if v != '% Aware']
                periods = [str(p) for p in periods_row]

                if treats and q_vals:
                    cols_aw = st.columns(min(len(treats[:6]), 6))
                    for ci, (treat, val) in enumerate(zip(treats[:6], q_vals[:6])):
                        with cols_aw[ci]:
                            pct = round(float(val)*100) if isinstance(val, float) else 0
                            bg = "#15803D" if pct >= 70 else ("#FBBF24" if pct >= 50 else CRIMSON)
                            st.markdown(f'<div style="background:white;border:1px solid {MGRAY};border-radius:10px;padding:12px;text-align:center"><div style="font-size:10px;color:{DGRAY};margin-bottom:4px">{treat}</div><div style="font-size:28px;font-weight:700;color:{bg}">{pct}%</div><div style="font-size:9px;color:#94A3B8">unaided aware</div></div>', unsafe_allow_html=True)
            except Exception as e:
                st.info(f"Could not parse awareness section: {e}")

            with st.expander("↳  How this data was extracted"):
                st.markdown(f"""
<div style="background:{LGRAY};border-left:4px solid {TEAL};border-radius:0 10px 10px 0;padding:12px 14px">
  <div style="font-size:12px;color:#334155;line-height:1.6">
    <b>Source:</b> GLIOMA_Q2_FY26_ATU_Workbook.xlsx, sheet 'ATU Awareness & Familiarity', rows 3–7 (0-indexed).<br>
    <b>Question:</b> ATU Q2.10 — "What treatments come to mind when thinking of treating IDH-mutant astrocytoma or oligodendroglioma patients?" Unaided, open-end voice response. Coded by ZoomRx.<br>
    <b>Metric:</b> % mentioning each treatment, among all physicians in that wave.<br>
    <b>Note:</b> These are pre-computed values from the workbook, not recalculated from raw ATU responses.
  </div>
</div>
""", unsafe_allow_html=True)

            # Section 2: Awareness by segment
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.18em;color:{TEAL};font-weight:700;margin-bottom:8px">UNAIDED AWARENESS — BY SEGMENT (Q2.10)</div>', unsafe_allow_html=True)
            try:
                seg_labels_row = aw_df.iloc[15].dropna().tolist()
                seg_vals_row   = aw_df.iloc[16].dropna().tolist()
                seg_ns_row     = aw_df.iloc[17].dropna().tolist()
                seg_labels = [str(s) for s in seg_labels_row if s != '% Aware']
                seg_vals   = [v for v in seg_vals_row if v != '% Aware']
                seg_ns     = [str(n).strip() for n in seg_ns_row]

                if seg_labels and seg_vals:
                    # Show THE STUDY DRUG awareness specifically
                    rows_html_aw = ""
                    for sl, sv, sn in zip(seg_labels[:8], seg_vals[:8], seg_ns[:8]):
                        try:
                            pct = round(float(sv)*100)
                            bg_s, fg_s = ("#15803D", "white") if pct>=70 else ("#FEF9C3","#713F12") if pct>=50 else ("#FEE2E2","#991B1B")
                            rows_html_aw += f'<tr><td style="padding:6px 10px;font-size:11px;color:#0F172A">{sl}</td><td style="padding:6px 8px;text-align:center"><span style="background:{bg_s};color:{fg_s};padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700">{pct}%</span></td><td style="padding:6px 8px;text-align:center;font-size:10px;color:#94A3B8">{sn}</td></tr>'
                        except: pass
                    if rows_html_aw:
                        st.markdown(f'<div style="font-size:12px;color:{DGRAY};margin-bottom:6px">% the study drug unaided awareness by segment — FY26 Q2</div>', unsafe_allow_html=True)
                        st.markdown(f'<table style="width:100%;border-collapse:collapse"><thead><tr style="background:{LGRAY}"><th style="padding:6px 10px;text-align:left;font-size:10px;color:{DGRAY};font-weight:600">Segment</th><th style="padding:6px 8px;text-align:center;font-size:10px;color:{DGRAY};font-weight:600">% Aware</th><th style="padding:6px 8px;text-align:center;font-size:10px;color:{DGRAY};font-weight:600">n</th></tr></thead><tbody>{rows_html_aw}</tbody></table>', unsafe_allow_html=True)
            except Exception as e:
                st.info(f"Could not parse segment awareness: {e}")

            # Section 3: Familiarity
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.18em;color:{TEAL};font-weight:700;margin-bottom:8px">AIDED FAMILIARITY — THE STUDY DRUG SCALE (Q2.20)</div>', unsafe_allow_html=True)
            try:
                fam_rows = {
                    'Have used': aw_df.iloc[26],
                    'Planning to use': aw_df.iloc[27],
                    'Familiar, not planning': aw_df.iloc[28],
                    'Heard of, no knowledge': aw_df.iloc[29],
                }
                fam_data = {}
                for label, row in fam_rows.items():
                    vals = row.dropna().tolist()
                    num_vals = [v for v in vals if isinstance(v, (int, float))]
                    fam_data[label] = num_vals

                if fam_data:
                    fig_fam = go.Figure()
                    colors_fam = [GREEN, TEAL, AMBER, CRIMSON]
                    for (label, vals), color in zip(fam_data.items(), colors_fam):
                        if vals:
                            fig_fam.add_trace(go.Bar(
                                name=label, x=[f"Treat {i+1}" for i in range(len(vals))],
                                y=[v*100 for v in vals[:8]],
                                marker_color=color,
                            ))
                    fig_fam.update_layout(
                        barmode="stack", height=320, showlegend=True,
                        plot_bgcolor="white", paper_bgcolor="white",
                        font=dict(family="Inter", size=10),
                        yaxis=dict(range=[0,105], title="% of HCPs", showgrid=True, gridcolor="#F1F5F9"),
                        legend=dict(orientation="h", yanchor="bottom", y=-0.35),
                        margin=dict(l=0,r=0,t=10,b=0),
                        title=dict(text="ATU Q2.20 Familiarity scale by treatment — FY26 Q2", font=dict(size=13)),
                    )
                    st.plotly_chart(fig_fam, use_container_width=True)
                    st.markdown(f'<div style="font-size:10px;color:#94A3B8">Source: GLIOMA_Q2_FY26_ATU_Workbook.xlsx · ATU Awareness & Familiarity sheet · rows 26–29 · ATU Q2.20 aided familiarity scale [1=Never heard → 5=Have used]</div>', unsafe_allow_html=True)
            except Exception as e:
                st.info(f"Could not parse familiarity: {e}")
        else:
            st.info("ATU Workbook awareness sheet not found.")

    # ── TAB 5: ATU Workbook — Usage ────────────────────────────────────────
    with tabs[4]:
        st.markdown(f"""
<div style="font-family:'DM Serif Display',serif;font-size:24px;color:#0F172A;margin-bottom:8px">
  ATU Workbook: the study drug Current & Typical Share by Segment
</div>
<div style="font-size:12px;color:#94A3B8;margin-bottom:16px">
  Source: GLIOMA_Q2_FY26_ATU_Workbook.xlsx · 'ATU Usage (current & future)' sheet.
  Pre-computed usage data by target type, specialty, and practice setting.
</div>
""", unsafe_allow_html=True)

        if 'ATU Usage (current & future)' in wb:
            us_df = wb['ATU Usage (current & future)']

            def _parse_usage_block(start_row, label, segments, seg_row):
                """Parse a current/typical usage block from the workbook."""
                try:
                    segs = [str(s) for s in us_df.iloc[seg_row].dropna().tolist() if s not in ['Grade','Glioma Subtype','Extent of Resection']]
                    astro_vals = [v for v in us_df.iloc[start_row].dropna().tolist() if isinstance(v, float)]
                    oligo_vals = [v for v in us_df.iloc[start_row+1].dropna().tolist() if isinstance(v, float)]
                    return segs, astro_vals, oligo_vals
                except: return [], [], []

            # Overall (row 7-9)
            st.markdown(f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.18em;color:{TEAL};font-weight:700;margin-bottom:8px">CURRENT THE STUDY DRUG SHARE — OVERALL (FY26 Q2)</div>', unsafe_allow_html=True)
            try:
                r7 = us_df.iloc[7].dropna().tolist()
                r9 = us_df.iloc[9].dropna().tolist()
                # r7: overall row with numeric values
                pt_labels = ['Adj GTR','Adj STR','Stable GTR','Stable STR','Recurr obs','Maint','Stable post-sys','Recurr post-sys']
                astro_vals_ov = [v for v in r7 if isinstance(v,(int,float))]
                oligo_vals_ov = [v for v in r9 if isinstance(v,(int,float))]

                if astro_vals_ov:
                    fig_ov = go.Figure()
                    x_labels = pt_labels[:len(astro_vals_ov)]
                    fig_ov.add_trace(go.Bar(name='Astrocytoma', x=x_labels, y=[v*100 for v in astro_vals_ov], marker_color=TEAL, text=[f"{v*100:.0f}%" for v in astro_vals_ov], textposition="outside"))
                    if oligo_vals_ov:
                        fig_ov.add_trace(go.Bar(name='Oligodendroglioma', x=x_labels[:len(oligo_vals_ov)], y=[v*100 for v in oligo_vals_ov], marker_color=NAVY, text=[f"{v*100:.0f}%" for v in oligo_vals_ov], textposition="outside"))
                    fig_ov.update_layout(barmode="group", height=300, plot_bgcolor="white", paper_bgcolor="white",
                                         font=dict(family="Inter",size=10),
                                         yaxis=dict(range=[0,35], title="the study drug share %", showgrid=True, gridcolor="#F1F5F9"),
                                         legend=dict(orientation="h", yanchor="bottom", y=-0.3),
                                         margin=dict(l=0,r=0,t=10,b=0))
                    st.plotly_chart(fig_ov, use_container_width=True)
                    st.markdown(f'<div style="font-size:10px;color:#94A3B8">Source: ATU Q3_60Z — current the study drug patient share across 8 patient type columns · n=100 · FY26 Q2</div>', unsafe_allow_html=True)
                    with st.expander("↳  How current the study drug share is calculated"):
                        st.markdown(f"""
<div style="background:{LGRAY};border-left:4px solid {TEAL};border-radius:0 10px 10px 0;padding:12px 14px">
  <div style="font-size:12px;color:#334155;line-height:1.6">
    <b>Question:</b> ATU Q3_60a — "How many of your [N] patients of this type are currently receiving Any the study drug (IDH inhibitor)-containing regimen?"<br>
    <b>Denominator:</b> Total patient count per patient type (ATU Q3_50Z or S0_120Z).<br>
    <b>Metric:</b> the study drug patients ÷ total patients per type = unweighted share.<br>
    <b>Patient types shown:</b> Adjuvant GTR, Adjuvant STR, Stable >6mo GTR, Stable >6mo STR, Recurrent/Progressive after observation, Maintenance post-RT/CT, Stable post-systemic therapy, Recurrent/Progressive after systemic therapy.<br>
    <b>This chart:</b> Values extracted directly from GLIOMA_Q2_FY26_ATU_Workbook.xlsx rows 7–9 — pre-computed by ZoomRx.
  </div>
</div>
""", unsafe_allow_html=True)
            except Exception as e:
                st.info(f"Could not parse overall usage: {e}")

            # By Target Type (rows 30-32)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.18em;color:{TEAL};font-weight:700;margin-bottom:8px">CURRENT THE STUDY DRUG SHARE — BY TARGET TYPE</div>', unsafe_allow_html=True)
            try:
                seg_row = us_df.iloc[30].dropna().tolist()
                ast_row = us_df.iloc[31].dropna().tolist()
                ol_row  = us_df.iloc[32].dropna().tolist()
                segs = [str(s) for s in seg_row if s not in [2,'','Grade','Glioma Subtype','Extent of Resection']]
                ast_v = [v for v in ast_row if isinstance(v, float)]
                ol_v  = [v for v in ol_row  if isinstance(v, float)]

                if segs and ast_v:
                    n_pairs = min(len(segs)//2, len(ast_v)//2, 4)
                    fig_tt = go.Figure()
                    seg_pairs = []
                    for j in range(0, len(segs)-1, 2):
                        if j//2 < len(ast_v):
                            seg_pairs.append(segs[j])
                    x_tt = seg_pairs[:4]
                    ast_tt = ast_v[:len(x_tt)]
                    fig_tt.add_trace(go.Bar(name='Astrocytoma (GTR)', x=x_tt, y=[v*100 for v in ast_tt], marker_color=TEAL, text=[f"{v*100:.0f}%" for v in ast_tt], textposition="outside"))
                    fig_tt.update_layout(barmode="group", height=260, plot_bgcolor="white", paper_bgcolor="white",
                                          font=dict(family="Inter",size=11),
                                          yaxis=dict(range=[0,70], title="the study drug share %"),
                                          margin=dict(l=0,r=0,t=10,b=0))
                    st.plotly_chart(fig_tt, use_container_width=True)
                    n_info = us_df.iloc[33].dropna().tolist()
                    if n_info: st.markdown(f'<div style="font-size:10px;color:#94A3B8">{n_info[0]} · Source: ATU workbook rows 30–33</div>', unsafe_allow_html=True)
            except Exception as e:
                st.info(f"Could not parse target type usage: {e}")
        else:
            st.info("ATU Workbook usage sheet not found.")

    # ── TAB 6: VA Used vs Not (PET × ATU) ────────────────────────────────
    with tabs[5]:
        # This matches matched HCPs only (PET × ATU overlap)
        hcps_df = eng.hcps_df
        if hcps_df is not None and 'any_va' in hcps_df.columns:
            pet_atu_df = hcps_df.copy()
            # Add perf cols from the base
            pet_base = _build_atu_hcp_base(eng)
            if pet_base is not None:
                pet_atu_df = pet_atu_df.merge(pet_base[['uid'] + [f'perf_{i}' for i in range(19)] + [f't2b_perf_{i}' for i in range(19)]], on='uid', how='left', suffixes=('','_raw'))

            n_va  = int(hcps_df['any_va'].sum())
            n_nva = int((hcps_df['any_va']==0).sum())
            n_ov  = len(hcps_df)

            st.markdown(f"""
<div style="background:white;border:1px solid {MGRAY};border-radius:12px;padding:14px 18px;margin-bottom:16px">
  <div style="font-size:14px;font-weight:600;color:#0F172A;margin-bottom:4px">
    Visual Aid Used vs Not Used — the study drug Performance (Matched HCPs only)
  </div>
  <div style="font-size:12px;color:{DGRAY}">
    Restricted to {n_ov} HCPs who completed both ATU and PET surveys.
    VA Used (n={n_va}): any of 10 content types in PET Q1_100Z = 1.
    No VA (n={n_nva}): all content types = 0.
  </div>
</div>
""", unsafe_allow_html=True)

            groups_va = [
                ("VA Used",  pet_atu_df['any_va'] == 1),
                ("No VA",    pet_atu_df['any_va'] == 0),
            ]
            split_desc_va = ("PET Q1_100Z — visual aid content types (10 binary items). VA Used = any item = 1 during most recent rep visit. No VA = all items = 0 or missing. Source: matched HCPs only (ATU+PET overlap, n=" + str(n_ov) + ").")
            _full_xt_section(pet_atu_df, groups_va, split_desc_va,
                             "ATU Q3_120Z the study drug col · PET Q1_100Z (VA content types)",
                             col_prefix="perf_", t2b_prefix="t2b_perf_",
                             is_3group=False)
        else:
            st.info("Upload ATU + PET files to enable this cross-tab.")

    # ── TAB 7: Download ───────────────────────────────────────────────────
    with tabs[6]:
        st.markdown(f'<div style="font-family:\'DM Serif Display\',serif;font-size:22px;color:#0F172A;margin-bottom:12px">Download All Cross-Tab Results</div>', unsafe_allow_html=True)

        all_rows = []
        for seg_col, seg_label, seg_source in [
            ('seg1', 'High vs Low vs Non-User', 'High_vs_Low_vs_No_User_ATU_PET_Segment.xlsx'),
            ('seg2', 'Rep-Driven', 'Rep_Driven_Attributes_ATU.xlsx'),
            ('seg3', 'Usage × PET Perception', 'ATU_Usage_and_PET_Perception.xlsx'),
        ]:
            segs = df[seg_col].dropna().unique().tolist()
            for i, attr in enumerate(ATTRS):
                row = {'Source file': seg_source, 'Segment variable': seg_label, 'Attribute': attr}
                raws = []
                for seg in segs:
                    sub = df[df[seg_col] == seg][f't2b_perf_{i}'].dropna()
                    raw = df[df[seg_col] == seg][f'perf_{i}'].dropna()
                    row[f'{seg} T2B%'] = f"{sub.mean()*100:.0f}%" if len(sub) > 0 else "—"
                    row[f'{seg} n'] = len(sub)
                    raws.append(raw)
                try:
                    if len(raws) > 2: _,p = kruskal(*[r for r in raws if len(r)>=3]) if sum(len(r)>=3 for r in raws)>=2 else (0,1.0)
                    else: _,p = mannwhitneyu(raws[0], raws[1], alternative='two-sided') if all(len(r)>=3 for r in raws) else (0,1.0)
                    row['p-value'] = round(p, 3)
                    row['Sig at 90%'] = 'Yes' if p < 0.10 else 'No'
                    row['Sig at 95%'] = 'Yes' if p < 0.05 else 'No'
                except: row['p-value'] = 'N/A'; row['Sig at 90%'] = 'N/A'; row['Sig at 95%'] = 'N/A'
                all_rows.append(row)

        out_df = pd.DataFrame(all_rows)
        st.dataframe(out_df, use_container_width=True, height=500)
        st.download_button("⬇ Download all results (CSV)",
                           data=out_df.to_csv(index=False),
                           file_name="crosstab_all_segments.csv", mime="text/csv")
