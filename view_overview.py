"""Tab 1 — Overview: ICI explainer, scores by specialty/setting/target type."""
import streamlit as st, pandas as pd, numpy as np
import plotly.graph_objects as go
from _shared import (TEAL,NAVY,CRIMSON,AMBER,GREEN,PURPLE,BLUE,LGRAY,MGRAY,DGRAY,
                            DIM_META, dim_badge, metric_card, hbar)

def render(eng, hcps, filter_bar=None):
    if hcps is None or hcps.empty:
        st.warning("Upload ATU and PET workbooks in the sidebar to begin."); return

    # Apply global filters
    df = filter_bar(hcps, "ov") if filter_bar else hcps
    if df.empty: st.info("No HCPs match selected filters."); return

    n = len(df); avg_ici = round(df["ICI"].mean(), 1)
    n_vora = int((df['curr_vora']>0).sum()) if 'curr_vora' in df.columns else 0
    n_ltip = int(df['ltip_top2'].sum())     if 'ltip_top2' in df.columns else 0
    weakest = min([(k, round(df[k].mean(),1)) for k,*_ in DIM_META if k in df.columns], key=lambda x:x[1])

    # ── Masthead ──────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,{NAVY} 0%,{TEAL} 100%);border-radius:16px;
     padding:30px 36px;margin-bottom:22px">
  <div style="font-size:9px;text-transform:uppercase;letter-spacing:.3em;
       color:rgba(255,255,255,.45);font-weight:600;margin-bottom:6px">
    THE STUDY DRUG · IDH-MUTANT GLIOMA · HCP CONVERSION ATLAS</div>
  <div style="font-family:'DM Serif Display',serif;font-size:44px;font-weight:300;
       color:white;line-height:1.05;margin-bottom:10px">Interaction Conversion Index</div>
  <div style="font-size:13px;color:rgba(255,255,255,.7);max-width:680px;line-height:1.7">
    A 0–100 composite measuring how effectively the manufacturer support programme rep interactions convert into
    prescribing behaviour. <b style="color:white">8 dimensions</b> · {n} HCPs shown
    (ATU + PET matched). VA use and patient support services are embedded inside the
    relevant ICI dimensions.
  </div>
</div>""", unsafe_allow_html=True)

    # ── Metrics ───────────────────────────────────────────────────────────
    for col,(lbl,val,sub,clr) in zip(st.columns(5),[
        ("MATCHED HCPs", str(n), "Both surveys completed", TEAL),
        ("AVG ICI", f"{avg_ici}", "/ 100", GREEN if avg_ici>=55 else (AMBER if avg_ici>=45 else CRIMSON)),
        ("HAS VORA PATIENTS", f"{round(n_vora/n*100)}%", f"n={n_vora}", TEAL),
        ("LTIP TOP-2 BOX", f"{round(n_ltip/n*100)}%", "Post-visit intent ≥6/7", GREEN),
        ("CRITICAL LEAK", f"{weakest[0]}", f"avg {weakest[1]}/100", CRIMSON),
    ]): col.markdown(metric_card(lbl,val,sub,clr), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Dimension tiles ───────────────────────────────────────────────────
    st.markdown(f'<div style="font-family:\'DM Serif Display\',serif;font-size:24px;color:#0F172A;margin-bottom:12px">What is the ICI?</div>', unsafe_allow_html=True)
    for col,(k,nm,w,c,desc) in zip(st.columns(8), DIM_META):
        v = round(df[k].mean(),1) if k in df.columns else 0
        col.markdown(dim_badge(k,nm,w,c,v), unsafe_allow_html=True)

    st.markdown(f"""
