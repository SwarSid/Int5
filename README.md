# HCP Conversion Atlas — Interaction Conversion Index Dashboard

A Streamlit dashboard measuring how effectively rep interactions convert into prescribing behaviour for an IDH inhibitor in IDH-mutant glioma.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data inputs (sidebar)

Upload two workbooks:
- **ATU Workbook** — Awareness, Trial & Usage survey export (LimeSurvey format)
- **PET Workbook** — Promotional Effectiveness Tracker survey export

All ICI scores, clusters, and charts recompute automatically on upload.

## ICI dimensions

| Code | Dimension | Weight |
|------|-----------|--------|
| AC | Awareness Conversion | 13% |
| IBC | Intent → Behavior | 23% |
| MBC | Message → Belief | 19% |
| RTC | Rep Trust Conversion | 12% |
| ABR | Access Barrier Resolution | 14% |
| KCC | Knowledge & Classification | 8% |
| CI | Competitive Influence | 5% |
| PE | Patient Enquiry | 6% |

## Tabs

1. **Overview** — ICI explainer, scores by specialty / practice setting / on-off list
2. **Interaction → Intent to Use** — All 8 dimensions with ATU↔PET cross-tabs
3. **HCP Segmentation** — Sequential rule-based clustering (5 segments)
4. **Qualitative Deep-Dive** — Q3 new question coded insights
5. **Rep Support Card** — Next-call playbook filtered by specialty / setting / on-off list

## Filters

Every tab supports three filters extracted directly from the ATU workbook:
- Specialty (S0_30Z)
- Practice Setting (S0_60Z — Academic / Community)
- On/Off List (ATU col 3 — On-List / Off-List / Co-Loc)

## Cost

Zero API cost. Pure Python + Pandas + Plotly.
