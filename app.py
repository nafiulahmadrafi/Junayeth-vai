"""
============================================================
POLITICAL MEDIA INTELLIGENCE SYSTEM v2.0
Bangladesh + India + International Media Monitor
============================================================
Deployed on: Hugging Face Spaces (Streamlit SDK)
Engine: scraper_engine.py (Tier1/2/3/GNews)
============================================================
"""

import os
import sys
import subprocess
import streamlit as st

# ── HF Spaces: install Playwright browser on cold start ──
@st.cache_resource(show_spinner=False)
def _install_playwright():
    try:
        result = subprocess.run(
            ["playwright", "install", "chromium", "--with-deps"],
            capture_output=True, text=True, timeout=180
        )
        return result.returncode == 0
    except Exception:
        try:
            os.system("playwright install chromium --with-deps")
        except Exception:
            pass
        return False

_pw_ok = _install_playwright()

# ── Page config (MUST be first Streamlit call) ───────────
st.set_page_config(
    page_title="🧠 Political Media Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import re
import time
from datetime import datetime
from collections import Counter, defaultdict

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False

try:
    from scraper_engine import run_scraper, SITE_SELECTORS
except ImportError as e:
    st.error(f"❌ scraper_engine.py ইমপোর্ট করা যায়নি: {e}")
    st.stop()


# ============================================================
# MEDIA DIRECTORY
# ============================================================

MEDIA_DIRECTORY = {
    "print_newspapers_bangla": [
        {"name": "Daily Janakantha",   "website": "dailyjanakantha.com",  "key_person": "Enayetur Rahim"},
        {"name": "Jai Jai Din",        "website": "jjdin.com",            "key_person": "Sayeed Hossain Chowdhury"},
        {"name": "Bhorer Kagoj",       "website": "bhorerkagoj.com",      "key_person": "Shyamal Dutta"},
        {"name": "Daily Inqilab",      "website": "dailyinqilab.com",     "key_person": "A.M.M. Bahauddin"},
        {"name": "Sangbad",            "website": "sangbad.net.bd",       "key_person": "Altamash Kabir"},
        {"name": "Daily Dinkal",       "website": "daily-dinkal.com",     "key_person": "Dr. Rezuan Hossain"},
        {"name": "Kalbela",            "website": "kalbela.com",          "key_person": "Mia Nuruddin Apu"},
        {"name": "Desh Rupantor",      "website": "deshrupantor.com",     "key_person": "Mustafa Mamun"},
    ],
    "print_newspapers_english": [
        {"name": "Daily Star",         "website": "thedailystar.net",     "key_person": "Mahfuz Anam"},
        {"name": "Daily Observer",     "website": "observerbd.com",       "key_person": "Iqbal Sobhan Chowdhury"},
        {"name": "Business Standard",  "website": "tbsnews.net",          "key_person": "Inam Ahmed"},
        {"name": "Dhaka Tribune",      "website": "dhakatribune.com",     "key_person": "Zafar Sobhan"},
    ],
    "digital_news_portals": [
        {"name": "BD News 24",         "website": "bangla.bdnews24.com",  "key_person": "Toufique Imrose Khalidi"},
        {"name": "Jago News 24",       "website": "jagonews24.com",       "key_person": "Mohiuddin Sarker"},
        {"name": "Bangla Tribune",     "website": "banglatribune.com",    "key_person": "Zulfiqer Russell"},
        {"name": "Amar Desh",          "website": "amar-desh24.com",      "key_person": "Mahmudur Rahman"},
    ],
    "television_channels": [
        {"name": "Somoy News",         "website": "somoynews.tv",         "key_person": "Ahmed Jobaer"},
        {"name": "Jamuna TV",          "website": "jamuna.tv",            "key_person": "Fahim Ahmed"},
        {"name": "Channel i",          "website": "channelionline.com",   "key_person": "Shykh Seraj"},
        {"name": "Ekattor TV",         "website": "ekattor.tv",           "key_person": "Mozammel Babu"},
    ],
    "regional_portals": [
        {"name": "Coxsbazar News",     "website": "coxsbazarnews.com",    "key_person": "Prof. Akthar Chowdhury"},
        {"name": "Daily Coxsbazar",    "website": "dailycoxsbazar.com",   "key_person": "Mohammad Mujibur Rahman"},
        {"name": "Uttorpurbo",         "website": "uttorpurbo.com",       "key_person": "Safwan Chowdhury"},
        {"name": "Ajker Jamalpur",     "website": "ajkerjamalpur.com",    "key_person": "Azizur Rahman"},
        {"name": "Amader Barisal",     "website": "amaderbarisal.com",    "key_person": "Saidur Rahman"},
        {"name": "Surma Times",        "website": "surmatimes.com",       "key_person": "Editorial Team"},
        {"name": "Chandpur Times",     "website": "chandpurtimes.com",    "key_person": "Kazi Md. Ibrahim Juel"},
        {"name": "Mukto Khobor 24",    "website": "muktokhobor24.com",    "key_person": "M.A. Malek"},
        {"name": "Bogra Sangbad",      "website": "bograsangbad.com",     "key_person": "Kamal Ahmed"},
        {"name": "Rajshahir Somoy",    "website": "rajshahirsomoy.com",   "key_person": "Humayun Kabir"},
        {"name": "Lakshmipur 24",      "website": "lakshmipur24.com",     "key_person": "Sana Ullah Sanu"},
        {"name": "Prothom Feni",       "website": "prothom-feni.com",     "key_person": "Ariful Amin Majumder"},
        {"name": "Gramer Kagoj",       "website": "gamerkagoj.com",       "key_person": "Mobinul Islam Mobin"},
    ],
    "indian_bengali_media": [
        {"name": "Anandabazar Patrika","website": "anandabazar.com",       "key_person": "Aveek Sarkar"},
        {"name": "Sangbad Pratidin",   "website": "sangbadpratidin.in",   "key_person": "Srinjoy Bose"},
        {"name": "ABP Ananda",         "website": "bengali.abplive.com",  "key_person": "Suman De"},
        {"name": "24 Ghanta",          "website": "zee24ghanta.com",      "key_person": "Anirban Chowdhury"},
        {"name": "Ei Samay",           "website": "eisamay.com",          "key_person": "Rupankar Sarkar"},
        {"name": "Bartaman Patrika",   "website": "bartamanpatrika.com",  "key_person": "Subha Dutta"},
    ],
    "international_news_agencies": [
        {"name": "BBC News",           "website": "bbc.com",              "key_person": "Tim Davie"},
        {"name": "Al Jazeera",         "website": "aljazeera.com",        "key_person": "Mostefa Souag"},
        {"name": "AFP",                "website": "afp.com",              "key_person": "Fabrice Fries"},
        {"name": "The Guardian",       "website": "theguardian.com",      "key_person": "Katharine Viner"},
        {"name": "CNN",                "website": "edition.cnn.com",      "key_person": "Mark Thompson"},
        {"name": "NY Times",           "website": "nytimes.com",          "key_person": "A.G. Sulzberger"},
        {"name": "Hindustan Times",    "website": "hindustantimes.com",   "key_person": "Shobhana Bhartia"},
        {"name": "ABC News",           "website": "abcnews.go.com",       "key_person": "David Muir"},
        {"name": "Yahoo News",         "website": "news.yahoo.com",       "key_person": "Editorial Team"},
    ],
}

ALL_MEDIA = []
for _cat, _outlets in MEDIA_DIRECTORY.items():
    for _o in _outlets:
        _o["category"] = _cat
        ALL_MEDIA.append(_o)


# ============================================================
# INTELLIGENCE KEYWORDS
# ============================================================

PARTY_KEYWORDS = {
    "Awami League":       ["awami", "আওয়ামী", "sheikh hasina", "শেখ হাসিনা", "নৌকা", "হাসিনা", "মুজিব", "bangabandhu", "বঙ্গবন্ধু", "১৪ দল", "fourteen party"],
    "BNP":                ["bnp", "বিএনপি", "khaleda", "খালেদা", "tarique", "তারেক", "জিয়া", "zia", "২০ দল", "তত্ত্বাবধায়ক", "caretaker", "নির্দলীয়"],
    "Jamaat-e-Islami":    ["jamaat", "জামায়াত", "ইসলামী", "islami", "শিবির", "নিজামী", "nizami", "রাজাকার"],
    "Jatiya Party":       ["jatiya party", "জাতীয় পার্টি", "ershad", "এরশাদ", "রওশন", "rowshan", "লাঙল", "জাপা"],
    "Interim Government": ["interim", "অন্তর্বর্তী", "yunus", "ইউনুস", "chief adviser", "প্রধান উপদেষ্টা", "সংস্কার", "reform"],
}

THREAT_KEYWORDS = [
    "সহিংসতা", "violence", "হামলা", "attack", "গ্রেপ্তার", "arrest",
    "নিষিদ্ধ", "ban", "ষড়যন্ত্র", "conspiracy", "বিদেশী হস্তক্ষেপ",
    "foreign interference", "অস্থিরতা", "instability", "অবরোধ", "blockade",
    "হরতাল", "hartal", "strike", "ধর্মঘট", "সংঘাত", "conflict",
    "উত্তেজনা", "tension", "সংকট", "crisis", "আন্দোলন", "movement",
    "নিহত", "killed", "আহত", "injured", "সংঘর্ষ", "clash", "বিস্ফোরণ", "explosion",
]

NARRATIVE_THEMES = {
    "Election":       ["নির্বাচন", "election", "ভোট", "vote", "ballot", "প্রার্থী", "candidate", "ইভিএম", "evm"],
    "Economy":        ["অর্থনীতি", "economy", "মূল্যস্ফীতি", "inflation", "দ্রব্যমূল্য", "price", "taka", "টাকা", "রিজার্ভ", "reserve"],
    "Security":       ["নিরাপত্তা", "security", "পুলিশ", "police", "র‌্যাব", "rab", "সেনা", "army", "বিজিবি", "bgb"],
    "Corruption":     ["দুর্নীতি", "corruption", "লুটপাট", "looting", "অর্থ আত্মসাৎ", "embezzlement", "দুদক", "acc"],
    "Foreign Policy": ["ভারত", "india", "চীন", "china", "আমেরিকা", "america", "usa", "রোহিঙ্গা", "rohingya", "মিয়ানমার", "myanmar"],
    "Justice":        ["বিচার", "justice", "মামলা", "case", "আদালত", "court", "ট্রাইব্যুনাল", "tribunal", "রায়", "verdict"],
    "Protest":        ["আন্দোলন", "protest", "বিক্ষোভ", "demonstration", "ধর্মঘট", "সমাবেশ", "rally", "মিছিল"],
    "Diplomacy":      ["কূটনীতি", "diplomacy", "দূতাবাস", "embassy", "সম্পর্ক", "relation", "চুক্তি", "agreement", "সফর", "visit"],
}

PARTY_COLORS = {
    "Awami League":       "#2563eb",
    "BNP":                "#16a34a",
    "Jamaat-e-Islami":    "#dc2626",
    "Jatiya Party":       "#d97706",
    "Interim Government": "#7c3aed",
}

CAT_LABELS = {
    "print_newspapers_bangla":     "📰 Bangla Newspapers (8)",
    "print_newspapers_english":    "📰 English Newspapers (4)",
    "digital_news_portals":        "🌐 Digital Portals (4)",
    "television_channels":         "📺 TV Channels (4)",
    "regional_portals":            "📍 Regional BD (13)",
    "indian_bengali_media":        "🇮🇳 Indian Bengali (6)",
    "international_news_agencies": "🌍 International (9)",
}

TIER_CSS = {
    "Tier1 (aiohttp)":    ("tier1", "⚡"),
    "Tier2 (Playwright)": ("tier2", "🎭"),
    "Tier3 (Stealth)":    ("tier3", "🥷"),
    "Tier4 (GNews RSS)":  ("tier4", "📡"),
    "Failed":             ("tierfail", "❌"),
}


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .main-header {
    font-size: 2.3rem; font-weight: 800;
    background: linear-gradient(135deg, #1e3a8a 0%, #7c3aed 60%, #db2777 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center; margin-bottom: 0.2rem; letter-spacing: -0.5px;
  }
  .sub-header { text-align: center; color: #6b7280; margin-bottom: 1.5rem; font-size: 0.9rem; }

  .kpi-card {
    background: white; border: 1px solid #e5e7eb;
    border-radius: 12px; padding: 16px 20px; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
  }
  .kpi-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
  .kpi-label { font-size: 0.78rem; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
  .kpi-value { font-size: 2rem; font-weight: 800; color: #111827; line-height: 1.1; }
  .kpi-sub   { font-size: 0.75rem; color: #9ca3af; margin-top: 2px; }

  .tier-badge {
    font-size: 0.72rem; padding: 2px 9px; border-radius: 10px;
    font-weight: 700; display: inline-block; letter-spacing: 0.3px;
  }
  .tier1    { background: #d1fae5; color: #065f46; }
  .tier2    { background: #dbeafe; color: #1e40af; }
  .tier3    { background: #ede9fe; color: #5b21b6; }
  .tier4    { background: #fef3c7; color: #92400e; }
  .tierfail { background: #fee2e2; color: #991b1b; }

  .narrative-box {
    border-left: 4px solid #7c3aed; padding: 12px 14px;
    background: #f5f3ff; border-radius: 0 8px 8px 0; margin: 7px 0;
    transition: background 0.2s;
  }
  .narrative-box:hover { background: #ede9fe; }

  .threat-card {
    border: 1px solid #fca5a5; background: #fff1f2;
    border-radius: 10px; padding: 14px 16px; margin: 8px 0;
    border-left: 5px solid #dc2626;
  }

  .predict-card {
    border: 1px solid #e5e7eb; padding: 16px 18px;
    border-radius: 12px; margin: 8px 0;
    background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }

  .outlet-card {
    border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 12px 14px; margin: 6px 0;
    background: white; transition: box-shadow 0.15s;
  }
  .outlet-card:hover { box-shadow: 0 3px 8px rgba(0,0,0,0.08); }

  .alert-box {
    border-radius: 10px; padding: 14px 18px; margin: 10px 0;
    border-left: 5px solid;
  }
  .alert-info    { background: #eff6ff; border-color: #3b82f6; color: #1e40af; }
  .alert-warning { background: #fffbeb; border-color: #f59e0b; color: #92400e; }
  .alert-danger  { background: #fff1f2; border-color: #dc2626; color: #991b1b; }


  .wp-card  { border:1px solid #d1fae5; background:#f0fdf4; border-radius:12px; padding:14px; margin:6px 0; border-left:5px solid #16a34a; }
  .wp-error { border:1px solid #fca5a5; background:#fff1f2; border-radius:12px; padding:12px; margin:6px 0; border-left:5px solid #dc2626; }
  /* Hide Streamlit branding */
  #MainMenu, footer { visibility: hidden; }
  .stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# INTELLIGENCE ANALYSIS ENGINE
# ============================================================

def _sentiment(text: str) -> tuple:
    if HAS_TEXTBLOB:
        try:
            pol = TextBlob(text).sentiment.polarity
        except Exception:
            pol = 0.0
    else:
        pol = 0.0
    label = "Positive" if pol > 0.1 else ("Negative" if pol < -0.1 else "Neutral")
    return label, round(pol, 3)


def analyze_text(text: str) -> dict:
    text_lower = text.lower()
    label, polarity = _sentiment(text)

    party_scores = {
        p: sum(1 for kw in kws if kw in text_lower)
        for p, kws in PARTY_KEYWORDS.items()
    }
    party_scores = {p: s for p, s in party_scores.items() if s > 0}

    threat_hits = [kw for kw in THREAT_KEYWORDS if kw in text_lower]
    threat_score = min(len(threat_hits) * 18, 100)
    threat_level = "HIGH" if threat_score >= 60 else ("MEDIUM" if threat_score >= 30 else "LOW")

    theme_scores = {
        t: sum(1 for kw in kws if kw in text_lower)
        for t, kws in NARRATIVE_THEMES.items()
    }
    theme_scores = {t: s for t, s in theme_scores.items() if s > 0}

    return {
        "sentiment":     label,
        "polarity":      polarity,
        "party_scores":  party_scores,
        "dominant_party": max(party_scores, key=party_scores.get) if party_scores else None,
        "threat_score":  threat_score,
        "threat_level":  threat_level,
        "threat_hits":   threat_hits,
        "dominant_theme": max(theme_scores, key=theme_scores.get) if theme_scores else "General",
        "theme_scores":  theme_scores,
    }


def analyze_outlet_results(raw: dict) -> dict:
    headlines = raw.get("headlines", [])
    if not headlines:
        return {**raw,
                "avg_polarity": 0, "sentiment_dist": {}, "party_bias": {},
                "dominant_party": None, "threat_score": 0, "threat_level": "LOW",
                "dominant_theme": "N/A", "narrative_themes": {}, "analyzed_headlines": []}

    analyzed = [{"text": h, **analyze_text(h)} for h in headlines]
    polarities = [a["polarity"] for a in analyzed]
    avg_pol = round(sum(polarities) / len(polarities), 3) if polarities else 0

    sentiment_dist = Counter(a["sentiment"] for a in analyzed)

    party_agg = defaultdict(int)
    theme_agg = defaultdict(int)
    for a in analyzed:
        for p, s in a["party_scores"].items():   party_agg[p] += s
        for t, s in a["theme_scores"].items():   theme_agg[t] += s

    avg_threat = sum(a["threat_score"] for a in analyzed) / len(analyzed) if analyzed else 0
    threat_level = "HIGH" if avg_threat >= 50 else ("MEDIUM" if avg_threat >= 25 else "LOW")

    return {
        **raw,
        "avg_polarity":       avg_pol,
        "sentiment_dist":     dict(sentiment_dist),
        "party_bias":         dict(party_agg),
        "dominant_party":     max(party_agg, key=party_agg.get) if party_agg else None,
        "threat_score":       round(avg_threat),
        "threat_level":       threat_level,
        "dominant_theme":     max(theme_agg, key=theme_agg.get) if theme_agg else "General",
        "narrative_themes":   dict(theme_agg),
        "analyzed_headlines": analyzed,
    }


# ============================================================
# NARRATIVE ENGINE
# ============================================================

def detect_narratives(results: list) -> list:
    all_hl = [{"text": h, "source": r["name"]}
              for r in results for h in r.get("headlines", [])]

    bigram_freq: Counter  = Counter()
    bigram_src:  defaultdict = defaultdict(set)

    for item in all_hl:
        words = re.findall(r'[\u0980-\u09FF\w]{3,}', item["text"].lower())
        for i in range(len(words) - 1):
            bg = f"{words[i]} {words[i+1]}"
            bigram_freq[bg] += 1
            bigram_src[bg].add(item["source"])

    narratives = []
    for bg, count in bigram_freq.most_common(20):
        if count < 2:
            continue
        sources = list(bigram_src[bg])
        theme = next(
            (t for t, kws in NARRATIVE_THEMES.items() if any(kw in bg for kw in kws)),
            "General"
        )
        narratives.append({
            "phrase":      bg,
            "count":       count,
            "sources":     sources,
            "source_count": len(sources),
            "theme":       theme,
            "coordinated": len(sources) >= 3,
        })

    return sorted(narratives, key=lambda x: (x["source_count"], x["count"]), reverse=True)[:12]


# ============================================================
# THREAT ENGINE
# ============================================================

def detect_threats(results: list) -> list:
    threats = []

    high = [r for r in results if r.get("threat_level") == "HIGH"]
    if len(high) >= 3:
        threats.append({
            "type":    "Coordinated Threat Coverage",
            "level":   "HIGH",
            "detail":  f"{len(high)} outlets simultaneously publishing high-threat content",
            "outlets": [r["name"] for r in high],
        })

    party_neg: defaultdict = defaultdict(list)
    for r in results:
        if r.get("avg_polarity", 0) < -0.15 and r.get("dominant_party"):
            party_neg[r["dominant_party"]].append(r["name"])
    for party, outlets in party_neg.items():
        if len(outlets) >= 3:
            threats.append({
                "type":    "Coordinated Negative Campaign",
                "level":   "HIGH",
                "detail":  f"{len(outlets)} outlets with sustained negative framing targeting {party}",
                "outlets": outlets,
            })

    # Surge detection: theme suddenly dominant
    theme_counter: Counter = Counter()
    for r in results:
        for t, c in r.get("narrative_themes", {}).items():
            theme_counter[t] += c
    for theme, cnt in theme_counter.most_common(3):
        if cnt >= 15:
            threats.append({
                "type":    f"Narrative Surge — {theme}",
                "level":   "MEDIUM",
                "detail":  f"'{theme}' theme appears {cnt} times across media — potential agenda push",
                "outlets": [],
            })

    return threats


# ============================================================
# PREDICTION ENGINE
# ============================================================

PREDICTIONS = {
    "Election":       "নির্বাচনী উত্তেজনা আগামী ২–৪ সপ্তাহে বাড়তে পারে। দলীয় সমাবেশ ও পাল্টাপাল্টি বিবৃতি আসার সম্ভাবনা।",
    "Economy":        "দ্রব্যমূল্য ও অর্থনৈতিক চাপ রাজনৈতিক হাতিয়ার হিসেবে ব্যবহার হওয়ার আশঙ্কা।",
    "Security":       "আইন-শৃঙ্খলা পরিস্থিতি বিরোধীদের আন্দোলনের ট্রিগার হতে পারে।",
    "Corruption":     "দুর্নীতির ন্যারেটিভ আসন্ন রাজনৈতিক বিতর্কে প্রাধান্য পাবে।",
    "Foreign Policy": "বৈদেশিক সম্পর্কের ইস্যু অভ্যন্তরীণ রাজনীতিতে প্রভাব ফেলতে পারে।",
    "Justice":        "বিচারিক উন্নয়ন পরবর্তী রাজনৈতিক সংবাদ চক্রে আধিপত্য বিস্তার করবে।",
    "Protest":        "বিক্ষোভ ও আন্দোলনের মাত্রা বৃদ্ধি পাওয়ার সম্ভাবনা আছে।",
    "Diplomacy":      "কূটনৈতিক গতিবিধি অভ্যন্তরীণ রাজনীতিতে নতুন মাত্রা যোগ করতে পারে।",
}

def predict_issues(results: list) -> list:
    theme_counts: Counter = Counter()
    for r in results:
        for t, c in r.get("narrative_themes", {}).items():
            theme_counts[t] += c

    return [
        {
            "theme":      t,
            "intensity":  min(c * 6, 100),
            "prediction": PREDICTIONS.get(t, f"{t} ইস্যু রাজনৈতিক আলোচনায় আসতে পারে।"),
            "count":      c,
        }
        for t, c in theme_counts.most_common(8)
    ]


# ============================================================
# HELPER WIDGETS
# ============================================================

def _tier_badge(tier: str) -> str:
    css, icon = TIER_CSS.get(tier, ("tierfail", "❓"))
    return f'<span class="tier-badge {css}">{icon} {tier}</span>'

def _kpi(label: str, value, sub: str = "") -> str:
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""

def _threat_icon(level: str) -> str:
    return {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(level, "⚪")


# ============================================================
# MAIN APP
# ============================================================


# ============================================================
# WORDPRESS API ENGINE
# ============================================================

def wp_test_connection(url, user, password):
    try:
        r = requests.get(url.rstrip("/") + "/wp-json/wp/v2/users/me",
                         auth=(user, password), timeout=10)
        if r.status_code == 200:
            d = r.json()
            return {"ok": True, "name": d.get("name","?"), "roles": d.get("roles",[])}
        return {"ok": False, "error": "HTTP " + str(r.status_code)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def wp_get_categories(url, user, password):
    try:
        r = requests.get(url.rstrip("/")+"/wp-json/wp/v2/categories?per_page=50",
                         auth=(user, password), timeout=10)
        if r.status_code == 200:
            return [{"id": c["id"], "name": c["name"]} for c in r.json()]
    except Exception:
        pass
    return []


def wp_post_article(url, user, password, title, content,
                    status="draft", category_ids=None, tags=None):
    endpoint = url.rstrip("/") + "/wp-json/wp/v2/posts"
    payload  = {"title": title, "content": content, "status": status, "format": "standard"}
    if category_ids:
        payload["categories"] = category_ids
    if tags:
        tag_ids = []
        for tag in tags[:5]:
            try:
                te = url.rstrip("/")+"/wp-json/wp/v2/tags?search="+str(tag)
                tr = requests.get(te, auth=(user, password), timeout=8)
                existing = tr.json() if tr.status_code == 200 else []
                if existing:
                    tag_ids.append(existing[0]["id"])
                else:
                    tc_r = requests.post(url.rstrip("/")+"/wp-json/wp/v2/tags",
                                         json={"name": tag}, auth=(user, password), timeout=8)
                    if tc_r.status_code in (200, 201):
                        tag_ids.append(tc_r.json()["id"])
            except Exception:
                continue
        if tag_ids:
            payload["tags"] = tag_ids
    try:
        r = requests.post(endpoint, json=payload, auth=(user, password), timeout=15)
        if r.status_code in (200, 201):
            d = r.json()
            return {"ok": True, "id": d.get("id"), "link": d.get("link", "")}
        return {"ok": False, "error": "HTTP " + str(r.status_code) + ": " + r.text[:120]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def build_wp_summary_post(results, scan_time):
    successful  = [r for r in results if r.get("status") == "success"]
    total_hl    = sum(r.get("count", 0) for r in successful)
    high_threat = sum(1 for r in successful if r.get("threat_level") == "HIGH")
    date_str    = datetime.now().strftime("%d %B %Y")
    tc = Counter()
    for r in successful:
        for t, c in r.get("narrative_themes", {}).items():
            tc[t] += c
    top_themes = [t for t, _ in tc.most_common(3)]
    pa = Counter()
    for r in successful:
        for p, s in r.get("party_bias", {}).items():
            pa[p] += s
    top_party = pa.most_common(1)[0][0] if pa else "N/A"
    title = "রাজনৈতিক মিডিয়া বিশ্লেষণ — " + date_str
    rows_html = ""
    for r in successful[:20]:
        threat_c = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#16a34a"}.get(
            r.get("threat_level", "LOW"), "#16a34a")
        party = r.get("dominant_party") or "—"
        pc    = PARTY_COLORS.get(party, "#6b7280")
        items = "".join(
            "<li style=\'margin-bottom:4px;font-size:0.92em;\'>" + hl + "</li>"
            for hl in r.get("headlines", [])[:8]
        )
        extra = len(r.get("headlines", [])) - 8
        if extra > 0:
            items += "<li style=\'color:#9ca3af;\'>... আরো " + str(extra) + "টি</li>"
        rows_html += (
            "<div style=\'border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin:10px 0;"
            "border-left:4px solid " + pc + ";\'>\n"
            "<strong>" + r["name"] + "</strong> "
            "<span style=\'background:" + pc + ";color:white;padding:2px 8px;border-radius:10px;"
            "font-size:0.78em;\'>" + party + "</span>"
            "<span style=\'background:" + threat_c + ";color:white;padding:2px 8px;border-radius:10px;"
            "font-size:0.78em;margin-left:4px;\'>⚠️ " + r.get("threat_level", "LOW") + "</span>"
            "<br/><ul style=\'margin:8px 0;padding-left:18px;\'>" + items + "</ul></div>\n"
        )
    html = (
        "<div style=\'background:#f8fafc;border-left:5px solid #7c3aed;padding:16px;"
        "border-radius:0 10px 10px 0;margin-bottom:20px;\'>"
        "<h2 style=\'color:#1e3a8a;margin:0 0 8px;\'>Political Media Intelligence Report</h2>"
        "<p style=\'color:#6b7280;margin:0;font-size:0.9em;\'>" + scan_time + "</p></div>"
        "<h3>স্ক্যান সারসংক্ষেপ</h3>"
        "<table style=\'width:100%;border-collapse:collapse;margin-bottom:20px;\'>"
        "<tr style=\'background:#f1f5f9;\'>"
        "<td style=\'padding:10px;border:1px solid #e2e8f0;font-weight:600;\'>সফল আউটলেট</td>"
        "<td style=\'padding:10px;border:1px solid #e2e8f0;\'>" + str(len(successful)) + " টি</td>"
        "<td style=\'padding:10px;border:1px solid #e2e8f0;font-weight:600;\'>মোট শিরোনাম</td>"
        "<td style=\'padding:10px;border:1px solid #e2e8f0;\'>" + str(total_hl) + " টি</td></tr>"
        "<tr>"
        "<td style=\'padding:10px;border:1px solid #e2e8f0;font-weight:600;\'>High Threat</td>"
        "<td style=\'padding:10px;border:1px solid #e2e8f0;color:#dc2626;font-weight:700;\'>" + str(high_threat) + " টি</td>"
        "<td style=\'padding:10px;border:1px solid #e2e8f0;font-weight:600;\'>শীর্ষ দল</td>"
        "<td style=\'padding:10px;border:1px solid #e2e8f0;\'>" + top_party + "</td></tr>"
        "<tr style=\'background:#f1f5f9;\'>"
        "<td style=\'padding:10px;border:1px solid #e2e8f0;font-weight:600;\'>প্রধান থিম</td>"
        "<td colspan=\'3\' style=\'padding:10px;border:1px solid #e2e8f0;\'>" + " · ".join(top_themes) + "</td>"
        "</tr></table>"
        "<h3>আউটলেট ভিত্তিক শিরোনাম</h3>" + rows_html +
        "<hr style=\'border:none;border-top:2px solid #e2e8f0;margin:24px 0;\'>"
        "<p style=\'color:#9ca3af;font-size:0.82em;text-align:center;\'>"
        "Auto-generated · Political Media Intelligence System · " + scan_time + "</p>"
    )
    return title, html


def build_per_outlet_posts(results):
    posts = []
    for r in [x for x in results if x.get("status") == "success" and x.get("headlines")]:
        party   = r.get("dominant_party") or "General"
        theme   = r.get("dominant_theme", "General")
        threat  = r.get("threat_level", "LOW")
        pc      = PARTY_COLORS.get(party, "#6b7280")
        tc_color = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#16a34a"}.get(threat, "#16a34a")
        date_s  = datetime.now().strftime("%d %B %Y")
        title   = r["name"] + " — " + date_s + " শিরোনাম বিশ্লেষণ"
        items   = "".join("<li style=\'margin-bottom:6px;\'>" + hl + "</li>" for hl in r.get("headlines", []))
        content = (
            "<div style=\'background:#f8fafc;border-left:4px solid " + pc + ";padding:14px;"
            "border-radius:0 8px 8px 0;margin-bottom:16px;\'>"
            "<strong>" + r["name"] + "</strong> | " + r.get("category","").replace("_"," ").title() + "<br/>"
            "<small style=\'color:#6b7280;\'>Key Person: " + r.get("key_person","—") + " | Tier: " + r.get("tier","—") + "</small></div>"
            "<table style=\'width:100%;border-collapse:collapse;margin-bottom:16px;\'>"
            "<tr style=\'background:#f1f5f9;\'>"
            "<td style=\'padding:8px;border:1px solid #e2e8f0;\'><b>Party</b></td>"
            "<td style=\'padding:8px;border:1px solid #e2e8f0;\'>" + party + "</td>"
            "<td style=\'padding:8px;border:1px solid #e2e8f0;\'><b>Theme</b></td>"
            "<td style=\'padding:8px;border:1px solid #e2e8f0;\'>" + theme + "</td></tr>"
            "<tr>"
            "<td style=\'padding:8px;border:1px solid #e2e8f0;\'><b>Threat</b></td>"
            "<td style=\'padding:8px;border:1px solid #e2e8f0;color:" + tc_color + ";font-weight:700;\'>" + threat + "</td>"
            "<td style=\'padding:8px;border:1px solid #e2e8f0;\'><b>Headlines</b></td>"
            "<td style=\'padding:8px;border:1px solid #e2e8f0;\'>" + str(r.get("count",0)) + "</td></tr>"
            "</table><h3>শিরোনাম সমূহ</h3><ul>" + items + "</ul>"
        )
        tags = [r.get("category","media"), party.lower().replace(" ","-"), theme.lower(), "bangladesh", "politics"]
        posts.append({"outlet_name": r["name"], "title": title, "content": content,
                      "tags": [t for t in tags if t and t != "—"]})
    return posts


def main():
    # Header
    st.markdown('<h1 class="main-header">🧠 Political Media Intelligence System</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">'
        'Real-time Bangladesh · India · International Media Monitor · '
        'Playwright + aiohttp + GNews Engine · '
        'Bias · Narrative · Threat · Prediction'
        '</p>',
        unsafe_allow_html=True,
    )

    if not _pw_ok:
        st.warning("⚠️ Playwright browser could not be auto-installed. Tier1 + GNews RSS will still work.")

    # ── SIDEBAR ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🎛️ Control Panel")

        selected_cats = st.multiselect(
            "📂 Media Categories",
            options=list(MEDIA_DIRECTORY.keys()),
            default=["print_newspapers_bangla", "print_newspapers_english",
                     "digital_news_portals", "television_channels"],
            format_func=lambda x: CAT_LABELS.get(x, x),
        )

        selected_outlets = [o for cat in selected_cats for o in MEDIA_DIRECTORY.get(cat, [])]
        st.caption(f"**{len(selected_outlets)} outlets selected**")

        concurrency = st.slider("⚡ Parallel Scrapers", 2, 12, 6,
                                help="Higher = faster but more memory. 6 is recommended for HF Spaces.")

        est_low  = len(selected_outlets) * 3  // max(concurrency, 1)
        est_high = len(selected_outlets) * 7  // max(concurrency, 1)
        st.caption(f"⏱️ Estimated: {est_low}–{est_high}s")

        st.markdown("---")
        threat_filter = st.selectbox("⚠️ Threat Filter", ["All", "HIGH", "MEDIUM", "LOW"])
        party_filter  = st.selectbox("🎯 Party Filter",  ["All"] + list(PARTY_KEYWORDS.keys()))

        st.markdown("---")
        st.markdown("**🔧 Scraper Tiers**")
        for tier, (css, icon) in TIER_CSS.items():
            if tier != "Failed":
                st.markdown(f'<span class="tier-badge {css}">{icon} {tier}</span><br/>', unsafe_allow_html=True)

        st.markdown("---")
        run_scan = st.button("🚀 Run Full Intelligence Scan",
                             type="primary", use_container_width=True,
                             disabled=len(selected_outlets) == 0)
        if len(selected_outlets) == 0:
            st.warning("Please select at least one category.")

    # ── TABS ─────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Overview",
        "⚖️ Bias & Alignment",
        "📢 Narratives",
        "⚠️ Threats",
        "🔮 Prediction",
        "🔍 Search",
        "🌐 WordPress",
        "🔬 Raw Data",
    ])

    # ── SCAN ─────────────────────────────────────────────────
    if run_scan and selected_outlets:
        progress = st.progress(0, "🚀 Initializing scraper engine...")
        status_placeholder = st.empty()
        start_ts = time.time()

        with st.spinner(f"Scanning {len(selected_outlets)} outlets with {concurrency} parallel workers..."):
            progress.progress(0.1, "⚡ Launching scrapers...")
            raw_results = run_scraper(selected_outlets, concurrency=concurrency)

            progress.progress(0.75, "🧠 Running intelligence analysis...")
            results = [analyze_outlet_results(r) for r in raw_results]

            progress.progress(1.0, "✅ Done!")
            progress.empty()

        elapsed = round(time.time() - start_ts, 1)
        st.session_state["results"]   = results
        st.session_state["scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        success_n = sum(1 for r in results if r["status"] == "success")
        total_hl  = sum(r["count"] for r in results if r["status"] == "success")
        st.success(
            f"✅ **Scan complete** in **{elapsed}s** — "
            f"{success_n}/{len(results)} outlets · **{total_hl}** headlines scraped"
        )

        # Tier breakdown
        tier_counts = Counter(r.get("tier", "Failed") for r in results)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("⚡ Tier1 (aiohttp)",    tier_counts.get("Tier1 (aiohttp)", 0))
        c2.metric("🎭 Tier2 (Playwright)", tier_counts.get("Tier2 (Playwright)", 0))
        c3.metric("🥷 Tier3 (Stealth)",    tier_counts.get("Tier3 (Stealth)", 0))
        c4.metric("📡 Tier4 (GNews)",      tier_counts.get("Tier4 (GNews RSS)", 0))
        c5.metric("❌ Failed",              tier_counts.get("Failed", 0))

    # ── Load state ───────────────────────────────────────────
    results    = st.session_state.get("results", [])
    scan_time  = st.session_state.get("scan_time", "—")

    if not results:
        st.info("👆 Select categories in the sidebar and click **Run Full Intelligence Scan** to begin.")
        return

    successful = [r for r in results if r["status"] == "success"]
    failed     = [r for r in results if r["status"] == "failed"]

    # Apply sidebar filters
    filtered = successful[:]
    if party_filter != "All":
        filtered = [r for r in filtered if r.get("dominant_party") == party_filter]
    if threat_filter != "All":
        filtered = [r for r in filtered if r.get("threat_level") == threat_filter]

    # ── TAB 1: OVERVIEW ──────────────────────────────────────
    with tab1:
        # KPIs
        high_threat_n = sum(1 for r in successful if r.get("threat_level") == "HIGH")
        coord_n = sum(1 for n in detect_narratives(successful) if n["coordinated"])
        total_hl_n = sum(r["count"] for r in successful)
        avg_sent = round(
            sum(r.get("avg_polarity", 0) for r in successful) / max(len(successful), 1), 3
        ) if successful else 0

        cols = st.columns(6)
        kpi_data = [
            ("📡 Outlets Scanned",  len(results),     f"{len(successful)} success"),
            ("📰 Headlines",        total_hl_n,        f"Avg {total_hl_n//max(len(successful),1)}/outlet"),
            ("🚨 High Threat",      high_threat_n,     "outlets"),
            ("🔴 Coordinated",      coord_n,           "narratives"),
            ("💬 Avg Sentiment",    f"{avg_sent:+.3f}", "polarity"),
            ("⏰ Last Scan",         scan_time[-8:],    scan_time[:10]),
        ]
        for col, (label, val, sub) in zip(cols, kpi_data):
            col.markdown(_kpi(label, val, sub), unsafe_allow_html=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🌡️ Sentiment Distribution")
            rows = []
            for r in filtered:
                dist  = r.get("sentiment_dist", {})
                total = sum(dist.values()) or 1
                rows.append({
                    "Outlet":      r["name"],
                    "Positive %":  round(dist.get("Positive", 0) / total * 100, 1),
                    "Neutral %":   round(dist.get("Neutral",  0) / total * 100, 1),
                    "Negative %":  round(dist.get("Negative", 0) / total * 100, 1),
                })
            if rows:
                df = pd.DataFrame(rows)
                fig = px.bar(
                    df.melt(id_vars="Outlet", var_name="Sentiment", value_name="Percent"),
                    x="Percent", y="Outlet", color="Sentiment", orientation="h",
                    color_discrete_map={
                        "Positive %": "#16a34a",
                        "Neutral %":  "#6b7280",
                        "Negative %": "#dc2626",
                    },
                    template="plotly_white",
                )
                fig.update_layout(barmode="stack", height=max(320, len(rows) * 28),
                                  margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("🎨 Narrative Theme Distribution")
            theme_agg: Counter = Counter()
            for r in filtered:
                for t, c in r.get("narrative_themes", {}).items():
                    theme_agg[t] += c
            if theme_agg:
                df_t = pd.DataFrame(theme_agg.items(), columns=["Theme", "Mentions"])
                fig2 = px.pie(df_t, values="Mentions", names="Theme",
                              color_discrete_sequence=px.colors.qualitative.Bold,
                              template="plotly_white")
                fig2.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📋 Outlet Summary Table")
        tbl = []
        for r in filtered:
            tbl.append({
                "Media":          r["name"],
                "Category":       r["category"].replace("_", " ").title(),
                "Headlines":      r["count"],
                "Avg Sentiment":  round(r.get("avg_polarity", 0), 3),
                "Dominant Party": r.get("dominant_party") or "—",
                "Main Theme":     r.get("dominant_theme", "—"),
                "Threat Level":   r.get("threat_level", "—"),
                "Scraper Tier":   r.get("tier", "—"),
                "Time (s)":       r.get("elapsed_sec", "—"),
            })
        if tbl:
            df_tbl = pd.DataFrame(tbl)
            st.dataframe(
                df_tbl.style
                .applymap(
                    lambda v: "background:#fee2e2;font-weight:bold" if v == "HIGH"
                    else ("background:#fef3c7" if v == "MEDIUM" else ""),
                    subset=["Threat Level"]
                )
                .background_gradient(subset=["Avg Sentiment"], cmap="RdYlGn", vmin=-1, vmax=1),
                use_container_width=True, height=400,
            )

        if failed:
            with st.expander(f"❌ {len(failed)} failed outlets — click to expand"):
                for r in failed:
                    err = r.get("error") or "Unknown error"
                    st.write(f"• **{r['name']}** (`{r['website']}`) — {err[:80]}")

    # ── TAB 2: BIAS & ALIGNMENT ───────────────────────────────
    with tab2:
        st.subheader("⚖️ Media Bias & Party Alignment")

        matrix: defaultdict = defaultdict(lambda: defaultdict(int))
        for r in successful:
            for p, s in r.get("party_bias", {}).items():
                matrix[r["name"]][p] += s

        if matrix:
            mdf = pd.DataFrame(matrix).T.fillna(0)
            if not mdf.empty:
                fig_h = px.imshow(
                    mdf, title="Media × Party Coverage Heatmap",
                    color_continuous_scale="Blues", aspect="auto",
                    labels=dict(color="Mentions"), template="plotly_white",
                )
                fig_h.update_layout(height=max(420, len(mdf) * 30))
                st.plotly_chart(fig_h, use_container_width=True)

        st.subheader("🎯 Party Alignment Cards")
        cols = st.columns(3)
        for i, r in enumerate(successful):
            party  = r.get("dominant_party") or "—"
            color  = PARTY_COLORS.get(party, "#6b7280")
            pol    = r.get("avg_polarity", 0)
            icon   = "😊" if pol > 0.1 else ("😠" if pol < -0.1 else "😐")
            tl     = r.get("threat_level", "LOW")
            ti     = _threat_icon(tl)
            tier   = r.get("tier", "—")
            tc, ti2 = TIER_CSS.get(tier, ("tierfail", "❓"))
            with cols[i % 3]:
                st.markdown(f"""
                <div class="outlet-card" style="border-left:5px solid {color};">
                    <b>{r['name']}</b>
                    &nbsp;<span style="font-size:0.78rem;color:#9ca3af;">{r['category'].replace('_',' ')}</span><br/>
                    <span style="color:{color}; font-size:0.87rem; font-weight:600;">▶ {party}</span><br/>
                    <span style="font-size:0.8rem; color:#6b7280;">
                        {icon} {pol:+.2f} &nbsp;|&nbsp; {ti} {tl}
                        &nbsp;|&nbsp; 📰 {r['count']} hl
                    </span><br/>
                    <span class="tier-badge {tc}" style="font-size:0.68rem;">{ti2} {tier}</span>
                </div>
                """, unsafe_allow_html=True)

        st.subheader("📊 Party Mentions — All Media")
        overall: Counter = Counter()
        for r in successful:
            for p, s in r.get("party_bias", {}).items():
                overall[p] += s
        if overall:
            df_p = pd.DataFrame(overall.items(), columns=["Party", "Mentions"]).sort_values("Mentions")
            fig_p = px.bar(df_p, x="Mentions", y="Party", orientation="h",
                           color="Party", color_discrete_map=PARTY_COLORS,
                           title="Total Party Mentions Across All Scanned Media",
                           template="plotly_white")
            fig_p.update_layout(showlegend=False)
            st.plotly_chart(fig_p, use_container_width=True)

    # ── TAB 3: NARRATIVES ─────────────────────────────────────
    with tab3:
        st.subheader("📢 Emerging Narrative Detection")
        st.caption("৩+ মিডিয়া একই phrase push করলে 🔴 COORDINATED হিসেবে চিহ্নিত হবে")

        narratives = detect_narratives(successful)
        if narratives:
            col1, col2 = st.columns([3, 1])
            with col1:
                for n in narratives:
                    badge = "🔴 COORDINATED" if n["coordinated"] else "🟡 Organic"
                    theme_color = "#7c3aed" if n["theme"] != "General" else "#6b7280"
                    st.markdown(f"""
                    <div class="narrative-box">
                        <b>"{n['phrase']}"</b>
                        &nbsp;<span style="background:{theme_color};color:white;padding:2px 8px;
                                    border-radius:10px;font-size:0.76rem;">{n['theme']}</span>
                        &nbsp;<span style="font-size:0.8rem;">{badge}</span><br/>
                        <span style="color:#6b7280;font-size:0.82rem;">
                            {n['source_count']} outlets · {n['count']} mentions
                        </span><br/>
                        <span style="font-size:0.76rem;color:#9ca3af;">
                            📰 {' · '.join(n['sources'][:6])}{'...' if len(n['sources'])>6 else ''}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

            with col2:
                coord   = sum(1 for n in narratives if n["coordinated"])
                organic = len(narratives) - coord
                st.metric("🔴 Coordinated", coord)
                st.metric("🟡 Organic",     organic)
                st.metric("📢 Total",        len(narratives))
                outlets_in = len(set(s for n in narratives for s in n["sources"]))
                st.metric("📰 Outlets",      outlets_in)

                tc = Counter(n["theme"] for n in narratives)
                fig_tc = px.pie(
                    pd.DataFrame(tc.items(), columns=["Theme", "Count"]),
                    values="Count", names="Theme", title="By Theme",
                    color_discrete_sequence=px.colors.qualitative.Safe,
                    template="plotly_white",
                )
                st.plotly_chart(fig_tc, use_container_width=True)
        else:
            st.info("More outlets needed to detect narratives. Try selecting more categories.")

    # ── TAB 4: THREATS ────────────────────────────────────────
    with tab4:
        st.subheader("⚠️ Threat Intelligence Dashboard")
        signals = detect_threats(successful)

        if signals:
            high_signals = [s for s in signals if s["level"] == "HIGH"]
            med_signals  = [s for s in signals if s["level"] == "MEDIUM"]
            st.error(f"🚨 {len(signals)} threat signal(s) detected! ({len(high_signals)} HIGH, {len(med_signals)} MEDIUM)")
            for ts in signals:
                css = "alert-danger" if ts["level"] == "HIGH" else "alert-warning"
                outlets_str = f"<br/><small>Outlets: {', '.join(ts['outlets'][:8])}</small>" if ts.get("outlets") else ""
                st.markdown(f"""
                <div class="alert-box {css}">
                    <b>{_threat_icon(ts['level'])} {ts['type']}</b><br/>
                    {ts['detail']}{outlets_str}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No coordinated threat campaigns detected in current scan.")

        st.markdown("---")
        st.subheader("📊 Threat Score by Outlet")
        td = sorted(
            [{"Outlet": r["name"], "Score": r.get("threat_score", 0), "Level": r.get("threat_level", "LOW")}
             for r in (filtered if threat_filter != "All" else successful)],
            key=lambda x: x["Score"], reverse=True
        )
        if td:
            df_td = pd.DataFrame(td)
            fig_td = px.bar(
                df_td, x="Outlet", y="Score", color="Level",
                color_discrete_map={"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#16a34a"},
                title="Threat Score per Outlet", template="plotly_white",
            )
            fig_td.update_layout(xaxis_tickangle=-35, height=380)
            st.plotly_chart(fig_td, use_container_width=True)

        st.subheader("🔑 Top Threat Keywords Detected")
        kw_hits: Counter = Counter()
        for r in successful:
            for a in r.get("analyzed_headlines", []):
                for kw in a.get("threat_hits", []):
                    kw_hits[kw] += 1
        if kw_hits:
            df_kw = pd.DataFrame(kw_hits.most_common(18), columns=["Keyword", "Count"])
            fig_kw = px.bar(df_kw, x="Count", y="Keyword", orientation="h",
                            color="Count", color_continuous_scale="Reds",
                            title="Most Frequent Threat Keywords", template="plotly_white")
            st.plotly_chart(fig_kw, use_container_width=True)

    # ── TAB 5: PREDICTION ─────────────────────────────────────
    with tab5:
        st.subheader("🔮 Predictive Political Intelligence")
        st.caption("Current media signal analysis → 2–4 week political forecast")

        preds = predict_issues(successful)
        if preds:
            for i, p in enumerate(preds, 1):
                intensity = p["intensity"]
                color = "#dc2626" if intensity >= 70 else ("#d97706" if intensity >= 40 else "#16a34a")
                st.markdown(f"""
                <div class="predict-card" style="border-left:6px solid {color};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size:1.05rem;">#{i} {p['theme']}</b>
                        <span style="background:{color};color:white;padding:4px 12px;
                                     border-radius:12px;font-size:0.82rem;font-weight:700;">
                            {intensity}% Signal
                        </span>
                    </div>
                    <p style="margin:8px 0 0 0;color:#374151;font-size:0.92rem;">{p['prediction']}</p>
                    <span style="font-size:0.78rem;color:#9ca3af;">Media mentions: {p['count']}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            df_pred = pd.DataFrame(preds)
            fig_pred = px.bar(
                df_pred, x="theme", y="intensity",
                color="intensity", color_continuous_scale="RdYlGn_r",
                title="Predicted Issue Intensity (Next 2–4 Weeks)",
                labels={"theme": "Political Theme", "intensity": "Signal Strength (%)"},
                template="plotly_white",
            )
            fig_pred.update_layout(showlegend=False, xaxis_tickangle=-20)
            st.plotly_chart(fig_pred, use_container_width=True)
        else:
            st.info("Not enough data for predictions. Run a scan first.")

    # ── TAB 6: SEARCH ─────────────────────────────────────────
    with tab6:
        st.subheader("🔍 Cross-Media Headline Intelligence Search")
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            q = st.text_input("Search term", placeholder="e.g. নির্বাচন / election / bnp / yunus / arrest")
        with col_s2:
            search_party = st.selectbox("Filter by party", ["All"] + list(PARTY_KEYWORDS.keys()),
                                        key="search_party")

        if q:
            matches = []
            for r in successful:
                if search_party != "All" and r.get("dominant_party") != search_party:
                    continue
                for h in r.get("headlines", []):
                    if q.lower() in h.lower():
                        a = analyze_text(h)
                        matches.append({
                            "Source":    r["name"],
                            "Category":  r["category"].replace("_", " ").title(),
                            "Tier":      r.get("tier", "—"),
                            "Headline":  h,
                            "Sentiment": a["sentiment"],
                            "Party":     a.get("dominant_party") or "—",
                            "Theme":     a.get("dominant_theme", "—"),
                        })

            st.write(f"**{len(matches)} results** found for `{q}`")
            if matches:
                df_m = pd.DataFrame(matches)
                st.dataframe(
                    df_m.style.applymap(
                        lambda v: "color:#16a34a;font-weight:600" if v == "Positive"
                        else ("color:#dc2626;font-weight:600" if v == "Negative" else ""),
                        subset=["Sentiment"]
                    ),
                    use_container_width=True, height=400,
                )

                # Sentiment breakdown of search results
                sent_ct = Counter(m["Sentiment"] for m in matches)
                fig_s = px.pie(
                    pd.DataFrame(sent_ct.items(), columns=["Sentiment", "Count"]),
                    values="Count", names="Sentiment",
                    color="Sentiment",
                    color_discrete_map={"Positive": "#16a34a", "Neutral": "#6b7280", "Negative": "#dc2626"},
                    title=f"Sentiment of results for '{q}'",
                    template="plotly_white",
                )
                st.plotly_chart(fig_s, use_container_width=True)


    # ── TAB 7: WORDPRESS ──────────────────────────────────────
    with tab7:
        st.subheader("🌐 WordPress Auto-Publish")
        st.caption("স্ক্যান ফলাফল সরাসরি WordPress সাইটে পোস্ট করুন")

        with st.expander("🔑 WordPress Credentials", expanded=True):
            st.info(
                "**Application Password ব্যবহার করুন**\n\n"
                "WordPress Admin → Users → Profile → Application Passwords → নতুন পাসওয়ার্ড তৈরি করুন\n\n"
                "⚠️ Regular login password কাজ করবে না।"
            )
            wc1, wc2 = st.columns(2)
            with wc1:
                wp_url  = st.text_input("🔗 WordPress URL", placeholder="https://your-site.com",
                                        value=st.session_state.get("wp_url", ""), key="wp_url_input")
                wp_user = st.text_input("👤 Username", placeholder="admin",
                                        value=st.session_state.get("wp_user", ""), key="wp_user_input")
            with wc2:
                wp_pass   = st.text_input("🔐 Application Password",
                                          placeholder="xxxx xxxx xxxx xxxx xxxx xxxx",
                                          type="password", key="wp_pass_input")
                wp_status = st.selectbox("📤 Post Status", ["draft", "publish", "pending"],
                                         index=0, key="wp_status_input",
                                         help="draft = ড্রাফট হিসেবে সেভ হবে, পাবলিশ হবে না")
            if st.button("🔌 Test Connection"):
                if wp_url and wp_user and wp_pass:
                    with st.spinner("Connecting..."):
                        conn = wp_test_connection(wp_url, wp_user, wp_pass)
                    if conn["ok"]:
                        st.success("✅ Connected! User: **" + conn["name"] + "** | Roles: " + ", ".join(conn["roles"]))
                        st.session_state["wp_url"]  = wp_url
                        st.session_state["wp_user"] = wp_user
                    else:
                        st.error("❌ Failed: " + conn["error"])
                else:
                    st.warning("URL, Username ও Password সব দিন।")

        if not successful:
            st.warning("⚠️ WordPress-এ পোস্ট করতে আগে scan চালান।")
        else:
            st.markdown("---")

            # Optional: fetch WP categories
            wp_url_val  = st.session_state.get("wp_url", "")
            wp_user_val = st.session_state.get("wp_user", "")
            wp_pass_val = st.session_state.get("wp_pass_input", "")
            cat_ids_wp  = []

            with st.expander("🗂️ WordPress Category (optional)"):
                if wp_url_val and wp_user_val and wp_pass_val:
                    if st.button("📂 Fetch WP Categories"):
                        wpcats = wp_get_categories(wp_url_val, wp_user_val, wp_pass_val)
                        st.session_state["wp_cats"] = wpcats
                    wpcats_list = st.session_state.get("wp_cats", [])
                    if wpcats_list:
                        cat_map = {c["name"]: c["id"] for c in wpcats_list}
                        sel_wpcat = st.selectbox("Category", ["— None —"] + list(cat_map.keys()))
                        if sel_wpcat != "— None —":
                            cat_ids_wp = [cat_map[sel_wpcat]]
                else:
                    st.info("Credentials সেট করুন তারপর categories দেখতে পারবেন।")

            pub_mode = st.radio(
                "পোস্ট মোড",
                ["📄 Summary Post", "📋 Per-Outlet Posts", "🎯 Selected Outlets"],
                horizontal=True
            )

            wp_url_cur  = st.session_state.get("wp_url_input", "") or st.session_state.get("wp_url", "")
            wp_user_cur = st.session_state.get("wp_user_input", "") or st.session_state.get("wp_user", "")
            wp_pass_cur = st.session_state.get("wp_pass_input", "")
            wp_stat_cur = st.session_state.get("wp_status_input", "draft")

            if "Summary" in pub_mode:
                wp_title, wp_html = build_wp_summary_post(results, scan_time)
                with st.expander("👁️ Preview Post"):
                    st.write("**Title:** " + wp_title)
                    st.components.v1.html(wp_html, height=380, scrolling=True)
                if st.button("🚀 Publish Summary Post to WordPress", type="primary", use_container_width=True):
                    if not (wp_url_cur and wp_user_cur and wp_pass_cur):
                        st.error("❌ Credentials দিন।")
                    else:
                        with st.spinner("Publishing..."):
                            pub_res = wp_post_article(
                                wp_url_cur, wp_user_cur, wp_pass_cur,
                                wp_title, wp_html, status=wp_stat_cur,
                                category_ids=cat_ids_wp,
                                tags=["political-intelligence", "bangladesh", "media-analysis"]
                            )
                        if pub_res["ok"]:
                            st.success("✅ Published! Post ID: **" + str(pub_res["id"]) + "**")
                            if pub_res.get("link"):
                                st.markdown("🔗 [পোস্ট দেখুন](" + pub_res["link"] + ")")
                        else:
                            st.error("❌ Failed: " + pub_res["error"])

            elif "Per-Outlet" in pub_mode:
                outlet_posts = build_per_outlet_posts(results)
                st.info("**" + str(len(outlet_posts)) + " posts** তৈরি হবে — প্রতি outlet আলাদা পোস্ট")
                pa_col, pb_col = st.columns(2)
                with pa_col:
                    pub_delay = st.slider("Delay between posts (seconds)", 0, 5, 1, key="pub_delay")
                if st.button("🚀 Publish " + str(len(outlet_posts)) + " Posts", type="primary", use_container_width=True):
                    if not (wp_url_cur and wp_user_cur and wp_pass_cur):
                        st.error("❌ Credentials দিন।")
                    else:
                        wp_prog = st.progress(0, "Publishing...")
                        pub_ok_n, pub_fail_n = 0, 0
                        for idx, opost in enumerate(outlet_posts):
                            pub_r = wp_post_article(
                                wp_url_cur, wp_user_cur, wp_pass_cur,
                                opost["title"], opost["content"],
                                status=wp_stat_cur, category_ids=cat_ids_wp,
                                tags=opost.get("tags", [])
                            )
                            if pub_r["ok"]:
                                pub_ok_n += 1
                                link_html = ("<a href=\"" + pub_r.get("link","") + "\" target=\"_blank\">Post #" + str(pub_r.get("id","")) + "</a>")
                                st.markdown(
                                    "<div class=\"wp-card\">✅ <b>" + opost["outlet_name"] + "</b> — " + link_html + "</div>",
                                    unsafe_allow_html=True
                                )
                            else:
                                pub_fail_n += 1
                                st.markdown(
                                    "<div class=\"wp-error\">❌ <b>" + opost["outlet_name"] + "</b> — " + pub_r["error"][:80] + "</div>",
                                    unsafe_allow_html=True
                                )
                            wp_prog.progress((idx + 1) / len(outlet_posts))
                            if pub_delay > 0:
                                time.sleep(pub_delay)
                        wp_prog.empty()
                        st.success("✅ " + str(pub_ok_n) + "/" + str(len(outlet_posts)) + " published! | ❌ " + str(pub_fail_n) + " failed")

            else:
                outlet_names_list = [r["name"] for r in successful]
                sel_outlet_names  = st.multiselect("Outlets বেছে নিন", outlet_names_list, default=outlet_names_list[:3])
                sel_o_posts = build_per_outlet_posts([r for r in successful if r["name"] in sel_outlet_names])
                if sel_o_posts:
                    if st.button("🚀 Publish " + str(len(sel_o_posts)) + " Selected Posts",
                                 type="primary", use_container_width=True):
                        if not (wp_url_cur and wp_user_cur and wp_pass_cur):
                            st.error("❌ Credentials দিন।")
                        else:
                            pub_ok_s = 0
                            for sop in sel_o_posts:
                                pub_r = wp_post_article(
                                    wp_url_cur, wp_user_cur, wp_pass_cur,
                                    sop["title"], sop["content"],
                                    status=wp_stat_cur, category_ids=cat_ids_wp,
                                    tags=sop.get("tags", [])
                                )
                                if pub_r["ok"]:
                                    pub_ok_s += 1
                                    link_h = ("<a href=\"" + pub_r.get("link","") + "\" target=\"_blank\">Post #" + str(pub_r.get("id","")) + "</a>")
                                    st.markdown("<div class=\"wp-card\">✅ <b>" + sop["outlet_name"] + "</b> — " + link_h + "</div>",
                                                unsafe_allow_html=True)
                                else:
                                    st.markdown("<div class=\"wp-error\">❌ <b>" + sop["outlet_name"] + "</b> — " + pub_r["error"][:80] + "</div>",
                                                unsafe_allow_html=True)
                            st.success("✅ " + str(pub_ok_s) + "/" + str(len(sel_o_posts)) + " published!")


    # ── TAB 8: RAW DATA ───────────────────────────────────────
    with tab8:
        st.subheader("🔬 Raw Scrape Data & Export")

        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Total Outlets",   len(results))
        col_r2.metric("Successful",       len(successful))
        col_r3.metric("Total Headlines",  sum(r["count"] for r in successful))

        for r in results:
            status_icon = "✅" if r["status"] == "success" else ("⏭️" if r["status"] == "skipped" else "❌")
            tier = r.get("tier", "Failed")
            tc, ti = TIER_CSS.get(tier, ("tierfail", "❓"))
            with st.expander(
                f"{status_icon} {r['name']} — {r['count']} headlines — "
                f"{r.get('elapsed_sec','?')}s — {tier}"
            ):
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.markdown(_tier_badge(tier), unsafe_allow_html=True)
                    st.write(f"**URL:** `{r.get('url','—')}`")
                    st.write(f"**Key Person:** {r.get('key_person','—')}")
                    st.write(f"**Scraped at:** {r.get('scraped_at','—')}")
                    if r.get("error"):
                        st.error(f"Error: {r['error'][:120]}")
                with col_b:
                    hls = r.get("headlines", [])
                    if hls:
                        for hl in hls[:20]:
                            st.write(f"• {hl}")
                        if len(hls) > 20:
                            st.caption(f"... and {len(hls)-20} more headlines")
                    else:
                        st.warning("No headlines scraped.")

        st.markdown("---")
        st.subheader("📥 Export")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            export_data = [
                {k: v for k, v in r.items() if k != "analyzed_headlines"}
                for r in results
            ]
            st.download_button(
                label="📥 Download Full JSON",
                data=json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name=f"media_intel_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_e2:
            if successful:
                rows_csv = []
                for r in successful:
                    for hl in r.get("headlines", []):
                        a = analyze_text(hl)
                        rows_csv.append({
                            "source":    r["name"],
                            "category":  r["category"],
                            "headline":  hl,
                            "sentiment": a["sentiment"],
                            "party":     a.get("dominant_party") or "",
                            "theme":     a.get("dominant_theme", ""),
                            "threat":    a.get("threat_level", ""),
                        })
                if rows_csv:
                    df_csv = pd.DataFrame(rows_csv)
                    st.download_button(
                        label="📥 Download Headlines CSV",
                        data=df_csv.to_csv(index=False, encoding="utf-8-sig"),
                        file_name=f"headlines_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )


if __name__ == "__main__":
    main()
