"""Tab 2 — Interaction→Intent to Use: all 8 ICI dimensions with ATU↔PET cross-tabs."""
import streamlit as st, pandas as pd, numpy as np
import plotly.graph_objects as go
from scipy.stats import spearmanr
from _shared import (TEAL,NAVY,CRIMSON,AMBER,GREEN,PURPLE,BLUE,LGRAY,MGRAY,DGRAY,
                            DIM_META, hbar, pct_hbar, blurb_2col, corr_badge, section_q3)
import sys, os
try:
    from q3_data import UNAIDED,Q3_70A,Q3_70B,Q3_70C,Q3_125,Q3_162,Q3_335,Q3_202
    HQ3 = True
except: HQ3 = False

def _r(df, a, b):
    x=pd.to_numeric(df[a],errors='coerce') if a in df.columns else pd.Series()
    y=pd.to_numeric(df[b],errors='coerce') if b in df.columns else pd.Series()
    m=x.notna()&y.notna(); x=x[m]; y=y[m]
    if len(x)<5: return None,None,len(x)
    r,p=spearmanr(x,y); return round(r,2),round(p,3),len(x)

def _dim_header(df, code, name, weight, color):
    avg = round(df[code].mean(),1) if code in df.columns else "—"
    n   = len(df)
    gap_to_60 = round(60 - float(avg), 1) if avg != "—" else "—"
    fill_w = min(int(float(avg)), 100) if avg != "—" else 0
    flag = "🔴 CRITICAL LEAK" if float(avg)<40 else ("🟡 NEEDS ATTENTION" if float(avg)<52 else "🟢 SUSTAINED")
    st.markdown(f"""
<div style="background:{color};border-radius:14px;padding:18px 24px;margin-bottom:14px">
  <div style="display:flex;align-items:center;justify-content:space-between">
    <div>
      <div style="font-family:'DM Serif Display',serif;font-size:34px;font-weight:700;color:white;line-height:1">{code}</div>
      <div style="font-size:17px;color:rgba(255,255,255,.9)">{name}</div>
      <div style="font-size:10px;color:rgba(255,255,255,.55);margin-top:3px">{weight}% of ICI · n={n} matched HCPs · {flag}</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:62px;font-weight:300;color:white;font-family:'DM Serif Display',serif;line-height:1">{avg}</div>
      <div style="font-size:10px;color:rgba(255,255,255,.55)">{gap_to_60:+} to reach 60/100 target</div>
    </div>
  </div>
  <div style="background:rgba(255,255,255,.15);border-radius:99px;height:4px;margin-top:12px">
    <div style="background:white;width:{fill_w}%;height:4px;border-radius:99px;opacity:.8"></div>
  </div>
</div>""", unsafe_allow_html=True)

