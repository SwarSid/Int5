"""Q3 FY26 ATU new questions — pre-coded data from uploaded Excel."""

UNAIDED = [
    ("IDH Inhibitors",         73, 76),("the study drug",                65, 68),
    ("Temozolomide (Temodar)", 62, 65),("PCV regimen",             38, 40),
    ("Tibsovo (Ivosidenib)",   26, 27),("Radiation",               25, 26),
    ("Bevacizumab",            11, 11),("CCNU (lomustine)",        11, 11),
    ("Safusidenib",             3,  3),
]

Q3_70A = {
    "q": "If surgeon reports GTR but post-op MRI shows minimal residual enhancement — does patient qualify for THE STUDY DRUG?",
    "n": 55,
    "cats": [("Yes — qualifies",37,67),("Conditional",15,27),("No — contraindicates",3,5)]
}
Q3_70B = {
    "q": "What evidence needed to move GTR patient from Active Observation to THE STUDY DRUG?",
    "n": 79,
    "cats": [("PFS data needed",22,28),("OS data needed",16,20),("Already prescribing — no evidence needed",15,19),
             ("Radiographic progression",15,19),("Neuro symptoms",13,16),("High-risk molecular features",10,13),("Seizures",6,8)]
}
Q3_70C = {
    "q": "GTR patient on Active Observation — what triggers THE STUDY DRUG initiation?",
    "n": 78,
    "cats": [("Any MRI change",33,42),("Neuro symptoms",29,37),("≤10% volume increase",28,36),
             ("Seizures",12,15),("No observation — treating all",7,9),("25%+ / RANO criteria",5,6)]
}
Q3_125 = {
    "q": "How does evidence of tumour volume reduction influence treatment decisions?",
    "n": 78,
    "cats": [("Efficacy proxy",28,36),("Prescription trigger",15,19),("Treatment continuation signal",9,12),
             ("Skeptics — PFS/OS primary",11,14),("QoL / symptom bridge",8,10),("Indifferent",7,9)]
}
Q3_162 = {
    "q": "Do you reserve THE STUDY DRUG only for 'low-regret' scenarios or use as primary adjuvant?",
    "n": 77,
    "cats": [("Broad / universal adopters",40,52),("Young professional champions",18,23),
             ("Conditional / criteria-driven",10,13),("Evolving / data-driven",4,5),("Hesitant / not yet ready",4,5)]
}
Q3_335 = {
    "q": "Patients prefer RT as finite course vs indefinite THE STUDY DRUG — how do you counter?",
    "n": 78,
    "cats": [("Highlight RT neurocognitive toxicity",32,41),("Cite PFS/OS efficacy data",24,31),
             ("THE STUDY DRUG preserves QoL",16,21),("Don't counter / patient preference",13,17)]
}
Q3_202 = {
    "q": "10mg BID due to hepatotoxicity — re-escalate to 40mg? Discontinue vs switch to TIBSOVO?",
    "n": 65,
    "cats": [("No protocol / case-by-case",25,38),("Re-escalate once LFTs normalise",16,25),
             ("Permanently discontinue Gr 3/4",15,23),("Follow FDA label / protocol",10,15),
             ("Maintain reduced dose",8,12),("Switch to TIBSOVO",8,12)]
}
