"""Tab 5 — Custom Rep Support Card: topic/message/perception/LTIP gaps → future intent."""
import streamlit as st, pandas as pd, numpy as np
from _shared import (TEAL,NAVY,CRIMSON,AMBER,GREEN,PURPLE,BLUE,LGRAY,MGRAY,DGRAY,DIM_META)

def render(eng, hcps, filter_bar=None):
    if hcps is None or hcps.empty: st.warning("No data loaded."); return
    df = filter_bar(hcps, "env") if filter_bar else hcps
    if df.empty: st.info("No HCPs match selected filters."); return

    st.markdown(f"""
<div style="margin-bottom:20px">
  <div style="font-size:9px;text-transform:uppercase;letter-spacing:.22em;color:{DGRAY};font-weight:600">REP SUPPORT CARD</div>
  <h1 style="font-family:'DM Serif Display',serif;font-size:38px;font-weight:300;color:#0F172A;line-height:1.1;margin-bottom:8px">
    Custom next-call playbook.</h1>
  <p style="font-size:12px;color:#475569;max-width:700px;line-height:1.65">
    Filtered by specialty, practice setting, and on/off-list status. Each card shows the gap,
    the data behind it, and exactly what to do in the next visit.
  </p>
</div>""", unsafe_allow_html=True)

    # ── Summary metrics ────────────────────────────────────────────────────
    n_f    = len(df)
    avg_ici= round(df['ICI'].mean(),1)
    n_ltip = int(df['ltip_top2'].sum())       if 'ltip_top2'  in df.columns else 0
    n_vora = int((df['curr_vora']>0).sum())   if 'curr_vora'  in df.columns else 0
    n_va   = int(df['any_va'].sum())           if 'any_va'     in df.columns else 0

    mc = st.columns(4)
    for col,(lbl,val,sub,clr) in zip(mc,[
        ("AVG ICI",      f"{avg_ici}",                  "/ 100",     TEAL),
        ("HAS VORA PTS", f"{round(n_vora/n_f*100)}%",  f"n={n_vora}",GREEN),
        ("LTIP TOP-2",   f"{round(n_ltip/n_f*100)}%",  f"n={n_ltip}",PURPLE),
        ("VA SHOWN",     f"{round(n_va/n_f*100)}%",     f"n={n_va}",  AMBER),
    ]):
        with col:
            st.markdown(f"""
<div style="background:white;border:1px solid {MGRAY};border-radius:10px;padding:12px;text-align:center">
  <div style="font-size:8px;text-transform:uppercase;letter-spacing:.16em;color:{DGRAY};font-weight:600">{lbl}</div>
  <div style="font-size:28px;font-weight:700;color:{clr};font-family:'DM Serif Display',serif;line-height:1.1">{val}</div>
  <div style="font-size:9px;color:#94A3B8">{sub}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Gap card helper — exactly 5 args ──────────────────────────────────
    def _gap(title, headline, body, evidence, color):
        st.markdown(f"""
<div style="background:white;border:1px solid {MGRAY};border-radius:12px;padding:16px 18px;margin-bottom:12px">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px">
    <div style="flex:2">
      <div style="font-size:9px;text-transform:uppercase;letter-spacing:.18em;color:{color};font-weight:700;margin-bottom:4px">{title}</div>
      <div style="font-size:14px;font-weight:600;color:#0F172A;margin-bottom:6px">{headline}</div>
      <div style="font-size:11px;color:#334155;line-height:1.65">{body}</div>
    </div>
    <div style="flex:1;background:{LGRAY};border-radius:8px;padding:10px 12px">
      <div style="font-size:9px;text-transform:uppercase;color:{DGRAY};font-weight:600;margin-bottom:4px">DATA EVIDENCE</div>
      <div style="font-size:10px;color:#475569;line-height:1.6">{evidence}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── 1. LTIP gap ───────────────────────────────────────────────────────
    ltip_avg     = round(df['ltip_raw'].mean(),1)   if 'ltip_raw'   in df.columns else 0
    ltip_delta   = round(df['ltip_delta'].mean(),1) if 'ltip_delta' in df.columns else 0
    ltip_top2_pct= round(n_ltip/n_f*100)
    if ltip_avg < 6:
        _gap(
            "LTIP GAP · PET C3_35Z",
            f"Post-visit prescribing intent {ltip_avg}/7 — below top-2 box",
            (f"{ltip_top2_pct}% of HCPs in this segment reached LTIP ≥6 post-visit. "
             f"Avg visit lift (post − pre) = {ltip_delta} points. "
             "Close every call with a specific commitment: "
             "'Based on today — will you consider this for your next eligible GTR patient?'"),
            (f"PET C3_35Z avg {ltip_avg}/7 · LTIP delta {ltip_delta} · "
             f"LTIP top-2 n={n_ltip}/{n_f} · Source: col 169 (post) vs col 168 (pre)"),
            CRIMSON,
        )

    # ── 2. Topic gap ──────────────────────────────────────────────────────
    topic_gap    = round(df['topic_gap_penalty'].mean(),2) if 'topic_gap_penalty' in df.columns else 0
    if topic_gap > 0:
        _gap(
            "TOPIC GAP · PET Q1_110Z vs Q1_140Z",
            "Access and patient support: more HCPs want them than are getting them",
            ("Access/insurance discussed in 21/104 visits but wanted in 22 (+1 gap). "
             "Patient support services discussed in 14/104 but wanted in 17 (+3 gap). "
             "Open the next call: 'I'd like to walk you through the patient support Co-Pay "
             "and Bridge Programme — can I take 5 minutes on this today?'"),
            (f"Topic gap penalty avg {topic_gap:.2f} · "
             "PET Q1_110Z col 97 (access discussed) vs Q1_140Z col 107 (want more) · "
             "Patient support: Q1_110Z col 99 vs Q1_140Z col 109"),
            AMBER,
        )

    # ── 3. Access VA gap ──────────────────────────────────────────────────
    access_va    = round(df['access_va'].mean(),1) if 'access_va' in df.columns else 0
    s1_fam       = round(df['s1_fam'].mean(),1)    if 's1_fam'    in df.columns else 0
    progs_known  = round(df['progs_known'].mean(),1)if 'progs_known'in df.columns else 0
    no_va_pct    = round((df['any_va']==0).mean()*100) if 'any_va' in df.columns else 0
    if access_va < 1:
        _gap(
            "ACCESS VA GAP · PET Q1_100Z",
            "Access-specific VAs (patient support, co-pay, toolkit) shown in < 1 visit avg",
            (f"{no_va_pct:.0f}% of HCPs in this segment had NO VA shown at all. "
             f"Manufacturer support programme familiarity is only {s1_fam}/5 — "
             f"programmes known avg {progs_known}/5. "
             "Bring the patient support leave-behind to every call. "
             "Showing the VA is what seeds programme awareness."),
            (f"access_va avg {access_va:.1f}/3 · any_va {round((1-no_va_pct/100)*100):.0f}% shown · "
             f"s1_fam {s1_fam}/5 · progs_known {progs_known}/5 · "
             "Source: PET Q1_100Z items: patient support col~81, co-pay col~83, toolkit col~86"),
            AMBER,
        )

    # ── 4. Perception gap ─────────────────────────────────────────────────
    top_attr     = round(df['top_attr_perf'].mean(),2)  if 'top_attr_perf'  in df.columns else 0
    attr_shift   = round(df['attr_shift'].mean(),1)      if 'attr_shift'     in df.columns else 0
    overall_perc = round(df['overall_perception'].mean(),1) if 'overall_perception' in df.columns else 0
    no_shift_pct = round((df['attr_shift']==0).mean()*100)  if 'attr_shift'  in df.columns else 0
    if top_attr < 5.0:
        _gap(
            "PERCEPTION GAP · ATU Q3_120 + PET Q3_40BZ",
            f"Product performance avg {top_attr}/7 — below 5.0 endorsement threshold",
            (f"Avg attribute belief shift in visit = {attr_shift}/17. "
             f"{no_shift_pct:.0f}% of visits produced zero belief shift. "
             f"Overall perception avg = {overall_perc}/7 immediately post-visit. "
             "Message priority: lead with PFS 61% vs placebo (V5) and TTNI 74% (V6). "
             "Anchor with the efficacy visual aid."),
            (f"Q3_40BZ attr shift avg {attr_shift} · Q3_120 Voranigo perf avg {top_attr}/7 · "
             f"overall_perception {overall_perc}/7 · "
             "Source: PET Q3_40BZ cols 173–189 + ATU Q3_120Z Voranigo cols 492–510"),
            NAVY,
        )

    # ── 5. DSE / classification gap ───────────────────────────────────────
    dse_avg  = round(df['dse'].mean(),2)           if 'dse'        in df.columns else 0
    ngs_avg  = round(df['ngs_rate'].mean()*100,0)  if 'ngs_rate'   in df.columns else 0
    beliefs  = round(df['belief_align'].mean(),1)  if 'belief_align'in df.columns else 0
    if dse_avg < 0.5:
        _gap(
            "DSE GAP · PET C1_18Z + ATU Q1_00Z",
            f"Only {round(dse_avg*100):.0f}% of HCPs applied DSE content to clinical decisions",
            (f"DSE intent to act (C1_18Z) = {round(dse_avg*100):.0f}%. "
             f"NGS testing rate avg = {ngs_avg:.0f}%. "
             f"Clinical belief alignment = {beliefs}/7. "
             "Open with IDH mutation classification and the NCCN 2025 GTR update. "
             "WHO Grade 2 IDH-mutant classification is the patient identification entry point."),
            (f"C1_18Z DSE intent {round(dse_avg*100):.0f}% · Q1_00Z NGS rate {ngs_avg:.0f}% · "
             f"Q4_00Z belief avg {beliefs}/7 · "
             "Source: PET C1_18Z col 50 + ATU Q1_00Z cols 80–87 + Q4_00Z"),
            DGRAY,
        )

    # ── 6. Patient demand gap ─────────────────────────────────────────────
    pd_avg      = round(df['patient_demand'].mean(),2)          if 'patient_demand'          in df.columns else 0
    conflict    = round(df['patient_conflict_pressure'].mean(),2)if 'patient_conflict_pressure'in df.columns else 0
    low_demand  = round((df['patient_demand']<0.25).mean()*100) if 'patient_demand'          in df.columns else 0
    if pd_avg < 0.5:
        _gap(
            "PATIENT ENQUIRY GAP · ATU Q3_300Z + Q3_310Z",
            f"Patient demand score {pd_avg:.2f} — patients not yet asking about this product",
            (f"{low_demand:.0f}% have very low patient demand (score < 0.25). "
             f"Patient preference conflict pressure = {conflict:.2f} (0=never, 1=very frequent). "
             "Provide patient-facing disease state materials and patient brochures. "
             "When patients ask about their IDH mutation, they are more likely to "
             "ask about targeted treatments by name."),
            (f"patient_demand {pd_avg:.2f} · conflict_pressure {conflict:.2f} · "
             "Source: ATU Q3_300Z col 612 (ask freq) + Q3_310Z col 613 (Rx impact) + "
             "Q3_320Z col 614 (conflict) · PE = ask(35%)+impact(35%)+conflict inv(20%)+VA(10%)"),
            BLUE,
        )

    # ── Footer note ───────────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:{LGRAY};border-radius:10px;padding:12px 16px;margin-top:8px">
  <div style="font-size:9px;text-transform:uppercase;letter-spacing:.16em;color:{DGRAY};font-weight:600;margin-bottom:4px">FILTERS</div>
  <div style="font-size:11px;color:#334155;line-height:1.6">
    Filtering by <b>Specialty</b> (ATU S0_30Z) · <b>Practice Setting</b> (ATU S0_60Z: Academic / Community) ·
    <b>On/Off-List</b> (ATU col 3: On-List / Off-List / Co-Loc). All three filters are applied globally
    from the filter bar above. n={n_f} HCPs shown.
  </div>
</div>""", unsafe_allow_html=True)