<div style="background:{LGRAY};border-radius:10px;padding:14px 18px;margin-top:10px">
  <div style="font-family:monospace;font-size:12px;color:#334155;line-height:2.4">
    ICI = (AC×0.13) + (IBC×0.23) + (MBC×0.19) + (RTC×0.12) + (ABR×0.14) + (KCC×0.08) + (CI×0.05) + (PE×0.06)
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;font-size:11px;color:{DGRAY};line-height:1.7">
    <div>
      <b style="color:{NAVY}">Visual Aid use — embedded in ICI:</b> IBC (any VA shown lifts intent weight) ·
      MBC (Q3_40BZ attr shift counts VA-driven belief changes) · ABR (access-specific VAs feed the manufacturer support programme funnel)
    </div>
    <div>
      <b style="color:{NAVY}">Patient support services — embedded in ICI:</b> ABR (Q3_270Z used / Q3_280Z effective) ·
      PE (Q3_300Z patient asks + Q1_100Z patient support VA shown)
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    with st.expander("↳  Why these 8 dimensions? Why sequential clustering, not K-means?"):
        st.markdown(f"""
<div style="font-size:12px;color:#334155;line-height:1.75;padding:4px">
  <b>IBC (23%)</b> — outcome dimension: did prescribing actually happen vs stated intent?<br>
  <b>MBC (19%) + ABR (14%)</b> — most actionable single-visit levers.<br>
  <b>AC (13%) + RTC (12%)</b> — foundational, build over multiple interactions.<br>
  <b>PE (6%)</b> — patient-initiated the study drug enquiry and its Rx impact (Q3_300/310Z).<br>
  <b>KCC (8%)</b> — upstream identification: if HCP can't identify IDH-mutant Grade 2 patients, nothing else matters.<br>
  <b>CI (5%)</b> — competitive context: the study drug vs ivosidenib gap + patient demand.<br><br>
  <b>Why not K-means?</b> Two HCPs with ICI=42 can have completely different blockers — patient load vs evidence gap.
  K-means groups by statistical proximity, not clinical logic. Sequential tree ensures the first causal blocker wins,
  and a first-time reader can trace exactly why any HCP landed in their cluster.
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── ICI by segment ────────────────────────────────────────────────────
    st.markdown(f'<div style="font-family:\'DM Serif Display\',serif;font-size:24px;color:#0F172A;margin-bottom:12px">ICI scores by segment</div>', unsafe_allow_html=True)

    seg_groups = [c for c in ['specialty','setting','target_type'] if c in df.columns]
    seg_cols = st.columns(len(seg_groups))
    labels_nice = {'specialty':'By Specialty','setting':'By Practice Setting','target_type':'By On/Off-List'}

    for ci, seg_col in enumerate(seg_groups):
        with seg_cols[ci]:
            grp = df.groupby(seg_col).agg(ICI=('ICI','mean'), n=(seg_col,'count')).reset_index()
            grp = grp.sort_values('ICI', ascending=True)
            bar_colors = [GREEN if v>=52 else (TEAL if v>=48 else (AMBER if v>=44 else CRIMSON)) for v in grp['ICI']]
            fig = go.Figure(go.Bar(
                x=grp['ICI'].round(1), y=grp[seg_col], orientation='h',
                marker_color=bar_colors,
                text=[f"  {v:.1f}  n={int(nn)}" for v,nn in zip(grp['ICI'],grp['n'])],
                textposition='outside', textfont=dict(size=11,color='#0F172A'),
            ))
            fig.update_layout(
                height=max(160,len(grp)*62),
                title=dict(text=labels_nice.get(seg_col,seg_col), font=dict(size=13,family="DM Serif Display",color="#0F172A")),
                plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Inter",size=11),
                xaxis=dict(range=[0,82],showgrid=True,gridcolor="#F1F5F9",showticklabels=False),
                yaxis=dict(autorange='reversed'),
                margin=dict(l=0,r=90,t=40,b=0), showlegend=False,
                shapes=[dict(type='line',x0=avg_ici,x1=avg_ici,y0=-0.5,y1=len(grp)-0.5,
                             line=dict(color=AMBER,width=1.5,dash='dot'))],
                annotations=[dict(x=avg_ici,y=len(grp)-0.2,text=f"Avg {avg_ici}",
                                  showarrow=False,font=dict(size=9,color=AMBER),xanchor='left')]
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander(f"↳  All 8 dimensions by {labels_nice.get(seg_col,seg_col).lower()}"):
                rows=""
                for _, row in grp.sort_values('ICI',ascending=False).iterrows():
                    sub=df[df[seg_col]==row[seg_col]]
                    cells="".join(
                        f'<td style="padding:5px 7px;text-align:center;font-size:10px;font-weight:600;'
                        f'color:{"#15803D" if sub[k].mean()>=60 else "#B45309" if sub[k].mean()>=45 else "#991B1B"}">'
                        f'{round(sub[k].mean(),1)}</td>'
                        for k,*_ in DIM_META if k in df.columns
                    )
                    rows+=f'<tr><td style="padding:5px 10px;font-size:10px;font-weight:600;color:#0F172A">{row[seg_col]}</td>{cells}<td style="padding:5px 8px;text-align:center;font-size:10px;color:{DGRAY}">{int(row["n"])}</td></tr>'
                hdrs="".join(f'<th style="padding:5px 7px;font-size:8px;text-transform:uppercase;color:{col}">{k}</th>' for k,_,_,col,_ in DIM_META if k in df.columns)
                st.markdown(f"""
<div style="overflow-x:auto">
<table style="width:100%;border-collapse:collapse;font-family:Inter">
  <thead><tr style="background:{LGRAY}"><th style="padding:5px 10px;text-align:left;font-size:8px;text-transform:uppercase;color:{DGRAY}">Segment</th>{hdrs}<th style="font-size:8px;text-transform:uppercase;color:{DGRAY}">n</th></tr></thead>
  <tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)
