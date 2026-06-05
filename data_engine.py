"""
DataEngine: reads raw ATU + PET files by question-code scanning,
computes ICI sub-scores, clusters every HCP, and builds the
cross-tab/qualitative datasets.
"""

import pandas as pd
import numpy as np
import io
import re
from pathlib import Path
from scipy import stats as scipy_stats


# ── Label maps ─────────────────────────────────────────────────────────────────
FAM_MAP = {
    "Never heard of it": 1,
    "Heard of it, but don't know anything about it": 2,
    "Familiar with it, but not yet planning to use": 3,
    "Planning to use, but have not yet had opportunity": 4,
    "Have used it to treat IDH-mutant astrocytoma or oligodendroglioma": 5,
}
NCCN_MAP = {
    "Never heard of it": 1,
    "Heard of it, but don't know anything about it": 2,
    "A little familiar": 3,
    "Somewhat familiar": 4,
    "Very familiar": 5,
}
PTINQ_MAP = {"Very often": 4, "Occasionally": 3, "Rarely": 2, "Never": 1}
PEER_MAP = {
    "Yes, but only within my practice": 2,
    "Yes, with my practice and my extended peer network": 3,
    "No": 0,
    "Not yet, but intend to": 1,
}

VA_LABELS = {
    79: "Product brochure",
    80: "Package insert / PI",
    81: "Patient support services",
    82: "Co-pay cards / voucher",
    83: "Patient brochures",
    84: "Disease state info",
    85: "Product access / reimbursement toolkit",
    86: "Product distribution info",
    87: "Product admin / mgmt guide",
    88: "Product summary / flashcard",
}

ATTR_LABELS = [
    "Prolonged PFS", "Reduction in tumor volume", "Prolonged OS",
    "Low grade 3-4 AEs", "Low hepatic toxicity", "Low hematological toxicity",
    "Low neurotoxicity", "Low risk hypermutations", "Manageable LFT monitoring",
    "Good patient QoL", "Affordable", "Manufacturer patient services",
    "Easy to prescribe", "Convenient route", "Low risk long-term SEs",
    "Ability to preserve fertility", "Delays next treatment",
    "Reduces seizures", "Fair office compensation",
]


def _tn(v, d=0):
    try:
        return float(v)
    except Exception:
        return d


def _ms(v, mapping, d=0):
    if pd.isna(v):
        return d
    # Try numeric conversion first (values already 1-5 or 1-7)
    try:
        num = float(v)
        if 1 <= num <= max(mapping.values()):
            return num
    except (ValueError, TypeError):
        pass
    sv = str(v).strip()
    return mapping.get(sv, d)


def _read_raw(src):
    """Read Excel, return (raw_df, qcode_row_idx, data_start_idx)."""
    if isinstance(src, (str, Path)):
        raw = pd.read_excel(src, header=None)
    else:
        raw = pd.read_excel(io.BytesIO(src), header=None)
    return raw


def _find_qcode_row(raw):
    """Return row index where question codes like Q2_10Z appear."""
    for i in range(min(8, len(raw))):
        row = raw.iloc[i]
        if any(re.match(r"[QCS]\d+_\d+", str(v)) for v in row.values):
            return i
    return 2  # default


