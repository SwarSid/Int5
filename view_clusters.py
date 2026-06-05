"""Tab 3 — HCP Segmentation: sequential clustering explainer with quantified leaks per segment."""
import streamlit as st, pandas as pd, numpy as np
import plotly.graph_objects as go
from _shared import (TEAL,NAVY,CRIMSON,AMBER,GREEN,PURPLE,BLUE,LGRAY,MGRAY,DGRAY, DIM_META)

CNAMES={1:"Patient ID Priority",2:"Intent-Led, Access-Pending",
        3:"Evidence Gap",4:"Narrative-Building Opportunity",5:"Conviction-Led Prescriber"}
CCOLORS={1:TEAL,2:NAVY,3:CRIMSON,4:AMBER,5:GREEN}
CICONS={1:"🔍",2:"🔒",3:"📋",4:"💬",5:"✅"}
CRULE={
    1:("gr2_pl ≤ 2  OR  the study drug familiarity < 3/5","ATU S0_120Z Grade 2 count + ATU Q2_20Z col149"),
    2:("(IBC ≥ 45 OR agreed=Y)  AND  (ABR < 40 OR access_va=0 AND barriers > 1)","PET C3_35Z LTIP + PET Q3_20Z + ICI ABR + PET Q1_100Z access VA"),
    3:("MBC < 40  OR  (top_attr_perf < 4.5  AND  attr_shift = 0)","ICI MBC score + ATU Q3_120 the study drug perf + PET Q3_40BZ shift count"),
    4:("IBC ≥ 50  AND  comp_fam ≥ 3.5  AND  CI < 50","ICI IBC + ATU Q2_20Z competitor fam + ICI CI score"),
    5:("All upstream gates cleared","Sequential tree: none of 1–4 fired"),
}
CLEAK={
    1:("Patient identification gap","Rep cannot have a product conversation without Grade 2 IDH patients. "
       "Avg the study drug familiarity = {vf:.1f}/5. Avg Grade 2 patient load = {pl:.1f}. "
       "{pct_low_fam:.0f}% have familiarity < 3. {pct_low_pl:.0f}% have ≤2 Grade 2 patients."),
    2:("Access blocking conversion","LTIP top-2 = {ltip_pct:.0f}% — intent present. Yet the manufacturer support programme "
       "progs known avg = {progs_known:.1f}/5, progs used = {progs_used:.1f}/5. "
       "Access VA shown in only {va_pct:.0f}% of visits. "
       "{no_va_pct:.0f}% had no access VA at all — the the manufacturer support programme conversation was never opened."),
    3:("Belief gap despite visits","Attr shift avg = {attr_shift:.1f}/17. "
       "the study drug performance avg = {vora_perf:.2f}/7. "
       "{pct_no_shift:.0f}% had zero attribute shift post-visit — visit produced no belief movement. "
       "Topic gap: patient support want more ({ps_want}) > discussed ({ps_disc}) in PET."),
    4:("Fragile uniqueness framing","Competitor familiarity avg = {comp_fam:.1f}/5. "
       "the study drug vs competitor gap = {vora_gap:+.2f}. "
       "CI avg = {ci:.1f}/100. Narrative built on 'first new treatment in 20 years' "
       "rather than clinical superiority — vulnerable when ivosidenib gains traction."),
    5:("No structural leak — focus on breadth","ICI avg = {ici:.1f}. "
       "Current Vora patients avg = {curr_vora:.1f}. "
       "{n} HCPs cleared all gates. Deepen volume per patient type and expand across patient types.")
}

def _leak_text(cid, sub):
    tmpl = CLEAK[cid][1]
    ns = dict(
        vf=sub['vora_fam'].mean()        if 'vora_fam' in sub.columns else 0,
        pl=sub['gr2_pl'].mean()          if 'gr2_pl' in sub.columns else 0,
        pct_low_fam=round((sub['vora_fam']<3).mean()*100) if 'vora_fam' in sub.columns else 0,
        pct_low_pl=round((sub['gr2_pl']<=2).mean()*100)   if 'gr2_pl' in sub.columns else 0,
        ltip_pct=round(sub['ltip_top2'].mean()*100)        if 'ltip_top2' in sub.columns else 0,
        progs_known=sub['progs_known'].mean()               if 'progs_known' in sub.columns else 0,
        progs_used=sub['progs_used'].mean()                 if 'progs_used' in sub.columns else 0,
        va_pct=round(sub['any_va'].mean()*100)              if 'any_va' in sub.columns else 0,
        no_va_pct=round((sub['any_va']==0).mean()*100)      if 'any_va' in sub.columns else 0,
        attr_shift=sub['attr_shift'].mean()                 if 'attr_shift' in sub.columns else 0,
        vora_perf=sub['top_attr_perf'].mean()               if 'top_attr_perf' in sub.columns else 0,
        pct_no_shift=round((sub['attr_shift']==0).mean()*100) if 'attr_shift' in sub.columns else 0,
        ps_want=17, ps_disc=14,
        comp_fam=sub['comp_fam'].mean()                     if 'comp_fam' in sub.columns else 0,
        vora_gap=sub['vora_gap'].mean()                     if 'vora_gap' in sub.columns else 0,
        ci=sub['CI'].mean()                                 if 'CI' in sub.columns else 0,
        ici=sub['ICI'].mean()                               if 'ICI' in sub.columns else 0,
        curr_vora=sub['curr_vora'].mean()                   if 'curr_vora' in sub.columns else 0,
        n=len(sub),
    )
    return tmpl.format(**ns)

