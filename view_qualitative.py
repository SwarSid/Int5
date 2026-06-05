"""Tab 4 — Qualitative Deep-Dive: clean visual insights from Q3 FY26 new questions + existing VR."""
import streamlit as st, pandas as pd, numpy as np
import plotly.graph_objects as go
import sys, os
try:
    from q3_data import UNAIDED,Q3_70A,Q3_70B,Q3_70C,Q3_125,Q3_162,Q3_335,Q3_202
    HQ3=True
except: HQ3=False

TEAL="#0F4C5C"; NAVY="#1E293B"; CRIMSON="#832232"; AMBER="#B8860B"; GREEN="#15803D"
PURPLE="#7C3AED"; BLUE="#0369A1"; LGRAY="#F8FAFC"; MGRAY="#E2E8F0"; DGRAY="#64748B"

def _section(title, color, icon=""):
    st.markdown(f"""
<div style="background:{color};border-radius:10px;padding:12px 18px;margin:20px 0 12px">
  <div style="font-size:13px;font-weight:600;color:white">{icon} {title}</div>
</div>""", unsafe_allow_html=True)

def _pct_bar(cats, title, color, n_base, note=""):
    labels=[c[0] for c in cats]; pcts=[c[2] for c in cats]; ns=[c[1] for c in cats]
    mx=max(pcts) if pcts else 50
    def _dim(hex_color):
        """Convert #RRGGBB to rgba with 0.55 opacity for non-peak bars."""
        h = hex_color.lstrip('#')
        r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return f"rgba({r},{g},{b},0.55)"
    clrs=[color if p==mx else _dim(color) for p in pcts]
    fig=go.Figure(go.Bar(
        x=pcts,y=labels,orientation='h',marker_color=clrs,
        text=[f"{p}%  (n={nn})" for p,nn in zip(pcts,ns)],
        textposition='outside',textfont=dict(size=12,color='#0F172A'),
    ))
    fig.update_layout(
        height=max(130,len(labels)*52),
        title=dict(text=f"{title}  <span style='font-size:11px;color:#94A3B8'>(n={n_base})</span>",
                   font=dict(size=13,family="DM Serif Display",color="#0F172A")),
        plot_bgcolor="white",paper_bgcolor="white",font=dict(family="Inter",size=11),
        xaxis=dict(range=[0,82],showgrid=True,gridcolor="#F1F5F9",showticklabels=False),
        yaxis=dict(autorange='reversed',tickfont=dict(size=12)),
        margin=dict(l=0,r=100,t=42,b=8),showlegend=False,
    )
    if note: fig.add_annotation(x=0,y=len(labels)+0.3,text=note,showarrow=False,
                                 font=dict(size=9,color=DGRAY),xanchor='left')
    return fig

def _insight_box(headline, body, color):
    st.markdown(f"""
<div style="background:{color}12;border-left:4px solid {color};border-radius:0 10px 10px 0;
     padding:12px 16px;margin-bottom:8px">
  <div style="font-size:12px;font-weight:700;color:{color};margin-bottom:4px">{headline}</div>
  <div style="font-size:11px;color:#334155;line-height:1.65">{body}</div>
</div>""", unsafe_allow_html=True)