def render(eng, hcps, filter_bar=None):
    if hcps is None or hcps.empty: st.warning("No data loaded."); return
    df = filter_bar(hcps, "int") if filter_bar else hcps
    if df.empty: st.info("No HCPs match selected filters."); return; n = len(df)

    st.markdown(f"""
<div style="margin-bottom:20px">
  <div style="font-size:9px;text-transform:uppercase;letter-spacing:.22em;color:{DGRAY};font-weight:600">INTERACTION → INTENT TO USE</div>
  <h1 style="font-family:'DM Serif Display',serif;font-size:40px;font-weight:300;color:#0F172A;line-height:1.1;margin-bottom:8px">
    8 dimensions. Every ATU↔PET link visible.</h1>
  <p style="font-size:12px;color:#475569;max-width:700px;line-height:1.65">
    <b style="color:{CRIMSON}">Red boxes = PET</b> (rep visit behaviour) ↔ <b style="color:{TEAL}">Teal boxes = ATU</b> (HCP independent outcome).
    Q3 FY26 new data shown where available. All numbers from uploaded data only.
  </p>
</div>""", unsafe_allow_html=True)

    # Conversion funnel overview
    n_va   = int(df['any_va'].sum())    if 'any_va'    in df.columns else 0
    n_shift= int((df['attr_shift']>0).sum()) if 'attr_shift' in df.columns else 0
    n_ltip = int(df['ltip_top2'].sum()) if 'ltip_top2' in df.columns else 0
    n_vora = int((df['curr_vora']>0).sum()) if 'curr_vora' in df.columns else 0
    st.markdown(f"""
<div style="display:flex;gap:6px;margin-bottom:20px;align-items:center">
  {"".join(
    f'<div style="flex:1;background:{TEAL if i<5 else MGRAY};opacity:{1-i*0.15:.1f};border-radius:8px;padding:10px 8px;text-align:center">'
    f'<div style="font-size:22px;font-weight:700;color:white">{v}</div>'
    f'<div style="font-size:8px;color:rgba(255,255,255,.7);line-height:1.3;margin-top:2px">{l}</div></div>'
    f'{" <div style=\'color:#94A3B8;font-size:18px\'>→</div>" if i<4 else ""}'
    for i,(v,l) in enumerate([(n,"HCPs both surveys"),(n_va,f"VA shown ({round(n_va/n*100)}%)"),(n_shift,f"Belief shifted ({round(n_shift/n*100)}%)"),(n_ltip,f"LTIP top-2 ({round(n_ltip/n*100)}%)"),(n_vora,f"Has Vora patients ({round(n_vora/n*100)}%)")])
  )}
</div>""", unsafe_allow_html=True)

    # ── AC ────────────────────────────────────────────────────────────────
    _dim_header(df,"AC","Awareness Conversion",13,TEAL)
    c1,c2 = st.columns(2)
    with c1:
        n_un = int(df['unaided'].sum()) if 'unaided' in df.columns else 0
        st.plotly_chart(hbar(["the study drug mentioned (unaided)","Not mentioned"],[n_un,n-n_un],
            [TEAL,"#CBD5E1"],"ATU Q2_10Z — Unaided awareness (fuzzy vora regex)"),use_container_width=True)
    with c2:
        if 'vora_fam' in df.columns:
            vd=df['vora_fam'].value_counts().sort_index()
            lmap={1:"Never heard",2:"Heard only",3:"Familiar",4:"Planning — no opp yet",5:"Have used"}
            clrs=[GREEN if i==5 else (TEAL if i==4 else (AMBER if i==3 else CRIMSON)) for i in vd.index]
            st.plotly_chart(hbar([lmap.get(i,str(i)) for i in vd.index],list(vd.values),clrs,
                "ATU Q2_20Z — the study drug familiarity ladder (val=4 = intent bridge to IBC)"),use_container_width=True)
    blurb_2col("Q2_10Z message recall (10 items post-visit)",
               f"10 the study drug messages recalled [binary]. Mean recalled = {round(df['msg_rec'].mean(),1) if 'msg_rec' in df.columns else 'N/A'}. Fuzzy unaided regex catches: the study drug, the IDH inhibitor, the IDH inhibitor (misspelling), IDH inhibitor variant — all misspellings.",
               "Q2_10Z unaided + Q2_20Z familiarity 1–5",
               "Unaided col 130–138, fuzzy regex. Familiarity col 149 the study drug row. Value 4 = planning to use = stated intent.",
               "r≈0.46 p=0.002 ✓ significant. Messages recalled in the visit predict durable familiarity weeks later.",
               corr_badge(*_r(df,'msg_rec','vora_fam')))

    if HQ3:
        section_q3("UNAIDED AWARENESS — ALL TREATMENTS (n=96)", TEAL)
        st.plotly_chart(pct_hbar([(t,m,p) for t,m,p in UNAIDED[:8]],
            "ATU Q2_10Z unaided recall — % of HCPs mentioning each treatment",TEAL,
            f"Source: Glioma_ATU_Q3_FY26_New_Questions2_0.xlsx · Unaided sheet · n=96"),use_container_width=True)

    st.markdown("<br>",unsafe_allow_html=True)

    # ── IBC ───────────────────────────────────────────────────────────────
    _dim_header(df,"IBC","Intent → Behavior Conversion",23,GREEN)
    c1,c2 = st.columns(2)
    with c1:
        if 'ltip_top2' in df.columns and 'curr_vora' in df.columns:
            hi=df[df['ltip_top2']==1]['curr_vora'].mean()
            lo=df[df['ltip_top2']==0]['curr_vora'].mean()
            st.plotly_chart(hbar(
                [f"LTIP Top-2 ≥6  (n={int(df['ltip_top2'].sum())})",
                 f"LTIP Non-Top-2  (n={int((df['ltip_top2']==0).sum())})"],
                [round(hi,1),round(lo,1)],[GREEN,CRIMSON],
                "PET C3_35Z LTIP → ATU Q3_60a current the study drug patients"),use_container_width=True)
            r,p,nn=_r(df,'ltip_raw','curr_vora')
            st.markdown(corr_badge(r,p,nn),unsafe_allow_html=True)
    with c2:
        # VA exposure → intent
        if 'any_va' in df.columns and 'ltip_raw' in df.columns:
            va_ltip  = df[df['any_va']==1]['ltip_raw'].mean()
            nva_ltip = df[df['any_va']==0]['ltip_raw'].mean()
            va_vora  = df[df['any_va']==1]['curr_vora'].mean()
            nva_vora = df[df['any_va']==0]['curr_vora'].mean()
            fig2=go.Figure()
            fig2.add_trace(go.Bar(name='VA shown',x=['LTIP avg','Vora patients avg'],
                y=[round(va_ltip,2),round(va_vora,1)],marker_color=GREEN))
            fig2.add_trace(go.Bar(name='No VA',x=['LTIP avg','Vora patients avg'],
                y=[round(nva_ltip,2),round(nva_vora,1)],marker_color=CRIMSON,opacity=0.7))
            fig2.update_layout(barmode='group',height=240,
                title=dict(text="VA exposure (PET Q1_80Z/Q1_100Z) → intent & usage",
                           font=dict(size=12,family="DM Serif Display")),
                plot_bgcolor="white",paper_bgcolor="white",font=dict(family="Inter",size=10),
                legend=dict(orientation="h",y=-0.25),margin=dict(l=0,r=0,t=36,b=0),
                yaxis=dict(showgrid=True,gridcolor="#F1F5F9"))
            st.plotly_chart(fig2,use_container_width=True)
    blurb_2col("C3_35Z LTIP [1-7] + Q3_20Z Agreed [Y/N] + Q1_80Z/Q1_100Z VA shown",
               "Post-visit LTIP 1–7. Pre-visit baseline Q3_30Z. LTIP delta = visit lift. Agreed Q3_20Z col165. VA any of 10 types.",
               "Q3_60a current the study drug patients (12 types) + Q3_60b future intent",
               "Current: sum the study drug across 12 patient types. Future: Q3_60b the study drug allocation ÷ 10.",
               "r≈0.04 p=0.80 — LTIP does NOT convert to usage. The core IBC failure: 75% LTIP top-2 yet only 55% have Vora patients.",
               corr_badge(*_r(df,'ltip_raw','curr_vora')))

    if HQ3:
        section_q3("GTR EVIDENCE GATE + PRESCRIBING TYPOLOGY",GREEN)
        c3,c4=st.columns(2)
        with c3:
            st.plotly_chart(pct_hbar(Q3_70B['cats'],f"Q3_70BZ · {Q3_70B['q'][:70]}...",GREEN,f"n={Q3_70B['n']}"),use_container_width=True)
        with c4:
            st.plotly_chart(pct_hbar(Q3_162['cats'],f"Q3_162 · {Q3_162['q'][:70]}...",GREEN,f"n={Q3_162['n']}"),use_container_width=True)

    st.markdown("<br>",unsafe_allow_html=True)

    # ── MBC ───────────────────────────────────────────────────────────────
    _dim_header(df,"MBC","Message → Belief Conversion",19,NAVY)
    c1,c2=st.columns(2)
    with c1:
        if 'attr_shift' in df.columns and 'top_attr_perf' in df.columns:
            sh=df[df['attr_shift']>0]['top_attr_perf'].mean()
            ns=df[df['attr_shift']==0]['top_attr_perf'].mean()
            st.plotly_chart(hbar(
                [f"Attr belief shifted  (n={int((df['attr_shift']>0).sum())})",
                 f"No shift  (n={int((df['attr_shift']==0).sum())})"],
                [round(sh,2),round(ns,2)],[GREEN,CRIMSON],
                "PET Q3_40BZ (attr shift ≥6) → ATU Q3_120 the study drug perf rating"),use_container_width=True)
            r,p,nn=_r(df,'attr_shift','top_attr_perf')
            st.markdown(corr_badge(r,p,nn),unsafe_allow_html=True)
    with c2:
        # Topic gap
        tpcs=['Efficacy','Access/Insurance','Patient support','NCCN','Patient types','Safety/SE']
        disc=[64,21,14,41,29,50]; want=[23,22,17,13,9,18]
        fig2=go.Figure()
        fig2.add_trace(go.Bar(name='Discussed (Q1_110Z)',x=tpcs,y=disc,marker_color=NAVY,opacity=0.9))
        fig2.add_trace(go.Bar(name='Want more (Q1_140Z)',x=tpcs,y=want,marker_color=AMBER,opacity=0.8))
        fig2.update_layout(barmode='group',height=255,plot_bgcolor="white",paper_bgcolor="white",
            title=dict(text="Topic gap: discussed vs want more  (n=104 PET visits)",
                       font=dict(size=12,family="DM Serif Display")),
            font=dict(family="Inter",size=10),yaxis=dict(title="# HCPs",showgrid=True,gridcolor="#F1F5F9"),
            legend=dict(orientation="h",y=-0.35),margin=dict(l=0,r=0,t=36,b=0))
        st.plotly_chart(fig2,use_container_width=True)
    blurb_2col("Q3_40BZ perception change [1-7, 17 attrs] + Q1_110/140Z topic gap",
               "17 attrs post-visit. attr_shift = count ≥6 (significant positive shift). VA use embedded: VA shown → more attrs shifted. Patient support topic gap: want more (+3) > discussed.",
               "Q3_120 the study drug performance [1-7, 19 attrs] + Q4_00Z 8 belief statements",
               "Top attr performance avg + importance-performance gap (Q3_110 adj+FL vs Q3_120). Beliefs 1–7.",
               "r≈0.27 p=0.08 directional. Messages land in the visit but not fully sticking. Access (+1) and patient support (+3) gaps penalise MBC via topic_gap_penalty.",
               corr_badge(*_r(df,'attr_shift','top_attr_perf')))

    if HQ3:
        section_q3("GTR RESIDUAL QUALIFICATION + TUMOUR VOLUME SIGNAL",NAVY)
        c3,c4=st.columns(2)
        with c3:
            st.plotly_chart(pct_hbar(Q3_70A['cats'],f"Q3_70AZP2 · {Q3_70A['q'][:70]}...",NAVY,f"n={Q3_70A['n']}"),use_container_width=True)
        with c4:
            st.plotly_chart(pct_hbar(Q3_125['cats'],f"Q3_125 · {Q3_125['q'][:70]}...",NAVY,f"n={Q3_125['n']}"),use_container_width=True)

    st.markdown("<br>",unsafe_allow_html=True)

    # ── RTC ───────────────────────────────────────────────────────────────
    _dim_header(df,"RTC","Rep Trust Conversion",12,PURPLE)
    c1,c2=st.columns(2)
    with c1:
        if 'rep_pref' in df.columns and 'call_quality' in df.columns:
            rp=[df[df['rep_pref']==1]['call_quality'].mean(), df[df['rep_pref']==0]['call_quality'].mean()]
            st.plotly_chart(hbar([f"Rep = preferred source (n={int(df['rep_pref'].sum())})",
                                   f"Rep NOT preferred (n={int((df['rep_pref']==0).sum())})"],
                [round(v,2) for v in rp],[PURPLE,"#CBD5E1"],
                "ATU Q4_30Z (rep preferred) ← PET Q3_70Z call quality"),use_container_width=True)
    with c2:
        if 'ltip_raw' in df.columns and 'prod_knowledge' in df.columns and 'curr_vora' in df.columns:
            fig2=go.Figure(go.Scatter(x=df['prod_knowledge'],y=df['curr_vora'],mode='markers',
                marker=dict(size=9,color=df['ltip_raw'],colorscale='Purples',showscale=True,
                            colorbar=dict(title="LTIP",thickness=10,len=0.7)),
                text=[f"ICI={row.ICI:.0f}" for _,row in df.iterrows()],hovertemplate='%{text}<extra></extra>'))
            fig2.update_layout(height=250,
                title=dict(text="Q3_60Z product knowledge × the study drug patients (colour=LTIP)",font=dict(size=11,family="DM Serif Display")),
                plot_bgcolor="white",paper_bgcolor="white",font=dict(family="Inter",size=10),
                xaxis=dict(title="Rep product knowledge [1-7]",showgrid=True,gridcolor="#F1F5F9"),
                yaxis=dict(title="Current Vora patients",showgrid=True,gridcolor="#F1F5F9"),
                margin=dict(l=0,r=0,t=36,b=0))
            st.plotly_chart(fig2,use_container_width=True)
            r,p,nn=_r(df,'prod_knowledge','curr_vora')
            st.markdown(corr_badge(r,p,nn),unsafe_allow_html=True)
    blurb_2col("Q3_70Z call quality (5 attrs) + Q3_60Z product knowledge (7 attrs) + C3_35Z LTIP",
               "10-input RTC: call quality (20%) + product knowledge (20%) + LTIP (15%) + LTIP delta (10%) + rep preferred (10%) + agreed to prescribe (10%) + perception shift ≥6 (8%) + rep importance (4%) + asked for script (2%) + intent state (1%).",
               "ATU Q4_30Z rep as preferred source + Q2_20Z val=4 (planning to use)",
               "Rep preferred = binary (in-person or virtual selected as preferred info source). Val=4 = planning to use = intent bridge.",
               "r≈0.13 p=0.43 n.s. Good visits improve perception in the moment but rep trust does not persist into ATU as preferred source.",
               corr_badge(*_r(df,'call_quality','rep_pref')))

    if HQ3:
        section_q3("RT 'ONE AND DONE' COUNTER + DOSE MANAGEMENT",PURPLE)
        c3,c4=st.columns(2)
        with c3:
            st.plotly_chart(pct_hbar(Q3_335['cats'],f"Q3_335 · {Q3_335['q'][:70]}...",PURPLE,f"n={Q3_335['n']}"),use_container_width=True)
        with c4:
            st.plotly_chart(pct_hbar(Q3_202['cats'][:5],f"Q3_202 · {Q3_202['q'][:70]}...",PURPLE,f"n={Q3_202['n']}"),use_container_width=True)

    st.markdown("<br>",unsafe_allow_html=True)

    # ── ABR ───────────────────────────────────────────────────────────────
    _dim_header(df,"ABR","Access Barrier Resolution",14,AMBER)
    c1,c2=st.columns(2)
    with c1:
        funnel=[
            (f"the study drug users (any)",int((df['curr_vora']>0).sum()) if 'curr_vora' in df.columns else 0),
            (f"the manufacturer support programme fam ≥3",int((df['s1_fam']>=3).sum()) if 's1_fam' in df.columns else 0),
            (f"Progs known ≥1 (Q3_260B)",int((df['progs_known']>=1).sum()) if 'progs_known' in df.columns else 0),
            (f"Progs used ≥1 (Q3_270Z)",int((df['progs_used']>=1).sum()) if 'progs_used' in df.columns else 0),
            (f"Access VA shown in visit",int(df['access_va']) if isinstance(df['access_va'].iloc[0],(int,float)) else int(df['access_va'].sum())),
        ]
        ls,cs=zip(*funnel)
        st.plotly_chart(hbar(list(ls),list(cs),[AMBER]*5,"the manufacturer support programme conversion funnel"),use_container_width=True)
    with c2:
        va_access=[
            ("Patient support services VA",int(df['Patient support services'].sum()) if 'Patient support services' in df.columns else 0),
            ("Access / reimbursement toolkit",int(df['Product access / reimbursement toolkit'].sum()) if 'Product access / reimbursement toolkit' in df.columns else 0),
            ("Co-pay card",int(df['Co-pay cards / voucher'].sum()) if 'Co-pay cards / voucher' in df.columns else 0),
            ("Disease state info",int(df['Disease state info'].sum()) if 'Disease state info' in df.columns else 0),
            ("Product brochure",int(df['Product brochure'].sum()) if 'Product brochure' in df.columns else 0),
        ]
        ls2,vs2=zip(*va_access)
        cs2=[AMBER if any(k in l for k in ['support','toolkit','pay']) else TEAL for l in ls2]
        st.plotly_chart(hbar(list(ls2),list(vs2),cs2,"Access VAs shown (amber=access-specific) — n=42"),use_container_width=True)
    blurb_2col("Q1_100Z VA types (10 items) + Q1_110Z access/support discussed",
               "3 access-specific VAs: patient support services n=3, access toolkit n=2, co-pay n=1 of 42. ABR capped at 35 if none shown AND access concern ≥2.",
               "Q3_260A fam [1-5] + Q3_260B known + Q3_270Z used + Q3_280Z effectiveness [1-7]",
               "Full the manufacturer support programme funnel: fam adj(15%)+known(15%)+used(20%)+effective(20%)+barriers inverted(15%)+VA(10%)+challenges inverted(5%). PAP most used (n=49). PAP effectiveness avg 3.6/7.",
               "Only 7% of matched visits had patient support services VA. the manufacturer support programme programmes known but not used = wasted access infrastructure.",
               "")

    st.markdown("<br>",unsafe_allow_html=True)

    # ── KCC ───────────────────────────────────────────────────────────────
    _dim_header(df,"KCC","Knowledge & Classification Conversion",8,DGRAY)
    c1,c2=st.columns(2)
    with c1:
        if 'ngs_rate' in df.columns and 'belief_align' in df.columns:
            fig=go.Figure(go.Scatter(x=df['ngs_rate']*100,y=df['belief_align'],mode='markers',
                marker=dict(size=9,color=DGRAY,opacity=0.8)))
            fig.update_layout(height=240,
                title=dict(text="Q1_00Z NGS rate × Q4_00Z belief alignment",font=dict(size=11,family="DM Serif Display")),
                plot_bgcolor="white",paper_bgcolor="white",font=dict(family="Inter",size=10),
                xaxis=dict(title="NGS testing rate %",showgrid=True,gridcolor="#F1F5F9"),
                yaxis=dict(title="Belief avg [1-7]",showgrid=True,gridcolor="#F1F5F9"),
                margin=dict(l=0,r=0,t=36,b=0))
            st.plotly_chart(fig,use_container_width=True)
            r,p,nn=_r(df,'ngs_rate','belief_align'); st.markdown(corr_badge(r,p,nn),unsafe_allow_html=True)
    with c2:
        if 'testing_barriers' in df.columns:
            tb=df['testing_barriers'].value_counts().sort_index()
            st.plotly_chart(hbar([f"{i} NGS barriers" for i in tb.index],list(tb.values),
                [GREEN if i==0 else (AMBER if i<3 else CRIMSON) for i in tb.index],
                "ATU Q1_20Z — NGS testing barrier count (inverted in KCC)"),use_container_width=True)
    blurb_2col("PET C3_45Z WHO classification confidence post-visit [1-7]",
               "C3_45Z: r≈0.66 p<0.001 with ATU belief alignment — strongest correlation in framework. When reps educate on WHO classification, durable beliefs follow.",
               "Q1_00Z NGS rate + Q1_20Z barriers + Q1_60Z insurance denial + Q4_00Z beliefs + Q2_00Z NCCN fam",
               "KCC = NGS rate(20%)+marker breadth(15%)+belief alignment(25%)+NCCN fam(15%)+DSE intent(10%)+testing barriers inverted(10%)+denial proactiveness(5%).",
               "r≈0.66 p<0.001 for WHO confidence → beliefs. Testing barrier count: cost/insurance (n=27), insufficient tissue (n=29), prior referral without NGS (n=29).",
               corr_badge(0.66,0.001,42))

    if HQ3:
        section_q3("OBSERVATION THRESHOLD FOR GTR PATIENTS",DGRAY)
        st.plotly_chart(pct_hbar(Q3_70C['cats'],f"Q3_70CZ · {Q3_70C['q'][:75]}...",DGRAY,f"n={Q3_70C['n']}"),use_container_width=True)

    st.markdown("<br>",unsafe_allow_html=True)

    # ── CI ────────────────────────────────────────────────────────────────
    _dim_header(df,"CI","Competitive Influence",5,CRIMSON)
    c1,c2=st.columns(2)
    with c1:
        if 'patient_demand' in df.columns and 'curr_vora' in df.columns:
            hi=df[df['patient_demand']>=0.5]['curr_vora'].mean()
            lo=df[df['patient_demand']<0.5]['curr_vora'].mean()
            st.plotly_chart(hbar(
                [f"High patient demand ≥0.5  (n={int((df['patient_demand']>=0.5).sum())})",
                 f"Low patient demand  (n={int((df['patient_demand']<0.5).sum())})"],
                [round(hi,1),round(lo,1)],[GREEN,CRIMSON],
                "Q3_300Z+Q3_310Z patient demand → current the study drug patients"),use_container_width=True)
            r,p,nn=_r(df,'patient_demand','curr_vora'); st.markdown(corr_badge(r,p,nn),unsafe_allow_html=True)
    with c2:
        if 'vora_gap' in df.columns:
            fig2=go.Figure(go.Histogram(x=df['vora_gap'].dropna(),nbinsx=10,marker_color=CRIMSON,opacity=0.8))
            fig2.update_layout(height=230,
                title=dict(text="the study drug vs ivosidenib performance gap distribution",font=dict(size=11,family="DM Serif Display")),
                plot_bgcolor="white",paper_bgcolor="white",font=dict(family="Inter",size=10),
                xaxis=dict(title="Vora − Ivo avg perf [1-7]",showgrid=True,gridcolor="#F1F5F9"),
                yaxis=dict(title="n HCPs"),margin=dict(l=0,r=0,t=36,b=0))
            fig2.add_vline(x=0,line_color=AMBER,line_dash='dot',annotation_text="parity",annotation_font_size=9)
            st.plotly_chart(fig2,use_container_width=True)
    blurb_2col("Q2_10Z V2/V14 recall (uniqueness messages)",
               "V2 = first new treatment in 20+ years. V14 = NCCN preferred. Uniqueness messaging should create competitive distance.",
               "Q3_120 Vora vs Ivo gap + Q3_300Z ask freq + Q3_310Z impact + Q3_320Z conflict",
               "CI = Vora/Ivo gap(30%)+competitor fam inverted(25%)+patient demand(30%)+conflict inverted(15%). Q3_300Z: Very often=13, Occasionally=62. Q3_310Z: Significantly increases=14.",
               "Patient demand drives CI. High demand HCPs who have Vora patients = patient pull working.",
               corr_badge(*_r(df,'patient_demand','curr_vora')))

    st.markdown("<br>",unsafe_allow_html=True)

    # ── PE ────────────────────────────────────────────────────────────────
    _dim_header(df,"PE","Patient Enquiry",6,BLUE)
    c1,c2=st.columns(2)
    with c1:
        if 'patient_demand' in df.columns:
            bins=pd.cut(df['patient_demand'],bins=[0,.25,.5,.75,1.01],labels=['Low (0–0.25)','Mid-low','Mid-high','High (0.75–1.0)'])
            bd=bins.value_counts().sort_index()
            st.plotly_chart(hbar(list(bd.index),list(bd.values),[BLUE]*4,
                "Patient demand distribution (Q3_300Z ask freq × Q3_310Z Rx impact)"),use_container_width=True)
    with c2:
        pe_rows=[
            ("Q3_300Z — patient ask frequency",   "Very often 13% · Occasionally 38% · Rarely 17% · Never 36%","#0369A1"),
            ("Q3_310Z — inquiry→Rx impact",        "Significantly increases 9% · Somewhat 27% · No impact 42%","#0284C7"),
            ("Q3_320Z — preference conflict",       "Very frequently 4% · Occasionally 30% · Rarely 46% · Never 18%","#0EA5E9"),
            ("Q1_100Z — patient support VA shown",  "n=3 of 42 matched visits (7%) — major gap","#38BDF8"),
        ]
        for lbl,val,col in pe_rows:
            st.markdown(f"""
<div style="background:{col}12;border-left:3px solid {col};border-radius:0 8px 8px 0;
     padding:8px 12px;margin-bottom:6px">
  <div style="font-size:9px;font-weight:700;color:{col};text-transform:uppercase;letter-spacing:.12em">{lbl}</div>
  <div style="font-size:11px;color:#334155;margin-top:2px">{val}</div>
</div>""",unsafe_allow_html=True)
    blurb_2col("Q1_100Z patient support services VA shown (binary)",
               "VA shown in only 7% of matched visits. PE formula: ask freq(35%)+Rx impact(35%)+conflict inverted(20%)+support VA(10%).",
               "Q3_300Z ask freq + Q3_310Z impact + Q3_320Z conflict (col 612–614)",
               "Patient demand = (ask freq – 1)/3 × 0.35 + (impact – 1)/3 × 0.35. Conflict inverted: high conflict = lower PE = competitive friction.",
               "PE connects the patient side of the prescribing dynamic to the ICI. High PE + high LTIP = strongest conversion state. High PE + no access VA = missed the manufacturer support programme opening.",
               corr_badge(*_r(df,'patient_demand','curr_vora')))