def render(eng, hcps, filter_bar=None):
    if hcps is None or hcps.empty: st.warning("No data loaded."); return
    df = filter_bar(hcps, "clu") if filter_bar else hcps
    if df.empty: st.info("No HCPs match selected filters."); return
    n = len(df)

    st.markdown(f"""
<div style="margin-bottom:20px">
  <div style="font-size:9px;text-transform:uppercase;letter-spacing:.22em;color:{DGRAY};font-weight:600">HCP SEGMENTATION</div>
  <h1 style="font-family:'DM Serif Display',serif;font-size:40px;font-weight:300;color:#0F172A;line-height:1.1;margin-bottom:8px">
    Five engagement states.<br><span style="color:{TEAL}">Each with a quantified leak.</span>
  </h1>
</div>""", unsafe_allow_html=True)

    # ── Why sequential, not k-means ───────────────────────────────────────
    with st.expander("↳  Why sequential rule-based clustering — not K-means?", expanded=True):
        st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:4px">
  <div style="background:#FEE2E2;border-radius:10px;padding:14px 16px">
    <div style="font-size:11px;font-weight:700;color:{CRIMSON};margin-bottom:6px">❌  K-means would do this</div>
    <div style="font-size:11px;color:#334155;line-height:1.7">
      Group HCPs by statistical proximity of ICI scores. Two HCPs with ICI=42 and ICI=44 would land in the same cluster
      even if one is blocked by patient load and the other by evidence gaps — completely different rep actions needed.
      K-means optimises within-cluster variance, not clinical logic.
    </div>
  </div>
  <div style="background:#DCFCE7;border-radius:10px;padding:14px 16px">
    <div style="font-size:11px;font-weight:700;color:{GREEN};margin-bottom:6px">✅  Sequential tree does this</div>
    <div style="font-size:11px;color:#334155;line-height:1.7">
      Each HCP walks a causal decision tree. <b>Gate 1</b> (patient load/awareness) fires first.
      If not triggered, <b>Gate 2</b> (access) fires. Then Gate 3 (evidence), Gate 4 (narrative), Gate 5 (conviction).
      The first blocker that fires wins. A first-time reader can trace exactly why any HCP landed in their cluster.
      Dual blockers → earlier gate = primary cluster, later gate = secondary badge on rep support card.
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Cluster summary bars ──────────────────────────────────────────────
    counts = {cid: int((df['cluster']==cid).sum()) for cid in range(1,6)}
    avg_ici_c = {cid: round(df[df['cluster']==cid]['ICI'].mean(),1) if counts[cid]>0 else 0 for cid in range(1,6)}

    st.markdown("<br>",unsafe_allow_html=True)
    bar_c = st.columns(5)
    for i,cid in enumerate(range(1,6)):
        n_c=counts[cid]; pct=(round(n_c/n*100) if n>0 else 0)
        with bar_c[i]:
            st.markdown(f"""
<div style="background:{CCOLORS[cid]};border-radius:12px;padding:16px 10px;text-align:center">
  <div style="font-size:22px">{CICONS[cid]}</div>
  <div style="font-size:32px;font-weight:700;color:white;line-height:1;font-family:'DM Serif Display',serif">{n_c}</div>
  <div style="font-size:10px;color:rgba(255,255,255,.65);margin-top:3px">{pct}% of panel</div>
  <div style="font-size:9px;color:rgba(255,255,255,.5);margin-top:4px;line-height:1.3">{CNAMES[cid]}</div>
  <div style="background:rgba(255,255,255,.2);border-radius:4px;padding:3px 6px;margin-top:6px">
    <div style="font-size:13px;font-weight:600;color:white">ICI {avg_ici_c[cid]}</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)

    # ── Per-cluster detail ────────────────────────────────────────────────
    for cid in range(1,6):
        n_c=counts[cid]
        if n_c==0: continue
        sub=df[df['cluster']==cid]
        color=CCOLORS[cid]; name=CNAMES[cid]; icon=CICONS[cid]
        rule, sources = CRULE[cid]
        leak_title, _ = CLEAK[cid]
        leak_text = _leak_text(cid, sub)
        avg_ici_s=round(sub['ICI'].mean(),1)
        panel_ici=round(df['ICI'].mean(),1)
        delta=round(avg_ici_s-panel_ici,1)

        with st.expander(f"{icon}  {name}  ·  n={n_c}  ·  Avg ICI {avg_ici_s}  ·  {delta:+.1f} vs panel"):
            # Header
            st.markdown(f"""
<div style="background:{color};border-radius:10px;padding:14px 20px;margin-bottom:14px">
  <div style="font-size:20px;font-weight:300;color:white;font-family:'DM Serif Display',serif;margin-bottom:4px">{icon} {name}</div>
  <div style="font-size:11px;color:rgba(255,255,255,.75);line-height:1.5">
    <b>Trigger rule:</b> <code style="background:rgba(255,255,255,.15);padding:1px 6px;border-radius:3px;font-size:10px">{rule}</code><br>
    <b>Sources:</b> {sources}
  </div>
</div>""", unsafe_allow_html=True)

            col1, col2, col3 = st.columns([1.2, 1.4, 1.4])

            with col1:
                # ICI dim profile
                st.markdown(f'<div style="font-size:9px;text-transform:uppercase;letter-spacing:.15em;color:{color};font-weight:700;margin-bottom:6px">ICI DIM PROFILE</div>',unsafe_allow_html=True)
                dim_avgs=[round(sub[k].mean(),1) for k,*_ in DIM_META if k in sub.columns]
                dim_keys=[k for k,*_ in DIM_META if k in sub.columns]
                bar_colors=[GREEN if v>=60 else (TEAL if v>=50 else (AMBER if v>=40 else CRIMSON)) for v in dim_avgs]
                fig=go.Figure(go.Bar(y=dim_keys,x=dim_avgs,orientation='h',marker_color=bar_colors,
                    text=[str(v) for v in dim_avgs],textposition='outside',textfont=dict(size=10)))
                fig.update_layout(height=230,plot_bgcolor="white",paper_bgcolor="white",
                    font=dict(family="Inter",size=9),
                    xaxis=dict(range=[0,105],showgrid=True,gridcolor="#F1F5F9",showticklabels=False),
                    yaxis=dict(autorange='reversed'),margin=dict(l=0,r=40,t=8,b=0),showlegend=False)
                st.plotly_chart(fig,use_container_width=True)
                # Micro-stats
                n_vora_c=int((sub['curr_vora']>0).sum()) if 'curr_vora' in sub.columns else 0
                n_ltip_c=int(sub['ltip_top2'].sum()) if 'ltip_top2' in sub.columns else 0
                n_va_c=int(sub['any_va'].sum()) if 'any_va' in sub.columns else 0
                for lbl,v,nn in [("Has Vora pts",f"{round(n_vora_c/n_c*100)}%",n_vora_c),
                                  ("LTIP top-2",f"{round(n_ltip_c/n_c*100)}%",n_ltip_c),
                                  ("VA shown",f"{round(n_va_c/n_c*100)}%",n_va_c)]:
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid {MGRAY};font-size:10px"><span style="color:{DGRAY}">{lbl}</span><span style="font-weight:700;color:#0F172A">{v} ({nn})</span></div>',unsafe_allow_html=True)

            with col2:
                # Leak quantified
                st.markdown(f"""
<div style="background:{color}15;border:1px solid {color}44;border-radius:10px;padding:14px 14px;height:100%">
  <div style="font-size:9px;text-transform:uppercase;letter-spacing:.15em;color:{color};font-weight:700;margin-bottom:8px">⚠ LEAK: {leak_title.upper()}</div>
  <div style="font-size:11px;color:#334155;line-height:1.7">{leak_text}</div>
</div>""",unsafe_allow_html=True)

            with col3:
                # Rep action + specialty breakdown
                st.markdown(f'<div style="font-size:9px;text-transform:uppercase;letter-spacing:.15em;color:{color};font-weight:700;margin-bottom:6px">SPECIALTY MIX</div>',unsafe_allow_html=True)
                spec_dist=sub['specialty'].value_counts()
                fig2=go.Figure(go.Bar(y=spec_dist.index,x=spec_dist.values,orientation='h',
                    marker_color=[color]*len(spec_dist),
                    text=spec_dist.values,textposition='outside',textfont=dict(size=10)))
                fig2.update_layout(height=140,plot_bgcolor="white",paper_bgcolor="white",
                    font=dict(family="Inter",size=9),
                    xaxis=dict(showgrid=True,gridcolor="#F1F5F9",showticklabels=False,range=[0,max(spec_dist.max()*1.5,1)]),
                    yaxis=dict(autorange='reversed'),margin=dict(l=0,r=40,t=0,b=0),showlegend=False)
                st.plotly_chart(fig2,use_container_width=True)

                # Setting
                sett_dist=sub['setting'].value_counts()
                setting_html="  ·  ".join([f'<b>{k}</b>: {v}' for k,v in sett_dist.items()])
                st.markdown(f'<div style="font-size:10px;color:{DGRAY};margin-top:4px">{setting_html}</div>',unsafe_allow_html=True)

                # Secondary badge
                sec = sub['cluster_secondary'].dropna()
                if len(sec)>0:
                    sec_name=CNAMES.get(int(sec.iloc[0]),str(sec.iloc[0]))
                    st.markdown(f'<div style="background:{AMBER}22;border-left:3px solid {AMBER};border-radius:0 6px 6px 0;padding:6px 10px;margin-top:8px;font-size:10px;color:#92400E"><b>Secondary badge:</b> {sec_name}</div>',unsafe_allow_html=True)