class DataEngine:
    def __init__(self):
        self.atu_raw = None
        self.pet_raw = None
        self.atu_qcodes = None
        self.pet_qcodes = None
        self.atu = None
        self.pet = None
        self.hcps_df = None
        self.xtab_df = None
        self._errors = []

    # ── Loading ───────────────────────────────────────────────────────────────
    def load_project(self):
        """Load from /mnt/project if running locally. On Streamlit Cloud this
        path won't exist — return an empty engine so the upload UI shows."""
        p = Path("/mnt/project")
        atu_path = p / "GLIOMA_ATU_Q126_Q226.xlsx"
        pet_path = p / "GLIOMA_PET_Q425_Q126_Q226.xlsx"
        if atu_path.exists() and pet_path.exists():
            self._load(atu_path, pet_path)
        # If files don't exist (Streamlit Cloud), engine stays empty —
        # app.py will show the upload UI instead.

    def load_from_bytes(self, atu_bytes, pet_bytes):
        self._load(atu_bytes, pet_bytes)

    @property
    def is_loaded(self):
        return self.hcps_df is not None and not self.hcps_df.empty

    def _load(self, atu_src, pet_src):
        self.atu_raw = _read_raw(atu_src)
        self.pet_raw = _read_raw(pet_src)

        atu_qrow = _find_qcode_row(self.atu_raw)
        pet_qrow = _find_qcode_row(self.pet_raw)

        self.atu_qcodes = self.atu_raw.iloc[atu_qrow].values
        self.pet_qcodes = self.pet_raw.iloc[pet_qrow].values

        self.atu = self.atu_raw.iloc[atu_qrow + 1:].reset_index(drop=True)
        self.pet = self.pet_raw.iloc[pet_qrow + 1:].reset_index(drop=True)

        # Normalize User Id — col index 1 may be int or str depending on platform
        def _get_uid_col(df):
            for key in [1, "1"]:
                if key in df.columns:
                    return df[key]
            return df.iloc[:, 1]

        self.atu["uid"] = pd.to_numeric(_get_uid_col(self.atu), errors="coerce")
        self.pet["uid"] = pd.to_numeric(_get_uid_col(self.pet), errors="coerce")
        self.atu = self.atu.dropna(subset=["uid"])
        self.pet = self.pet.dropna(subset=["uid"])
        self.atu["uid"] = self.atu["uid"].astype(int)
        self.pet["uid"] = self.pet["uid"].astype(int)

        self._build_hcps()
        self._build_xtab_dataset()

    # ── Column helpers ────────────────────────────────────────────────────────
    def _ac(self, prefix):
        return [i for i, v in enumerate(self.atu_qcodes) if str(v).startswith(prefix)]

    def _pc(self, prefix):
        return [i for i, v in enumerate(self.pet_qcodes) if str(v).startswith(prefix)]

    # ── HCP extraction ────────────────────────────────────────────────────────
    def _build_hcps(self):
        overlap_ids = sorted(set(self.atu["uid"]) & set(self.pet["uid"]))
        q220a = self._ac("Q2_20Z")
        q3120a = self._ac("Q3_120Z")
        q4300a = self._ac("Q4_30Z")

        records = []
        for uid in overlap_ids:
            a = self.atu[self.atu["uid"] == uid].iloc[0]
            p = self.pet[self.pet["uid"] == uid].iloc[0]

            # Patient load
            gc = self._ac("S0_120Z")
            gr2_pl = max(
                _tn(a[gc[0]] if gc else 0, 0)
                + _tn(a[gc[1]] if len(gc) > 1 else 0, 0),
                1,
            )

            # ── AC inputs ──
            # AC: Unaided awareness — fuzzy match across ALL Q2_10Z cols
            # Captures: the study drug, the IDH inhibitor, IDH inhibitor variant, IDH inhibitor variant, IDH inhibitor variant,
            # the IDH inhibitor (misspelling), voras (any misspelling starting with vor-)
            _vora_pat = re.compile(
                r"vor[a-z]*(?:sidenib|sinib|sanib|saneb|sidinib|anigo|anigeo|anig|asid)?",
                re.IGNORECASE
            )
            unaided = int(
                any(
                    _vora_pat.search(str(a[c] if not pd.isna(a[c]) else ""))
                    for c in self._ac("Q2_10Z")
                )
            )
            vf = q220a[10] if len(q220a) > 10 else None
            vora_fam = _ms(a[vf] if vf is not None else np.nan, FAM_MAP) or 1
            pt_inq = _ms(a[612] if 612 < len(a) else np.nan, PTINQ_MAP) or 1
            q210p = self._pc("Q2_10Z")
            msg_rec = sum(1 for c in q210p if _tn(p[c], 0) == 1)

            # ── IBC inputs ──
            curr_vora = min(
                sum(
                    _tn(a[self._ac(f"Q3_60Z_{pt}")[7]], 0)
                    for pt in range(1, 13)
                    if len(self._ac(f"Q3_60Z_{pt}")) > 7
                ),
                gr2_pl,
            )
            fut = sum(
                _tn(a[self._ac(f"Q3_60Z_{pt}")[19]], 0)
                for pt in range(1, 13)
                if len(self._ac(f"Q3_60Z_{pt}")) > 19
            )
            future_intent = min(fut / 10.0, 10.0)
            # Q3_20Z: agreed to prescribe for next appropriate patient (col 165)
            agreed = 1 if str(p[165] if 165 < len(p) else "N").strip().upper() in ["Y", "YES", "1"] else 0
            peer_shared = PEER_MAP.get(str(p[167] if 167 < len(p) else "").strip(), 0)
            like_inc = _tn(p[169] if 169 < len(p) else 4, 4)
            # Q2_20Z the study drug familiarity ladder: 4=Planning to use (intent state) — not yet used but intends
            # This bridges the gap between awareness (AC) and behavior (IBC)
            vf_intent = int(_tn(a[149] if 149 < len(a) else 4, 4) == 4)  # col149 = the study drug row, 4=Planning
            # Q3_110Z: importance ratings — adjuvant cols 432-450, first-line cols 451-469 (already in MBC)
            # Stored here for IBC: high importance + zero current usage = strongest unmet intent signal
            q3110a = self._ac("Q3_110Z")
            imp_adj = np.mean([_tn(a[c],np.nan) for c in q3110a[:19] if not np.isnan(_tn(a[c],np.nan))]) if q3110a else 4.0
            imp_fl  = np.mean([_tn(a[c],np.nan) for c in q3110a[19:38] if not np.isnan(_tn(a[c],np.nan))]) if len(q3110a)>19 else 4.0

            # ── MBC inputs ──
            vp = [_tn(a[c], np.nan) for c in q3120a[20:39]]
            vp = [v for v in vp if not np.isnan(v) and v > 0]
            top_attr_perf = np.mean(vp) if vp else 4.0
            q340p = self._pc("Q3_40BZ")
            # Q3_40BZ: perception change post-visit (17 attrs, 1-7; 4=no change, 6-7=significant positive)
            attr_shift = sum(1 for c in q340p if _tn(p[c], 0) >= 6)
            # Q3_40BZ overall perception (col 173) — first col in block
            overall_perception = _tn(p[q340p[0]] if q340p else np.nan, 4)
            q220p = self._pc("Q2_20Z")
            mv = [_tn(p[c], 0) for c in q220p if _tn(p[c], 0) > 0]
            motiv_score = np.mean(mv) if mv else 3.0
            q1100p = self._pc("Q1_100Z")
            access_va = min(sum(1 for c in q1100p if _tn(p[c], 0) == 1), 3)
            # Topic gap: Q1_110Z discussed vs Q1_140Z want more
            # Access gap: col97 want_more=1 AND col89 (access) NOT discussed → unmet access need
            q1110p = self._pc("Q1_110Z"); q1140p = self._pc("Q1_140Z")
            # access discussed = q1110p[8], want more access = q1140p[8]
            access_disc  = _tn(p[q1110p[8]] if len(q1110p)>8 else np.nan, 0)
            access_want  = _tn(p[q1140p[8]] if len(q1140p)>8 else np.nan, 0)
            support_disc = _tn(p[q1110p[10]] if len(q1110p)>10 else np.nan, 0)
            support_want = _tn(p[q1140p[10]] if len(q1140p)>10 else np.nan, 0)
            # topic_gap_penalty: want more access/support but not discussed = negative MBC signal
            topic_gap_penalty = max(0, (access_want - access_disc) + (support_want - support_disc))

            # ── RTC inputs ──
            # PET Q3_70Z: Overall call quality — 5 items (cols 211-215)
            # Overall call quality, preparedness, organisation, indication knowledge, time use [1-7 each]
            q370p = self._pc("Q3_70Z")
            cqv = [_tn(p[c], np.nan) for c in q370p]
            cqv = [v for v in cqv if not np.isnan(v) and v > 0]
            call_quality = np.mean(cqv) if cqv else 5.0

            # PET Q3_60Z: Product-specific rep performance — 7 items (cols 204-210)
            # the study drug knowledge, landscape knowledge, compelling reason, clear message,
            # credible support, address questions, engaging [1-7 each]
            q360p = self._pc("Q3_60Z")
            pkv = [_tn(p[c], np.nan) for c in q360p]
            pkv = [v for v in pkv if not np.isnan(v) and v > 0]
            prod_knowledge = np.mean(pkv) if pkv else 5.0

            # PET Q3_55Z: Rep attribute IMPORTANCE — 100-point allocation across 13 attrs (cols 191-203)
            # Weights what HCP cares most about: preparedness, time use, the study drug knowledge etc.
            # Top-weighted attrs: preparedness (avg 11.4), clear message (10.6), time use (10.5)
            q355p = self._pc("Q3_55Z")
            imp_weights = {c: _tn(p[c], 0) for c in q355p if c < len(p)}
            # the study drug-specific importance (col195 = the study drug knowledge, col197 = compelling reason)
            vora_rep_importance = sum(_tn(p[c], 0) for c in q355p[4:9] if c < len(p)) / 50.0  # normalise

            # PET C3_35Z: Likelihood to Increase Prescribing (LTIP) post-visit [1-7] (col 169)
            ltip_raw = _tn(p[169] if 169 < len(p) else 4, 4)
            ltip_norm = (ltip_raw - 1) / 6  # normalised 0-1

            # PET Q3_30Z: Pre-interaction LTIP baseline [1-7] (col 168) — before the visit
            pre_ltip = _tn(p[168] if 168 < len(p) else 4, 4)
            # LTIP delta: how much did the visit CHANGE intent? Positive = visit added value
            ltip_delta = max(0, ltip_raw - pre_ltip)  # only reward positive shift

            # PET Q3_10Z: Rep asked for the script [Y/N] (col 164)
            asked_q310 = 1 if str(p[164] if 164 < len(p) else "").strip().upper() in ["Y","YES","1"] else 0
            # PET Q3_20Z: HCP agreed to prescribe for next appropriate patient [Y/N] (col 165)
            agreed_q320 = 1 if str(p[165] if 165 < len(p) else "").strip().upper() in ["Y","YES","1"] else 0
            # PET Q3_25Z / C3_25Z: Shared with peers or beyond (col 166-167)
            prev_rx = 1 if str(p[167] if 167 < len(p) else "").strip().upper() in ["Y","YES","1"] else 0

            # ATU Q4_30Z: In-person or virtual rep listed as preferred information source (cols 634-635)
            rep_pref = 1 if any(_tn(a[c], 0) == 1 for c in q4300a[:2]) else 0

            # ATU Q2_20Z the study drug col 149 — familiarity intent state
            # Value 4 = "Planning to use, not yet had opportunity" = stated intent in ATU
            vf_intent_state = int(_tn(a[149] if 149 < len(a) else 4, 4) == 4)

            # ── ABR inputs ──
            # ATU Q3_260A (col 586): the manufacturer support programme familiarity [1=Not at all → 5=Extremely]
            s1_fam = _tn(a[586] if 586 < len(a) else 1, 1)

            # ATU Q3_260B (cols 587-592): the manufacturer support programme programmes AWARE OF [5 binary items + None]
            # Commercial Co-Pay, Bridge, PAP, QuickStart, Letter of Medical Necessity
            q3260b = self._ac("Q3_260BZ")
            progs_known = sum(1 for c in q3260b[:5] if _tn(a[c], 0) == 1)  # exclude "None" col

            # ATU Q3_270Z (cols 593-598): the manufacturer support programme programmes ACTUALLY USED [5 binary + None]
            # Co-Pay n=35, Bridge n=12, PAP n=49, QuickStart n=19, Letters n=12
            q3270 = self._ac("Q3_270Z")
            progs_used = sum(1 for c in q3270[:5] if _tn(a[c], 0) == 1)

            # ATU Q3_280Z (cols 599-603): Effectiveness of each used programme [1-7]
            # Co-Pay avg=2.5, PAP avg=3.6, QuickStart avg=1.4 (n=79 used at least one)
            q3280 = self._ac("Q3_280Z")
            eff_vals = [_tn(a[c], np.nan) for c in q3280 if c < len(a)]
            eff_vals = [v for v in eff_vals if not np.isnan(v) and v > 0]
            prog_effectiveness = np.mean(eff_vals) / 7.0 if eff_vals else 0.0  # normalised 0-1

            # ATU Q3_290Z (cols 604-611): the manufacturer support programme challenges cited [8 binary items]
            # Not integrated into workflow (n=22), Lack of awareness/training (n=15)
            # "Haven't used it" (col611 n=68) = NOT a barrier, just non-use → exclude from count
            q3290 = self._ac("Q3_290Z")
            # Only count actual friction challenges (cols 0-5), exclude "no challenges" and "haven't used"
            s1_challenges = sum(1 for c in q3290[:6] if _tn(a[c], 0) == 1)

            # Contradiction discount: fam ≥3 but 0 programmes known → 50% of familiarity sub-score
            s1_fam_adj = s1_fam * (0.5 if (s1_fam >= 3 and progs_known == 0) else 1.0)

            # ATU Q3_220Z: barriers cited (first 9 checkboxes = structured barriers)
            q3220a = self._ac("Q3_220Z")[:9]
            barriers = sum(1 for c in q3220a if _tn(a[c], 0) == 1)
            access_concern = max(0, 3 - access_va)

            # ── KCC inputs ──
            q100a = self._ac("Q1_00Z")
            ngs_rate = min(max(sum(_tn(a[c], 0) for c in q100a[1:3]) / 100.0, 0), 1)
            q170a = self._ac("Q1_70Z")[:12]
            markers_50 = sum(1 for c in q170a if _tn(a[c], 0) > 50)
            q400a = self._ac("Q4_00Z")[:8]
            bv = [_tn(a[c], np.nan) for c in q400a]
            bv = [v for v in bv if not np.isnan(v) and v > 0]
            belief_align = np.mean(bv) if bv else 4.5
            nccn_fam = _ms(a[129] if 129 < len(a) else np.nan, NCCN_MAP) or 3
            dse = 1 if "Apply it" in str(p[50] if 50 < len(p) else "") else 0
            # Q1_20Z: Testing barriers — cost/insurance (col88), NGS not actionable (col89),
            #          insufficient tissue (col93), patients referred without NGS (col95/100)
            # Testing barrier count (0-5 range, inverted for KCC)
            q120a = self._ac("Q1_20Z")
            testing_barriers = sum(1 for c in q120a[:8] if _tn(a[c], 0) == 1) if q120a else 0
            # Q1_60Z: NGS insurance denial in last 3 months (col105)
            # "Yes and appealed" = active (good, 0.8), "Yes not appealed" = passive (0.3),
            # "No but would appeal" = ready (0.9), "No would not appeal" = resigned (0.1)
            q160a = self._ac("Q1_60Z")
            ngsdeny_raw = str(a[q160a[0]] if q160a else "")
            if "appealed it" in ngsdeny_raw.lower() and "have not" not in ngsdeny_raw.lower():
                ngsdeny_score = 0.8   # Yes appealed — proactive
            elif "would try" in ngsdeny_raw.lower():
                ngsdeny_score = 0.9   # Would appeal if denied — proactive
            elif "have not tried" in ngsdeny_raw.lower() or "would not try" in ngsdeny_raw.lower():
                ngsdeny_score = 0.2   # Passive / resigned
            else:
                ngsdeny_score = 0.6   # Unknown / don't remember

            # ── CI inputs ──
            ip = [_tn(a[c], np.nan) for c in q3120a[40:59]]
            ip = [v for v in ip if not np.isnan(v) and v > 0]
            ivo_avg = np.mean(ip) if ip else 4.0
            vora_gap = round((np.mean(vp) if vp else 4.0) - ivo_avg, 2)
            cf = [q220a[4], q220a[6], q220a[7]] if len(q220a) > 7 else []
            comp_fam = round(np.mean([_tn(a[c], 1) for c in cf]) if cf else 2.5, 2)
            # Q3_300Z: patient inquiry frequency (col 612) — Very often=4, Occasionally=3, Rarely=2, Never=1
            # Q3_310Z: patient inquiry → prescribing impact (col 613) — Sig increases=4, Somewhat=3, No impact=2, Decreases=1
            PTINQ_MAP2 = {"Very often": 4, "Occasionally": 3, "Rarely": 2, "Never": 1}
            PTINQ_IMPACT = {"Significantly increases likelihood": 4, "Somewhat increases likelihood": 3,
                            "No impact": 2, "Not applicable": 2, "Decreases likelihood": 1}
            # Q3_300Z: How often patients ASK about the study drug (col 612) — pull demand
            pt_inq_freq   = PTINQ_MAP2.get(str(a[612] if 612 < len(a) else ""), 2)
            # Q3_310Z: How much does patient inquiry INFLUENCE prescribing decision (col 613)
            pt_inq_impact = PTINQ_IMPACT.get(str(a[613] if 613 < len(a) else ""), 2)
            # Q3_320Z: How often does patient preference CONFLICT with HCP recommendation (col 614)
            # Very frequently=4, Occasionally=3, Rarely=2, Never=1
            # Conflict = competitive pressure (patient pulling toward RT/observation vs the study drug)
            PTCONFLICT_MAP = {"Very frequently": 4, "Occasionally": 3, "Rarely": 2, "Never": 1}
            pt_conflict = PTCONFLICT_MAP.get(str(a[614] if 614 < len(a) else ""), 2)
            # patient_demand: high ask + high impact = strong pull; conflict inverted = competitive pressure
            patient_demand = (pt_inq_freq + pt_inq_impact) / 8.0  # normalised 0-1
            patient_conflict_pressure = (pt_conflict - 1) / 3.0   # normalised 0-1 (high = more competitive friction)

            # ── PE: Patient Enquiry (8th dimension) ──
            # Q3_300Z (col 612): How often patients ask about the study drug
            # Q3_310Z (col 613): How much patient inquiry influences prescribing decision
            # VA Patient support services shown → reinforces the manufacturer support programme conversation
            # This dimension captures the bidirectional patient pull signal
            pt_ask_score   = (pt_inq_freq - 1) / 3.0           # 0-1: Never→Very often
            pt_impact_score= (pt_inq_impact - 1) / 3.0         # 0-1: Decreases→Significantly increases
            # Q3_320Z conflict inverted: if patient often conflicts = lower PE
            pt_no_conflict = max(0, 1 - (pt_conflict - 1) / 3.0)
            # Patient support VA (Q1_100Z item) shown = rep opened the patient conversation
            pt_support_va  = int(_tn(p[81] if 81 < len(p) else 0, 0) == 1)  # Patient support services VA
            pe = (
                pt_ask_score    * 100 * 0.35   # Q3_300Z: patient ask frequency
                + pt_impact_score * 100 * 0.35  # Q3_310Z: patient impact on Rx
                + pt_no_conflict  * 100 * 0.20  # Q3_320Z inverted: no conflict = good
                + pt_support_va   * 100 * 0.10  # PET Q1_100Z: patient support VA shown
            )

            # ── VA flags ──
            va_used = {VA_LABELS.get(c, f"VA{c}"): int(_tn(p[c], 0) == 1) for c in range(79, 89) if c < len(p)}
            any_va = int(any(va_used.values()))

            # ── LTIP (top2 = 6,7) ──
            ltip_raw = _tn(p[169] if 169 < len(p) else 4, 4)
            ltip_top2 = int(ltip_raw >= 6)

            # ── the manufacturer support programme ──
            support_prog_aware = int(progs_known > 0 or s1_fam >= 3)

            # ── Specialty / setting ──
            specialty = str(a[48] if 48 < len(a) else "").strip()
            if not specialty or specialty == "nan":
                specialty = "Unknown"
            setting_raw = str(a[52] if 52 < len(a) else "").strip()
            if "Academic" in setting_raw or "Teaching" in setting_raw:
                setting = "Academic"
            elif "Community" in setting_raw or "Private" in setting_raw:
                setting = "Community"
            elif "VA" in setting_raw or "Network" in setting_raw:
                setting = "Integrated Network"
            else:
                setting = "Other"

            load_str = "High" if gr2_pl >= 15 else "Medium" if gr2_pl >= 6 else "Low"

            # ATU col 3: On Target / Off target / Co-locs (ZoomRx panelist list field)
            target_raw = str(a[3] if 3 < len(a) else "").strip()
            if "On Target" in target_raw:
                target_type = "On-List"
            elif "Co-loc" in target_raw:
                target_type = "Co-Loc"
            elif "Off" in target_raw:
                target_type = "Off-List"
            else:
                target_type = "Unknown"

            # ── ICI calculation ──
            # AC formula: unaided (60%) + aided familiarity ladder (40%)
            # Voice responses removed from ICI per Q3 FY26 update
            # pt_inq retained as minor signal via familiarity (Q3_300Z → used in CI instead)
            ac_raw = (
                unaided * 100 * 0.60                    # Q2_10Z unaided: fuzzy vora mention
                + (vora_fam - 1) / 4 * 100 * 0.40      # Q2_20Z the study drug familiarity 1–5 ladder
            )
            ac = min(ac_raw, 55) if unaided == 0 else ac_raw

            ibc = (
                min(curr_vora / gr2_pl, 1) * 100 * 0.35
                + future_intent / 10 * 100 * 0.25
                + (5.0 - 1) / 6 * 100 * 0.05
                + agreed * 100 * 0.2
                + peer_shared / 3 * 100 * 0.1
                + (like_inc - 1) / 6 * 100 * 0.05
            )

            mbc_raw = (
                msg_rec / 10 * 100 * 0.2
                + motiv_score / 5 * 100 * 0.3
                + (top_attr_perf - 1) / 6 * 100 * 0.3
                + attr_shift / 16 * 100 * 0.2
            )
            mbc = min(mbc_raw, 45) if attr_shift == 0 else mbc_raw

            rtc = (
                call_quality / 7 * 100       * 0.20   # PET Q3_70Z: call quality (5 attrs, 1-7)
                + prod_knowledge / 7 * 100   * 0.20   # PET Q3_60Z: product knowledge (7 attrs, 1-7)
                + ltip_norm * 100            * 0.15   # PET C3_35Z: LTIP post-visit [1-7, normalised]
                + min(ltip_delta / 3, 1)*100 * 0.10   # PET LTIP delta: post-visit minus pre-visit lift
                + rep_pref * 100             * 0.10   # ATU Q4_30Z: rep = preferred info source
                + agreed_q320 * 100          * 0.10   # PET Q3_20Z: agreed to prescribe next patient
                + int(overall_perception>=6)*100*0.08 # PET Q3_40BZ: overall perception shifted high
                + vora_rep_importance * 100  * 0.04   # PET Q3_55Z: HCP weights the study drug rep knowledge
                + asked_q310 * 100           * 0.02   # PET Q3_10Z: rep asked for the script
                + vf_intent_state * 100      * 0.01   # ATU Q2_20Z val=4: planning to use (intent bridge)
            )

            # ABR formula: the manufacturer support programme full funnel — aware → used → effective → no friction
            abr = (
                (s1_fam_adj - 1) / 4 * 100  * 0.15   # ATU Q3_260A: the manufacturer support programme familiarity (with contradiction discount)
                + progs_known / 5 * 100      * 0.15   # ATU Q3_260B: programmes known (breadth of awareness)
                + progs_used / 5 * 100       * 0.20   # ATU Q3_270Z: programmes actually used (conversion)
                + prog_effectiveness * 100   * 0.20   # ATU Q3_280Z: effectiveness rating of used programmes [1-7]
                + max(0, 100 - barriers*14.3)* 0.15   # ATU Q3_220Z: barrier count inverted
                + access_va / 3 * 100        * 0.10   # PET Q1_100Z: access VA shown in visit
                + max(0, 100 - s1_challenges/6*100)*0.05  # ATU Q3_290Z: the manufacturer support programme friction inverted
            )
            # Cap ABR at 35 if no access VA AND access not discussed in visit
            if access_va == 0 and access_concern >= 2:
                abr = min(abr, 35)

            kcc = (
                ngs_rate * 100                    * 0.20  # Q1_00Z NGS testing rate
                + markers_50 / 12 * 100           * 0.15  # Q1_70Z molecular marker breadth
                + (belief_align - 1) / 6 * 100   * 0.25  # Q4_00Z clinical belief alignment
                + (nccn_fam - 1) / 4 * 100        * 0.15  # Q2_00Z NCCN familiarity
                + dse * 100                        * 0.10  # PET C1_18Z DSE intent to act
                + max(0, 100 - testing_barriers/5*100) * 0.10  # Q1_20Z testing barriers inverted
                + ngsdeny_score * 100              * 0.05  # Q1_60Z NGS denial proactiveness
            )

            ci = (
                max(0, min((vora_gap + 1.5) / 5 * 100, 100)) * 0.30   # Vora vs competitor perf gap (Q3_120)
                + max(0, 100 - (comp_fam - 1) / 4 * 100) * 0.25        # Competitor familiarity inverted (Q2_20Z)
                + patient_demand * 100                     * 0.30        # Q3_300Z freq + Q3_310Z impact (patient pull)
                + max(0, 100 - patient_conflict_pressure * 100) * 0.15  # Q3_320Z conflict inverted (lower conflict = stronger CI)
            )

            ici = (
                ac * 0.13 + ibc * 0.23 + mbc * 0.19
                + rtc * 0.12 + abr * 0.14 + kcc * 0.08
                + ci * 0.05 + pe * 0.06
            )

            cluster_secondary = None  # default
            # ── Sequential Cluster Assignment (Option C — resolve blockers in order) ──
            # Q1: Is patient load too low to support any product conversation?
            # Low gr2 PL = practice mismatch. Low familiarity = pure awareness gap.
            if gr2_pl <= 2 or vora_fam < 3:
                cluster = 1  # Patient ID Priority
                cluster_secondary = None
            # Q2: Is access blocking an otherwise willing prescriber?
            elif ((ibc >= 45 or agreed == 1) and abr < 40) or (access_va == 0 and barriers > 1):
                cluster = 2  # Intent-Led, Access-Pending
                cluster_secondary = 3 if mbc < 40 else None
            # Q3: Is there a clinical misperception or evidence gap?
            elif mbc < 40 or (top_attr_perf < 4.5 and attr_shift == 0):
                cluster = 3  # Evidence Gap
                cluster_secondary = 2 if abr < 40 else None
            # Q4: Is conviction present but built on fragile uniqueness framing?
            elif ibc >= 50 and comp_fam >= 3.5 and ci < 50:
                cluster = 4  # Narrative-Building Opportunity
                cluster_secondary = None
            # Q5: All gates cleared — conviction-led
            else:
                cluster = 5  # Conviction-Led Prescriber
                cluster_secondary = None

            # Q3_110Z importance ratings (adjuvant column group A1)
            q3110a = self._ac("Q3_110Z")
            attr_importance = {}
            for idx, label in enumerate(ATTR_LABELS):
                c_idx = q3110a[idx] if idx < len(q3110a) else None
                attr_importance[f"imp_{label}"] = _tn(a[c_idx], np.nan) if c_idx else np.nan

            # Q3_120Z the study drug performance
            vora_perf = {}
            for idx, label in enumerate(ATTR_LABELS[:19]):
                c_idx = q3120a[20 + idx] if (20 + idx) < len(q3120a) else None
                vora_perf[f"perf_{label}"] = _tn(a[c_idx], np.nan) if c_idx else np.nan

            # Q3_50Z patient counts
            q350a = self._ac("Q3_50Z")
            total_gr2 = sum(_tn(a[c], 0) for c in q350a[:6]) if q350a else gr2_pl

            rec = {
                "uid": uid,
                "specialty": specialty,
                "target_type": target_type,
                "setting": setting,
                "load": load_str,
                "gr2_pl": gr2_pl,
                "unaided": unaided,
                "vora_fam": vora_fam,
                "pt_inq": pt_inq,
                "msg_rec": msg_rec,
                "curr_vora": curr_vora,
                "curr_vora_share": round(curr_vora / max(gr2_pl, 1) * 100, 1),
                "future_intent": round(future_intent, 1),
                "agreed": agreed,
                "peer_shared": peer_shared,
                "like_inc": round(like_inc, 1),
                "ltip_top2": ltip_top2,
                "top_attr_perf": round(top_attr_perf, 2),
                "attr_shift": attr_shift,
                "motiv_score": round(motiv_score, 2),
                "any_va": any_va,
                "access_va": access_va,
                "call_quality": round(call_quality, 2),
                "prod_knowledge": round(prod_knowledge, 2),
                "asked_q310": asked_q310,
                "agreed_q320": agreed_q320,
                "prev_rx": prev_rx,
                "ltip_raw": round(ltip_raw, 1),
                "ltip_norm": round(ltip_norm, 2),
                "ltip_delta": round(ltip_delta, 1),
                "vora_rep_importance": round(vora_rep_importance, 2),
                "progs_used": progs_used,
                "prog_effectiveness": round(prog_effectiveness, 2),
                "s1_challenges": s1_challenges,
                "patient_conflict_pressure": round(patient_conflict_pressure, 2),
                "overall_perception": round(overall_perception, 1),
                "attr_shift": attr_shift,
                "topic_gap_penalty": topic_gap_penalty,
                "testing_barriers": testing_barriers,
                "ngsdeny_score": round(ngsdeny_score, 2),
                "patient_demand": round(patient_demand, 2),
                "vf_intent": vf_intent,
                "imp_adj": round(imp_adj, 2),
                "imp_fl": round(imp_fl, 2),
                "prod_knowledge": round(prod_knowledge, 2),
                "rep_pref": rep_pref,
                "progs_known": progs_known,
                "s1_fam": s1_fam,
                "support_prog_aware": support_prog_aware,
                "barriers": barriers,
                "ngs_rate": round(ngs_rate, 2),
                "markers_50": markers_50,
                "belief_align": round(belief_align, 2),
                "nccn_fam": nccn_fam,
                "dse": dse,
                "vora_gap": vora_gap,
                "comp_fam": comp_fam,
                "AC": round(ac, 1),
                "PE": round(pe, 1),
                "IBC": round(ibc, 1),
                "MBC": round(mbc, 1),
                "RTC": round(rtc, 1),
                "ABR": round(abr, 1),
                "KCC": round(kcc, 1),
                "CI": round(ci, 1),
                "ICI": round(ici, 1),
                "cluster": cluster,
                "cluster_secondary": cluster_secondary if cluster_secondary is not None else None,
                "cluster_name": {
                    1: "Patient ID Priority",
                    2: "Intent-Led, Access-Pending",
                    3: "Evidence Gap",
                    4: "Narrative-Building Opportunity",
                    5: "Conviction-Led Prescriber",
                }[cluster],
                "total_gr2_q350": total_gr2,
            }
            rec.update(va_used)
            rec.update(attr_importance)
            rec.update(vora_perf)
            records.append(rec)

        self.hcps_df = pd.DataFrame(records)

    def _build_xtab_dataset(self):
        """Merge ATU + PET on uid for cross-tab analysis."""
        if self.hcps_df is None:
            return
        self.xtab_df = self.hcps_df.copy()

    # ── Stats ─────────────────────────────────────────────────────────────────
    def stats(self):
        atu_n = self.atu["uid"].nunique() if self.atu is not None else 0
        pet_n = self.pet["uid"].nunique() if self.pet is not None else 0
        ov_n = len(self.hcps_df) if self.hcps_df is not None else 0
        return {
            "atu_n": atu_n,
            "pet_n": pet_n,
            "overlap_n": ov_n,
            "atu_waves": "Q1+Q2",
            "pet_waves": "Q4+Q1+Q2",
        }
