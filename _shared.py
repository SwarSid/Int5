"""Shared visual helpers used across all tabs."""
import streamlit as st
import plotly.graph_objects as go

TEAL="#0F4C5C"; NAVY="#1E293B"; CRIMSON="#832232"; AMBER="#B8860B"; GREEN="#15803D"
PURPLE="#7C3AED"; BLUE="#0369A1"; LGRAY="#F8FAFC"; MGRAY="#E2E8F0"; DGRAY="#64748B"

DIM_META = [
    ("AC",  "Awareness Conversion",        13, TEAL,   "Unaided + familiarity ladder"),
    ("IBC", "Intent → Behavior",           23, GREEN,  "LTIP + agreed + current & future usage + VA exposure"),
    ("MBC", "Message → Belief",            19, NAVY,   "Attr shift + perception rating + topic gap"),
    ("RTC", "Rep Trust Conversion",        12, PURPLE, "Call quality + product knowledge + LTIP"),
    ("ABR", "Access Barrier Resolution",   14, AMBER,  "the manufacturer support programme funnel: aware→used→effective"),
    ("KCC", "Knowledge & Classification",   8, DGRAY,  "NGS rate + belief alignment + testing barriers"),
    ("CI",  "Competitive Influence",        5, CRIMSON,"Vora vs competitor gap + patient demand pull"),
    ("PE",  "Patient Enquiry",              6, BLUE,   "Patient ask freq + Rx impact + conflict inverted"),
]

def dim_badge(code, name, weight, color, avg=None):
    avg_str = f"<div style='font-size:28px;font-weight:300;color:white;line-height:1'>{avg}</div>" if avg else ""
    return f"""
<div style="background:{color};border-radius:10px;padding:12px 8px;text-align:center">
  <div style="font-size:18px;font-weight:700;color:white">{code}</div>
  <div style="font-size:9px;color:rgba(255,255,255,.6)">{weight}%</div>
  {avg_str}
  <div style="font-size:8px;color:rgba(255,255,255,.5);margin-top:2px;line-height:1.3">{name}</div>
</div>"""

def metric_card(label, value, sub, color=TEAL):
    return f"""
<div style="background:white;border:1px solid {MGRAY};border-radius:12px;padding:16px 12px;text-align:center">
  <div style="font-size:9px;text-transform:uppercase;letter-spacing:.16em;color:{DGRAY};font-weight:600">{label}</div>
  <div style="font-size:32px;font-weight:700;color:{color};font-family:'DM Serif Display',serif;line-height:1.1">{value}</div>
  <div style="font-size:10px;color:#94A3B8;margin-top:2px">{sub}</div>
</div>"""

def hbar(labels, values, colors, title, pct=False, max_x=None):
    mx = max_x or (max(values) * 1.35 if values else 10)
    text = [f"{v}%" if pct else str(v) for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation='h', marker_color=colors,
        text=text, textposition='outside', textfont=dict(size=11, color='#0F172A'),
    ))
    fig.update_layout(
        height=max(100, len(labels)*48),
        title=dict(text=title, font=dict(size=12, family="DM Serif Display", color="#0F172A")),
        plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Inter", size=10),
        xaxis=dict(range=[0, mx], showgrid=True, gridcolor="#F1F5F9", showticklabels=False),
        yaxis=dict(autorange='reversed', tickfont=dict(size=10)),
        margin=dict(l=0, r=70, t=36, b=0), showlegend=False,
    )
    return fig

def pct_hbar(cats, title, color=TEAL, note=""):
    """cats = list of (label, n, pct)"""
    labels = [c[0] for c in cats]
    pcts   = [c[2] for c in cats]
    ns     = [c[1] for c in cats]
    mx_p   = max(pcts) if pcts else 50
    bar_colors = [color if p == mx_p else f"{color}99" for p in pcts]
    fig = go.Figure(go.Bar(
        x=pcts, y=labels, orientation='h', marker_color=bar_colors,
        text=[f"<b>{p}%</b>  n={n}" for p, n in zip(pcts, ns)],
        textposition='outside', textfont=dict(size=11, color='#0F172A'),
    ))
    fig.update_layout(
        height=max(120, len(labels)*52),
        title=dict(text=title, font=dict(size=12, family="DM Serif Display", color="#0F172A")),
        plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Inter", size=10),
        xaxis=dict(range=[0, 85], showgrid=True, gridcolor="#F1F5F9", showticklabels=False),
        yaxis=dict(autorange='reversed', tickfont=dict(size=11, color="#0F172A")),
        margin=dict(l=0, r=90, t=38, b=8), showlegend=False,
    )
    if note: fig.add_annotation(x=0, y=len(labels)+0.2, text=note, showarrow=False,
                                 font=dict(size=8, color=DGRAY), xanchor='left')
    return fig

def blurb_2col(pet_q, pet_text, atu_q, atu_text, link, corr_html=""):
    st.markdown(f"""
<div style="background:white;border:1px solid {MGRAY};border-radius:12px;padding:16px 18px;margin:8px 0">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:10px">
    <div style="background:#FFF1F2;border-left:3px solid {CRIMSON};border-radius:0 8px 8px 0;padding:10px 12px">
      <div style="font-size:8px;text-transform:uppercase;letter-spacing:.18em;color:{CRIMSON};font-weight:700;margin-bottom:3px">PET · {pet_q}</div>
      <div style="font-size:11px;color:#334155;line-height:1.55">{pet_text}</div>
    </div>
    <div style="background:#F0F9FF;border-left:3px solid {TEAL};border-radius:0 8px 8px 0;padding:10px 12px">
      <div style="font-size:8px;text-transform:uppercase;letter-spacing:.18em;color:{TEAL};font-weight:700;margin-bottom:3px">ATU · {atu_q}</div>
      <div style="font-size:11px;color:#334155;line-height:1.55">{atu_text}</div>
    </div>
  </div>
  <div style="background:{LGRAY};border-radius:8px;padding:9px 12px;font-size:11px;color:#334155;line-height:1.6">
    <b>How they connect:</b> {link}
    {f"<br>{corr_html}" if corr_html else ""}
  </div>
</div>""", unsafe_allow_html=True)

def corr_badge(r, p, n=None):
    if r is None: return ""
    sig = ("✓ significant","#15803D","#DCFCE7") if p<0.05 else (("~ near-sig",AMBER,"#FEF9C3") if p<0.10 else ("n.s.",DGRAY,LGRAY))
    n_str = f" · n={n}" if n else ""
    return (f'<span style="background:{sig[2]};color:{sig[1]};padding:2px 8px;border-radius:4px;'
            f'font-size:10px;font-weight:600">r={r:.2f} · p={p:.3f} · {sig[0]}{n_str}</span>')

def section_q3(title, color):
    st.markdown(f"""
<div style="background:{color}15;border-left:3px solid {color};border-radius:0 8px 8px 0;
     padding:8px 14px;margin:18px 0 10px">
  <div style="font-size:9px;text-transform:uppercase;letter-spacing:.2em;color:{color};
       font-weight:700">Q3 FY26 NEW DATA · {title}</div>
</div>""", unsafe_allow_html=True)