def render(eng, hcps, filter_bar=None):
    if hcps is None or hcps.empty: st.warning("No data loaded."); return
    df = filter_bar(hcps, "qua") if filter_bar else hcps
    if df.empty: st.info("No HCPs match selected filters."); return

    st.markdown(f"""
<div style="margin-bottom:20px">
  <div style="font-size:9px;text-transform:uppercase;letter-spacing:.22em;color:{DGRAY};font-weight:600">QUALITATIVE DEEP-DIVE</div>
  <h1 style="font-family:'DM Serif Display',serif;font-size:40px;font-weight:300;color:#0F172A;line-height:1.1;margin-bottom:8px">
    Voice responses, decoded.</h1>
  <p style="font-size:12px;color:#475569;max-width:700px;line-height:1.65">
    Q3 FY26 ATU new questions (n≈78–103 per question) + existing ATU VR questions connected to ICI dimensions.
    All insights from uploaded data only. Question text shown for first-time reader context.
  </p>
</div>""", unsafe_allow_html=True)

    if not HQ3:
        st.info("Q3 FY26 Excel data not loaded. Upload Glioma_ATU_Q3_FY26_New_Questions2_0.xlsx.")
        return

    tabs = st.tabs(["📍 Who Prescribes?","🏥 GTR — Patient Journey","🧬 Evidence Gate",
                     "💊 Dosing & Safety","💬 Competitive Narrative","⬇ Download CSV"])

    # ── Tab 1: Who prescribes? ─────────────────────────────────────────────
    with tabs[0]:
        _section("Who prescribes THE STUDY DRUG? Broad adoption vs reserved use", GREEN, "👤")
        st.caption(f'"{Q3_162["q"]}"')
        c1,c2=st.columns([1.4,1])
        with c1:
            st.plotly_chart(_pct_bar(Q3_162['cats'],"Q3_162 — Prescribing typology",GREEN,Q3_162['n'],
                "Source: Q3_162 (new) · ATU Q3 FY26"),use_container_width=True)
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            _insight_box("52% are broad/universal adopters",
                "The majority are comfortable using the study drug as the primary adjuvant choice for eligible patients — not reserving for low-regret scenarios.",GREEN)
            _insight_box("23% champion young patients",
                "Young professional champions (age, fertility, function) represent a distinct segment — the INDIGO trial's young median age is resonating.",TEAL)
            _insight_box("13% are criteria-driven / data-waiting",
                "These HCPs need additional PFS or OS data to move beyond selective use. The OS data gap is quantified in Q3_70B (43% want more data).",AMBER)
            _insight_box("5% hesitant / not yet ready",
                "Small but disproportionately accessible via rep education. Primary blockers are evidence gaps, not access.",CRIMSON)

    # ── Tab 2: GTR patient journey ─────────────────────────────────────────
    with tabs[1]:
        _section("GTR definition — how do HCPs define Gross Total Resection?", NAVY, "🏥")
        c1,c2=st.columns(2)
        with c1:
            st.plotly_chart(_pct_bar(Q3_70A['cats'],"Q3_70AZP2 — Residual MRI read → the study drug qualification",NAVY,Q3_70A['n']),use_container_width=True)
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            _insight_box("67% say yes — GTR patient qualifies",
                "Even with minimal residual enhancement on post-op MRI, most HCPs would consider the patient eligible for the study drug.",NAVY)
            _insight_box("27% add conditions",
                "Conditional qualifiers: grade/IDH status clarification, clinical factors. These HCPs accept the label but add caveats — a teachable moment on NCCN 2025.",AMBER)
            _insight_box("5% say no — enhancement contraindicates",
                "Small but firm: enhancing disease = not eligible. Rep must address this miscategorisation directly.",CRIMSON)

        _section("Observation failure — what triggers treatment initiation?", TEAL, "📡")
        c3,c4=st.columns(2)
        with c3:
            st.plotly_chart(_pct_bar(Q3_70C['cats'],"Q3_70CZ — Observation failure triggers",TEAL,Q3_70C['n']),use_container_width=True)
        with c4:
            st.markdown("<br>",unsafe_allow_html=True)
            _insight_box("42% act on any MRI change",
                "The largest group uses any observable MRI change as their trigger — broadly aligned with tumour volume message (V12).",GREEN)
            _insight_box("37% also use neurological symptoms",
                "Neuro symptoms co-cited with MRI change by many. These HCPs may delay the study drug until symptoms emerge — a preventable delay.",AMBER)
            _insight_box("36% use a ≤10% volume threshold",
                "A meaningful minority apply a quantitative MRI threshold. TGR data (−1.3% the study drug vs +14.4% placebo) directly addresses this group.",TEAL)

    # ── Tab 3: Evidence gate ───────────────────────────────────────────────
    with tabs[2]:
        _section("What evidence is needed to initiate the study drug for GTR patients?", GREEN, "🧬")
        c1,c2=st.columns([1.4,1])
        with c1:
            st.plotly_chart(_pct_bar(Q3_70B['cats'],"Q3_70BZ — Evidence threshold for GTR→the study drug",GREEN,Q3_70B['n']),use_container_width=True)
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            _insight_box("43% want more data — OS or PFS",
                "28% need PFS data, 20% need OS data. This is the single largest IBC blocker for GTR patients — INDIGO trial PFS is available but OS is not yet mature.",CRIMSON)
            _insight_box("19% are already prescribing — no evidence needed",
                "These are the NCCN-aligned early adopters. They cleared the evidence gate and now need breadth and volume deepening.",GREEN)
            _insight_box("19% are waiting for radiographic progression",
                "These HCPs are using observation-first. They are not refusing the study drug — they are delaying it. The rep's job is to move the intervention point earlier.",AMBER)

        _section("How does tumour volume reduction influence treatment decisions?", NAVY, "📊")
        c3,c4=st.columns([1.4,1])
        with c3:
            st.plotly_chart(_pct_bar(Q3_125['cats'],"Q3_125 — Tumour volume reduction as a signal",NAVY,Q3_125['n']),use_container_width=True)
        with c4:
            st.markdown("<br>",unsafe_allow_html=True)
            _insight_box("36% use volume as an efficacy proxy",
                "Volume reduction confirms the drug is working — an adherence and continuation signal. V12 (TGR −1.3% vs +14.4%) speaks directly to this group.",NAVY)
            _insight_box("19% use volume change as a prescription trigger",
                "They initiate the study drug when they see MRI progression. Cross with Q3_70C: these are the ≤10% threshold group.",TEAL)
            _insight_box("14% are PFS/OS skeptics — volume insufficient",
                "This group explicitly states that volume reduction alone is not enough. They need survival data. Directly linked to the 43% who want more data in Q3_70B.",AMBER)

    # ── Tab 4: Dosing & safety ─────────────────────────────────────────────
    with tabs[3]:
        _section("Hepatotoxicity management — dose reduction and re-escalation", AMBER, "💊")
        c1,c2=st.columns([1.4,1])
        with c1:
            st.plotly_chart(_pct_bar(Q3_202['cats'][:6],"Q3_202 — Dose management after hepatotoxicity",AMBER,Q3_202['n']),use_container_width=True)
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            _insight_box("38% have no protocol — case-by-case",
                "The largest group makes individual decisions. This includes HCPs who haven't yet encountered hepatotoxicity. A standardised LFT monitoring protocol message is needed.",AMBER)
            _insight_box("25% re-escalate once LFTs normalise",
                "These HCPs follow what the label suggests. Rep can reinforce: re-escalation is appropriate and supported by the USPI.",GREEN)
            _insight_box("23% permanently discontinue at Grade 3/4",
                "Consistent with label guidance for severe hepatotoxicity. Not a misperception — rep should acknowledge and move to QuickStart/Tibsovo transition message.",NAVY)
            _insight_box("12% switch to TIBSOVO",
                "A meaningful minority convert hepatotoxicity into a competitor switch. Cross with CI dimension: competitor familiarity and ABR access barriers are co-predictors.",CRIMSON)

    # ── Tab 5: Competitive narrative ──────────────────────────────────────
    with tabs[4]:
        _section("How do HCPs counter patient preference for RT as 'one and done'?", PURPLE, "💬")
        c1,c2=st.columns([1.4,1])
        with c1:
            st.plotly_chart(_pct_bar(Q3_335['cats'],"Q3_335 — Countering RT finite-course preference",PURPLE,Q3_335['n']),use_container_width=True)
        with c2:
            st.markdown("<br>",unsafe_allow_html=True)
            _insight_box("41% lead with RT neurocognitive toxicity",
                "The strongest lever already in use. RT long-term neurocog is the primary counter-argument. Rep should reinforce this narrative with specific data.",PURPLE)
            _insight_box("31% cite PFS/OS efficacy data",
                "Clinical data users. Cross with Q3_70B evidence-seekers: the same HCPs who need OS data to prescribe are also the ones who cite it to counter RT.",NAVY)
            _insight_box("21% emphasise THE STUDY DRUG QoL / oral convenience",
                "These HCPs translate the oral daily tablet into a quality of life narrative — key for young, high-functioning patients (cross with Q3_162 young professional champions).",TEAL)
            _insight_box("17% don't counter — cede to patient preference",
                "This 17% is the most addressable group. They are not against the study drug — they lack a prepared counter-narrative. Direct coaching opportunity.",CRIMSON)

        st.markdown("<br>",unsafe_allow_html=True)
        _section("Unaided awareness — treatment landscape context", DGRAY, "📋")
        ua_cats=[(t,m,p) for t,m,p in UNAIDED]
        c3,c4=st.columns([1.4,1])
        with c3:
            st.plotly_chart(_pct_bar(ua_cats[:8],"ATU Q2_10Z — Unaided treatment mentions (Q3 FY26, n=96)",TEAL,96),use_container_width=True)
        with c4:
            st.markdown("<br>",unsafe_allow_html=True)
            _insight_box("IDH Inhibitors (76%) > the study drug (68%)",
                "Class-level awareness exceeds brand-level awareness. Some HCPs are aware of IDH inhibitors as a class without spontaneously naming the study drug by brand.",TEAL)
            _insight_box("Temozolomide (65%) — still top of mind",
                "The comparator remains highly salient. This is the standard-of-care frame the rep must shift from.",AMBER)
            _insight_box("Tibsovo (27%) — meaningful competitor salience",
                "Ivosidenib is present in unprompted awareness. CI dimension captures this competitive threat. Cross with comp_fam in the dashboard.",CRIMSON)

    # ── Tab 6: Download ───────────────────────────────────────────────────
    with tabs[5]:
        st.markdown(f'<div style="font-family:\'DM Serif Display\',serif;font-size:20px;color:#0F172A;margin-bottom:10px">Download coded qualitative data</div>',unsafe_allow_html=True)
        rows=[]
        for qdata,qname in [(Q3_162,'Q3_162'),(Q3_70A,'Q3_70A'),(Q3_70B,'Q3_70B'),
                            (Q3_70C,'Q3_70C'),(Q3_125,'Q3_125'),(Q3_335,'Q3_335'),(Q3_202,'Q3_202')]:
            for cat,n_c,pct in qdata['cats']:
                rows.append({'Question':qname,'Question text':qdata['q'][:80],'Category':cat,'n':n_c,'%':pct,'Base n':qdata['n']})
        out_df=pd.DataFrame(rows)
        st.dataframe(out_df, use_container_width=True)
        csv=out_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇ Download CSV",data=csv,file_name="q3_fy26_qual_coded.csv",mime="text/csv")
        st.caption("Source: Glioma_ATU_Q3_FY26_New_Questions2_0.xlsx — pre-coded categories only. ATU Q3 FY26.")
