import streamlit as st
import streamlit as st
import os

# Cloud-e Playwright browser install korar jonno
os.system("playwright install chromium")

st.set_page_config(
    page_title="Political Media Intelligence",
    # ... baki code
)

st.set_page_config(
    page_title="Political Media Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import time
from datetime import datetime
from collections import Counter, defaultdict
from textblob import TextBlob

# Import our powerful scraping engine
from scraper_engine import run_scraper, SITE_SELECTORS

# ============================================================
# MEDIA DIRECTORY
# ============================================================

MEDIA_DIRECTORY = {
    "print_newspapers_bangla": [
        {"name": "Daily Janakantha",  "website": "dailyjanakantha.com",  "key_person": "Enayetur Rahim"},
        {"name": "Jai Jai Din",       "website": "jjdin.com",            "key_person": "Sayeed Hossain Chowdhury"},
        {"name": "Bhorer Kagoj",      "website": "bhorerkagoj.com",      "key_person": "Shyamal Dutta"},
        {"name": "Daily Inqilab",     "website": "dailyinqilab.com",     "key_person": "A.M.M. Bahauddin"},
        {"name": "Sangbad",           "website": "sangbad.net.bd",       "key_person": "Altamash Kabir"},
        {"name": "Daily Dinkal",      "website": "daily-dinkal.com",     "key_person": "Dr. Rezuan Hossain"},
        {"name": "Kalbela",           "website": "kalbela.com",          "key_person": "Mia Nuruddin Apu"},
        {"name": "Desh Rupantor",     "website": "deshrupantor.com",     "key_person": "Mustafa Mamun"},
    ],
    "print_newspapers_english": [
        {"name": "Daily Star",        "website": "thedailystar.net",     "key_person": "Mahfuz Anam"},
        {"name": "Daily Observer",    "website": "observerbd.com",       "key_person": "Iqbal Sobhan Chowdhury"},
        {"name": "Business Standard", "website": "tbsnews.net",          "key_person": "Inam Ahmed"},
        {"name": "Dhaka Tribune",     "website": "dhakatribune.com",     "key_person": "Zafar Sobhan"},
    ],
    "digital_news_portals": [
        {"name": "BD News 24",        "website": "bangla.bdnews24.com",  "key_person": "Toufique Imrose Khalidi"},
        {"name": "Jago News 24",      "website": "jagonews24.com",       "key_person": "Mohiuddin Sarker"},
        {"name": "Bangla Tribune",    "website": "banglatribune.com",    "key_person": "Zulfiqer Russell"},
        {"name": "Amar Desh",         "website": "amar-desh24.com",      "key_person": "Mahmudur Rahman"},
    ],
    "television_channels": [
        {"name": "Somoy News",        "website": "somoynews.tv",         "key_person": "Ahmed Jobaer"},
        {"name": "Jamuna TV",         "website": "jamuna.tv",            "key_person": "Fahim Ahmed"},
        {"name": "Channel i",         "website": "channelionline.com",   "key_person": "Shykh Seraj"},
        {"name": "Ekattor TV",        "website": "ekattor.tv",           "key_person": "Mozammel Babu"},
    ],
    "regional_portals": [
        {"name": "Coxsbazar News",    "website": "coxsbazarnews.com",    "key_person": "Prof. Akthar Chowdhury"},
        {"name": "Daily Coxsbazar",   "website": "dailycoxsbazar.com",   "key_person": "Mohammad Mujibur Rahman"},
        {"name": "Uttorpurbo",        "website": "uttorpurbo.com",       "key_person": "Safwan Chowdhury"},
        {"name": "Ajker Jamalpur",    "website": "ajkerjamalpur.com",    "key_person": "Azizur Rahman"},
        {"name": "Amader Barisal",    "website": "amaderbarisal.com",    "key_person": "Saidur Rahman"},
        {"name": "Surma Times",       "website": "surmatimes.com",       "key_person": "Editorial Team"},
        {"name": "Chandpur Times",    "website": "chandpurtimes.com",    "key_person": "Kazi Md. Ibrahim Juel"},
        {"name": "Mukto Khobor 24",   "website": "muktokhobor24.com",    "key_person": "M.A. Malek"},
        {"name": "Bogra Sangbad",     "website": "bograsangbad.com",     "key_person": "Kamal Ahmed"},
        {"name": "Rajshahir Somoy",   "website": "rajshahirsomoy.com",   "key_person": "Humayun Kabir"},
        {"name": "Lakshmipur 24",     "website": "lakshmipur24.com",     "key_person": "Sana Ullah Sanu"},
        {"name": "Prothom Feni",      "website": "prothom-feni.com",     "key_person": "Ariful Amin Majumder"},
        {"name": "Gramer Kagoj",      "website": "gamerkagoj.com",       "key_person": "Mobinul Islam Mobin"},
    ],
    "indian_bengali_media": [
        {"name": "Anandabazar Patrika","website": "anandabazar.com",      "key_person": "Aveek Sarkar"},
        {"name": "Sangbad Pratidin",  "website": "sangbadpratidin.in",   "key_person": "Srinjoy Bose"},
        {"name": "ABP Ananda",        "website": "bengali.abplive.com",  "key_person": "Suman De"},
        {"name": "24 Ghanta",         "website": "zee24ghanta.com",      "key_person": "Anirban Chowdhury"},
        {"name": "Ei Samay",          "website": "eisamay.com",          "key_person": "Rupankar Sarkar"},
        {"name": "Bartaman Patrika",  "website": "bartamanpatrika.com",  "key_person": "Subha Dutta"},
    ],
    "international_news_agencies": [
        {"name": "BBC News",          "website": "bbc.com",              "key_person": "Tim Davie"},
        {"name": "Al Jazeera",        "website": "aljazeera.com",        "key_person": "Mostefa Souag"},
        {"name": "AFP",               "website": "afp.com",              "key_person": "Fabrice Fries"},
        {"name": "The Guardian",      "website": "theguardian.com",      "key_person": "Katharine Viner"},
        {"name": "CNN",               "website": "edition.cnn.com",      "key_person": "Mark Thompson"},
        {"name": "NY Times",          "website": "nytimes.com",          "key_person": "A.G. Sulzberger"},
        {"name": "Hindustan Times",   "website": "hindustantimes.com",   "key_person": "Shobhana Bhartia"},
        {"name": "ABC News",          "website": "abcnews.go.com",       "key_person": "David Muir"},
        {"name": "Yahoo News",        "website": "news.yahoo.com",       "key_person": "Editorial Team"},
    ],
}

ALL_MEDIA = []
for cat, outlets in MEDIA_DIRECTORY.items():
    for o in outlets:
        o["category"] = cat
        ALL_MEDIA.append(o)

# ============================================================
# POLITICAL INTELLIGENCE KEYWORDS
# ============================================================

PARTY_KEYWORDS = {
    "Awami League":       ["awami", "আওয়ামী", "sheikh hasina", "শেখ হাসিনা", "নৌকা", "league", "হাসিনা", "মুজিব", "mujib", "বঙ্গবন্ধু", "bangabandhu", "১৪ দল", "fourteen party"],
    "BNP":                ["bnp", "বিএনপি", "khaleda", "খালেদা", "tarique", "তারেক", "জিয়া", "zia", "২০ দল", "twenty party", "তত্ত্বাবধায়ক", "caretaker", "নির্দলীয়"],
    "Jamaat-e-Islami":    ["jamaat", "জামায়াত", "ইসলামী", "islami", "শিবির", "shib", "নিজামী", "nizami", "মুজাহিদ", "রাজাকার"],
    "Jatiya Party":       ["jatiya party", "জাতীয় পার্টি", "ershad", "এরশাদ", "রওশন", "rowshan", "লাঙল", "জাপা"],
    "Interim Government": ["interim", "অন্তর্বর্তী", "yunus", "ইউনুস", "chief adviser", "প্রধান উপদেষ্টা", "সংস্কার", "reform"],
}

THREAT_KEYWORDS = [
    "সহিংসতা", "violence", "হামলা", "attack", "গ্রেপ্তার", "arrest",
    "নিষিদ্ধ", "ban", "ষড়যন্ত্র", "conspiracy", "বিদেশী হস্তক্ষেপ",
    "foreign interference", "অস্থিরতা", "instability", "অবরোধ", "blockade",
    "হরতাল", "hartal", "strike", "ধর্মঘট", "সংঘাত", "conflict",
    "উত্তেজনা", "tension", "সংকট", "crisis", "আন্দোলন", "movement",
    "নিহত", "killed", "আহত", "injured", "ধর্মঘট", "সংঘর্ষ", "clash"
]

NARRATIVE_THEMES = {
    "Election":       ["নির্বাচন", "election", "ভোট", "vote", "ballot", "প্রার্থী", "candidate", "ইভিএম", "evm"],
    "Economy":        ["অর্থনীতি", "economy", "মূল্যস্ফীতি", "inflation", "দ্রব্যমূল্য", "price", "taka", "টাকা", "রিজার্ভ", "reserve"],
    "Security":       ["নিরাপত্তা", "security", "পুলিশ", "police", "র‌্যাব", "rab", "সেনা", "army", "বিজিবি", "bgb"],
    "Corruption":     ["দুর্নীতি", "corruption", "লুটপাট", "looting", "অর্থ আত্মসাৎ", "embezzlement", "দুদক", "acc"],
    "Foreign Policy": ["ভারত", "india", "চীন", "china", "আমেরিকা", "america", "usa", "রোহিঙ্গা", "rohingya", "মিয়ানমার", "myanmar"],
    "Justice":        ["বিচার", "justice", "মামলা", "case", "আদালত", "court", "ট্রাইব্যুনাল", "tribunal", "রায়", "verdict"],
    "Protest":        ["আন্দোলন", "protest", "বিক্ষোভ", "demonstration", "ধর্মঘট", "সমাবেশ", "rally", "মিছিল"],
}

# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem; font-weight: 800;
        background: linear-gradient(135deg, #1e3a8a, #7c3aed);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 0.3rem;
    }
    .sub-header { text-align: center; color: #6b7280; margin-bottom: 1.5rem; }
    .tier-badge {
        font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;
        font-weight: 600; display: inline-block;
    }
    .tier1 { background: #d1fae5; color: #065f46; }
    .tier2 { background: #dbeafe; color: #1e40af; }
    .tier3 { background: #ede9fe; color: #5b21b6; }
    .tierfail { background: #fee2e2; color: #991b1b; }
    .narrative-box {
        border-left: 4px solid #7c3aed; padding: 12px;
        background: #f5f3ff; border-radius: 0 8px 8px 0; margin: 8px 0;
    }
    .threat-card {
        border: 1px solid #fca5a5; background: #fff1f2;
        border-radius: 10px; padding: 14px; margin: 8px 0;
        border-left: 5px solid #dc2626;
    }
    .predict-card {
        border: 1px solid #e5e7eb; padding: 16px; border-radius: 10px; margin: 10px 0;
    }
    .outlet-card {
        border: 1px solid #e5e7eb; border-radius: 8px;
        padding: 10px; margin: 6px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# INTELLIGENCE ANALYSIS ENGINE
# ============================================================

def analyze_text(text: str) -> dict:
    text_lower = text.lower()
    try:
        polarity = TextBlob(text).sentiment.polarity
    except:
        polarity = 0.0

    sentiment = "Positive" if polarity > 0.1 else ("Negative" if polarity < -0.1 else "Neutral")

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
    dominant_theme = max(theme_scores, key=theme_scores.get) if theme_scores else "General"

    return {
        "sentiment": sentiment,
        "polarity": round(polarity, 3),
        "party_scores": party_scores,
        "dominant_party": max(party_scores, key=party_scores.get) if party_scores else None,
        "threat_score": threat_score,
        "threat_level": threat_level,
        "threat_hits": threat_hits,
        "dominant_theme": dominant_theme,
        "theme_scores": theme_scores,
    }


def analyze_outlet_results(raw: dict) -> dict:
    """Combine scrape result + intelligence analysis"""
    headlines = raw.get("headlines", [])
    if not headlines:
        return {**raw, "avg_polarity": 0, "sentiment_dist": {}, "party_bias": {},
                "dominant_party": None, "threat_score": 0, "threat_level": "LOW",
                "dominant_theme": "N/A", "narrative_themes": {}, "analyzed_headlines": []}

    analyzed = [{"text": h, **analyze_text(h)} for h in headlines]

    polarities = [a["polarity"] for a in analyzed]
    avg_polarity = round(sum(polarities) / len(polarities), 3)

    sentiment_dist = Counter(a["sentiment"] for a in analyzed)

    party_agg = defaultdict(int)
    theme_agg = defaultdict(int)
    for a in analyzed:
        for p, s in a["party_scores"].items(): party_agg[p] += s
        for t, s in a["theme_scores"].items(): theme_agg[t] += s

    avg_threat = sum(a["threat_score"] for a in analyzed) / len(analyzed)
    threat_level = "HIGH" if avg_threat >= 50 else ("MEDIUM" if avg_threat >= 25 else "LOW")

    return {
        **raw,
        "avg_polarity":      avg_polarity,
        "sentiment_dist":    dict(sentiment_dist),
        "party_bias":        dict(party_agg),
        "dominant_party":    max(party_agg, key=party_agg.get) if party_agg else None,
        "threat_score":      round(avg_threat),
        "threat_level":      threat_level,
        "dominant_theme":    max(theme_agg, key=theme_agg.get) if theme_agg else "General",
        "narrative_themes":  dict(theme_agg),
        "analyzed_headlines": analyzed,
    }


# ============================================================
# NARRATIVE & THREAT ENGINES
# ============================================================

def detect_narratives(results: list) -> list:
    all_hl = [{"text": h, "source": r["name"]} for r in results for h in r.get("headlines", [])]
    bigram_freq = Counter()
    bigram_sources = defaultdict(set)

    for item in all_hl:
        words = re.findall(r'[\u0980-\u09FF\w]{3,}', item["text"].lower())
        for i in range(len(words) - 1):
            bg = f"{words[i]} {words[i+1]}"
            bigram_freq[bg] += 1
            bigram_sources[bg].add(item["source"])

    narratives = []
    for bg, count in bigram_freq.most_common(12):
        if count < 2: continue
        sources = list(bigram_sources[bg])
        theme = next((t for t, kws in NARRATIVE_THEMES.items() if any(kw in bg for kw in kws)), "General")
        narratives.append({
            "phrase": bg, "count": count, "sources": sources,
            "source_count": len(sources), "theme": theme,
            "coordinated": len(sources) >= 3,
        })

    return sorted(narratives, key=lambda x: (x["source_count"], x["count"]), reverse=True)[:10]


def detect_threats(results: list) -> list:
    threats = []
    high = [r for r in results if r["threat_level"] == "HIGH"]
    if len(high) >= 3:
        threats.append({
            "type": "Coordinated Threat Coverage",
            "level": "HIGH",
            "detail": f"{len(high)} outlets simultaneously publishing high-threat content",
            "outlets": [r["name"] for r in high],
        })
    party_neg = defaultdict(list)
    for r in results:
        if r["avg_polarity"] < -0.15 and r["dominant_party"]:
            party_neg[r["dominant_party"]].append(r["name"])
    for party, outlets in party_neg.items():
        if len(outlets) >= 3:
            threats.append({
                "type": "Coordinated Negative Campaign",
                "level": "HIGH",
                "detail": f"{len(outlets)} outlets with negative coverage targeting {party}",
                "outlets": outlets,
            })
    return threats


def predict_issues(results: list) -> list:
    theme_counts = Counter()
    for r in results:
        for t, c in r.get("narrative_themes", {}).items():
            theme_counts[t] += c

    PREDICTIONS = {
        "Election":       "নির্বাচনী উত্তেজনা আগামী ২–৪ সপ্তাহে বাড়তে পারে। দলীয় সমাবেশ ও পাল্টাপাল্টি বিবৃতি আসার সম্ভাবনা।",
        "Economy":        "দ্রব্যমূল্য ও অর্থনৈতিক চাপ রাজনৈতিক হাতিয়ার হিসেবে ব্যবহার হওয়ার আশঙ্কা।",
        "Security":       "আইন-শৃঙ্খলা পরিস্থিতি বিরোধীদের আন্দোলনের ট্রিগার হতে পারে।",
        "Corruption":     "দুর্নীতির ন্যারেটিভ আসন্ন রাজনৈতিক বিতর্কে প্রাধান্য পাবে।",
        "Foreign Policy": "বৈদেশিক সম্পর্কের ইস্যু অভ্যন্তরীণ রাজনীতিতে প্রভাব ফেলতে পারে।",
        "Justice":        "বিচারিক উন্নয়ন পরবর্তী রাজনৈতিক সংবাদ চক্রে আধিপত্য বিস্তার করবে।",
        "Protest":        "বিক্ষোভ ও আন্দোলনের মাত্রা বৃদ্ধি পাওয়ার সম্ভাবনা আছে।",
    }

    return [
        {
            "theme": t,
            "intensity": min(c * 6, 100),
            "prediction": PREDICTIONS.get(t, f"{t} ইস্যু রাজনৈতিক আলোচনায় আসতে পারে।"),
            "count": c,
        }
        for t, c in theme_counts.most_common(6)
    ]


# ============================================================
# MAIN APP
# ============================================================

PARTY_COLORS = {
    "Awami League":       "#2563eb",
    "BNP":                "#16a34a",
    "Jamaat-e-Islami":    "#dc2626",
    "Jatiya Party":       "#d97706",
    "Interim Government": "#7c3aed",
}

def main():
    st.markdown('<h1 class="main-header">🧠 Political Media Intelligence System</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time Bangladesh Media · Playwright + aiohttp Engine · Bias · Narrative · Threat · Prediction</p>', unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🎛️ Control Panel")

        CAT_LABELS = {
            "print_newspapers_bangla":    "📰 Bangla Newspapers (8)",
            "print_newspapers_english":   "📰 English Newspapers (4)",
            "digital_news_portals":       "🌐 Digital Portals (4)",
            "television_channels":        "📺 TV Channels (4)",
            "regional_portals":           "📍 Regional BD (13)",
            "indian_bengali_media":       "🇮🇳 Indian Bengali (6)",
            "international_news_agencies":"🌍 International (9)",
        }

        selected_cats = st.multiselect(
            "Media Categories",
            options=list(MEDIA_DIRECTORY.keys()),
            default=["print_newspapers_bangla", "print_newspapers_english", "digital_news_portals", "television_channels"],
            format_func=lambda x: CAT_LABELS.get(x, x)
        )

        selected_outlets = [o for cat in selected_cats for o in MEDIA_DIRECTORY.get(cat, [])]
        st.markdown(f"**{len(selected_outlets)} outlets selected**")

        concurrency = st.slider("⚡ Concurrency (parallel scrapers)", 2, 10, 6)

        st.markdown("---")
        threat_filter = st.selectbox("⚠️ Threat Filter", ["All", "HIGH", "MEDIUM", "LOW"])
        party_filter  = st.selectbox("🎯 Party Filter",  ["All"] + list(PARTY_KEYWORDS.keys()))

        st.markdown("---")

        st.markdown("**🔧 Scraper Tiers**")
        st.markdown("""
        <span class="tier-badge tier1">Tier 1</span> aiohttp (fast)<br/>
        <span class="tier-badge tier2">Tier 2</span> Playwright (JS sites)<br/>
        <span class="tier-badge tier3">Tier 3</span> Stealth (bot-protected)
        """, unsafe_allow_html=True)

        st.markdown("---")
        run_scan = st.button("🚀 Run Full Scan", type="primary", use_container_width=True)
        st.caption(f"~{len(selected_outlets)*3//concurrency}–{len(selected_outlets)*6//concurrency}s estimated")

    # ── Tabs ─────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview",
        "⚖️ Bias & Alignment",
        "📢 Narratives",
        "⚠️ Threats",
        "🔮 Prediction",
        "🔬 Raw Data"
    ])

    # ── Scan ─────────────────────────────────────────────────
    if run_scan and selected_outlets:
        with st.spinner(f"🚀 Launching {concurrency} concurrent scrapers across {len(selected_outlets)} outlets..."):
            progress_bar = st.progress(0, "Starting...")
            start = time.time()

            # Run the async scraper engine
            raw_results = run_scraper(selected_outlets, concurrency=concurrency)

            progress_bar.progress(0.7, "Analyzing intelligence...")
            results = [analyze_outlet_results(r) for r in raw_results]

            progress_bar.progress(1.0, "Done!")
            progress_bar.empty()

            elapsed = round(time.time() - start, 1)
            st.session_state["results"] = results
            st.session_state["scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        success_count = sum(1 for r in results if r["status"] == "success")
        total_hl = sum(r["count"] for r in results if r["status"] == "success")
        st.success(f"✅ Scan complete in **{elapsed}s** — {success_count}/{len(results)} outlets · {total_hl} headlines scraped")

        # Tier breakdown
        tier_counts = Counter(r.get("tier", "Failed") for r in results)
        cols = st.columns(4)
        cols[0].metric("⚡ Tier1 (aiohttp)",    tier_counts.get("Tier1 (aiohttp)", 0))
        cols[1].metric("🎭 Tier2 (Playwright)", tier_counts.get("Tier2 (Playwright)", 0))
        cols[2].metric("🥷 Tier3 (Stealth)",    tier_counts.get("Tier3 (Stealth)", 0))
        cols[3].metric("❌ Failed",              tier_counts.get("Failed", 0))

    results = st.session_state.get("results", [])
    if not results:
        st.info("👆 Select categories and click **Run Full Scan** to begin.")
        return

    successful = [r for r in results if r["status"] == "success"]
    failed     = [r for r in results if r["status"] == "failed"]

    # Apply filters
    filtered = successful
    if party_filter != "All":
        filtered = [r for r in successful if r.get("dominant_party") == party_filter]
    if threat_filter != "All":
        filtered = [r for r in filtered if r.get("threat_level") == threat_filter]

    # ── TAB 1: Overview ───────────────────────────────────────
    with tab1:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📡 Outlets",         len(results))
        c2.metric("✅ Success",          len(successful))
        c3.metric("📰 Headlines",        sum(r["count"] for r in successful))
        c4.metric("🚨 High Threat",      sum(1 for r in successful if r["threat_level"] == "HIGH"))
        c5.metric("⏰ Last Scan",        st.session_state.get("scan_time", "—")[-8:])

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🌡️ Sentiment Distribution")
            rows = []
            for r in filtered:
                dist = r.get("sentiment_dist", {})
                total = sum(dist.values()) or 1
                rows.append({
                    "Outlet":      r["name"],
                    "Positive %":  round(dist.get("Positive", 0) / total * 100, 1),
                    "Neutral %":   round(dist.get("Neutral", 0)  / total * 100, 1),
                    "Negative %":  round(dist.get("Negative", 0) / total * 100, 1),
                })
            if rows:
                df = pd.DataFrame(rows)
                fig = px.bar(
                    df.melt(id_vars="Outlet", var_name="Sentiment", value_name="Percent"),
                    x="Percent", y="Outlet", color="Sentiment", orientation="h",
                    color_discrete_map={"Positive %": "#16a34a", "Neutral %": "#6b7280", "Negative %": "#dc2626"},
                )
                fig.update_layout(barmode="stack", height=max(300, len(rows) * 28))
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📊 Narrative Theme Distribution")
            theme_agg = Counter()
            for r in filtered:
                for t, c in r.get("narrative_themes", {}).items():
                    theme_agg[t] += c
            if theme_agg:
                df_t = pd.DataFrame(theme_agg.items(), columns=["Theme", "Mentions"])
                fig2 = px.pie(df_t, values="Mentions", names="Theme",
                              color_discrete_sequence=px.colors.qualitative.Bold)
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📋 Full Outlet Summary")
        tbl = []
        for r in filtered:
            tbl.append({
                "Media":          r["name"],
                "Category":       r["category"].replace("_", " ").title(),
                "Headlines":      r["count"],
                "Sentiment":      round(r.get("avg_polarity", 0), 3),
                "Dominant Party": r.get("dominant_party") or "—",
                "Theme":          r.get("dominant_theme", "—"),
                "Threat":         r.get("threat_level", "—"),
                "Scraper Tier":   r.get("tier", "—"),
                "Time (s)":       r.get("elapsed_sec", "—"),
            })
        if tbl:
            df_tbl = pd.DataFrame(tbl)
            st.dataframe(
                df_tbl.style
                .applymap(lambda v: "background:#fee2e2;font-weight:bold" if v == "HIGH"
                          else ("background:#fef3c7" if v == "MEDIUM" else ""), subset=["Threat"])
                .background_gradient(subset=["Sentiment"], cmap="RdYlGn", vmin=-1, vmax=1),
                use_container_width=True, height=380
            )

        if failed:
            with st.expander(f"❌ {len(failed)} failed outlets"):
                for r in failed:
                    st.write(f"• **{r['name']}** — `{r['website']}`")

    # ── TAB 2: Bias & Alignment ───────────────────────────────
    with tab2:
        st.subheader("⚖️ Media Bias & Party Alignment")

        # Heatmap
        matrix = defaultdict(lambda: defaultdict(int))
        for r in successful:
            for p, s in r.get("party_bias", {}).items():
                matrix[r["name"]][p] += s

        if matrix:
            mdf = pd.DataFrame(matrix).T.fillna(0)
            if not mdf.empty:
                fig_h = px.imshow(mdf, title="Media × Party Coverage Heatmap",
                                  color_continuous_scale="Blues", aspect="auto",
                                  labels=dict(color="Mentions"))
                fig_h.update_layout(height=max(400, len(mdf) * 28))
                st.plotly_chart(fig_h, use_container_width=True)

        st.subheader("🎯 Party Alignment Cards")
        cols = st.columns(3)
        for i, r in enumerate(successful):
            party = r.get("dominant_party") or "—"
            color = PARTY_COLORS.get(party, "#6b7280")
            icon  = "😊" if r.get("avg_polarity", 0) > 0.1 else ("😠" if r.get("avg_polarity", 0) < -0.1 else "😐")
            tl    = r.get("threat_level", "LOW")
            ti    = "🔴" if tl == "HIGH" else ("🟡" if tl == "MEDIUM" else "🟢")
            tier  = r.get("tier", "—")
            with cols[i % 3]:
                st.markdown(f"""
                <div class="outlet-card" style="border-left:5px solid {color};">
                    <b>{r['name']}</b><br/>
                    <span style="color:{color}; font-size:0.85rem;">▶ {party}</span><br/>
                    <span style="font-size:0.78rem; color:#6b7280;">
                        {icon} {r.get('avg_polarity',0):+.2f} &nbsp;|&nbsp; {ti} {tl}
                        &nbsp;|&nbsp; 📰 {r['count']} hl
                    </span><br/>
                    <span style="font-size:0.72rem; color:#9ca3af;">Scraper: {tier}</span>
                </div>
                """, unsafe_allow_html=True)

        st.subheader("📈 Overall Party Mention Count")
        overall = Counter()
        for r in successful:
            for p, s in r.get("party_bias", {}).items():
                overall[p] += s
        if overall:
            df_p = pd.DataFrame(overall.items(), columns=["Party", "Mentions"]).sort_values("Mentions")
            fig_p = px.bar(df_p, x="Mentions", y="Party", orientation="h",
                           color="Party", color_discrete_map=PARTY_COLORS,
                           title="Total Party Mentions Across All Media")
            st.plotly_chart(fig_p, use_container_width=True)

    # ── TAB 3: Narratives ─────────────────────────────────────
    with tab3:
        st.subheader("📢 Emerging Narrative Detection")
        st.caption("৩+ মিডিয়া একই phrase push করলে → COORDINATED হিসেবে চিহ্নিত")

        narratives = detect_narratives(successful)
        if narratives:
            col1, col2 = st.columns([2, 1])
            with col1:
                for n in narratives:
                    badge = "🔴 COORDINATED" if n["coordinated"] else "🟡 ORGANIC"
                    st.markdown(f"""
                    <div class="narrative-box">
                        <b>"{n['phrase']}"</b>
                        &nbsp;<span style="background:#7c3aed;color:white;padding:2px 8px;border-radius:10px;font-size:0.78rem;">{n['theme']}</span>
                        &nbsp;<span style="font-size:0.8rem;">{badge}</span><br/>
                        <span style="color:#6b7280;font-size:0.82rem;">
                            {n['source_count']} outlets · {n['count']} mentions
                        </span><br/>
                        <span style="font-size:0.78rem;">📰 {' · '.join(n['sources'])}</span>
                    </div>
                    """, unsafe_allow_html=True)

            with col2:
                coord = sum(1 for n in narratives if n["coordinated"])
                st.metric("🔴 Coordinated", coord)
                st.metric("📢 Total Detected", len(narratives))
                st.metric("📰 Outlets Involved", len(set(s for n in narratives for s in n["sources"])))
                tc = Counter(n["theme"] for n in narratives)
                dftc = pd.DataFrame(tc.items(), columns=["Theme", "Count"])
                fig_tc = px.pie(dftc, values="Count", names="Theme", title="By Theme",
                                color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_tc, use_container_width=True)
        else:
            st.info("More outlets needed to detect narratives.")

        st.markdown("---")
        st.subheader("🔍 Cross-Media Headline Search")
        q = st.text_input("Search term", placeholder="e.g. নির্বাচন / election / bnp / yunus")
        if q:
            matches = [
                {"Source": r["name"], "Tier": r.get("tier","—"), "Headline": h}
                for r in successful for h in r.get("headlines", [])
                if q.lower() in h.lower()
            ]
            st.write(f"**{len(matches)} results found**")
            if matches:
                st.dataframe(pd.DataFrame(matches), use_container_width=True)

    # ── TAB 4: Threats ────────────────────────────────────────
    with tab4:
        st.subheader("⚠️ Threat Intelligence")
        signals = detect_threats(successful)

        if signals:
            st.error(f"🚨 {len(signals)} threat signal(s) detected!")
            for ts in signals:
                st.markdown(f"""
                <div class="threat-card">
                    <b>🔴 {ts['type']}</b><br/>
                    {ts['detail']}<br/>
                    <span style="font-size:0.82rem; color:#6b7280;">
                        Outlets: {', '.join(ts['outlets'])}
                    </span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No coordinated threat campaigns detected.")

        st.markdown("---")
        st.subheader("📊 Threat Score by Outlet")
        td = sorted(
            [{"Outlet": r["name"], "Score": r.get("threat_score", 0), "Level": r.get("threat_level","LOW")}
             for r in successful], key=lambda x: x["Score"], reverse=True
        )
        if threat_filter != "All":
            td = [t for t in td if t["Level"] == threat_filter]
        if td:
            df_td = pd.DataFrame(td)
            fig_td = px.bar(df_td, x="Outlet", y="Score", color="Level",
                            color_discrete_map={"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#16a34a"},
                            title="Threat Score by Outlet")
            fig_td.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(fig_td, use_container_width=True)

        st.subheader("🔑 Top Threat Keywords")
        kw_hits = Counter()
        for r in successful:
            for a in r.get("analyzed_headlines", []):
                for kw in a.get("threat_hits", []):
                    kw_hits[kw] += 1
        if kw_hits:
            df_kw = pd.DataFrame(kw_hits.most_common(15), columns=["Keyword", "Count"])
            fig_kw = px.bar(df_kw, x="Count", y="Keyword", orientation="h",
                            color="Count", color_continuous_scale="Reds")
            st.plotly_chart(fig_kw, use_container_width=True)

    # ── TAB 5: Prediction ─────────────────────────────────────
    with tab5:
        st.subheader("🔮 Predictive Political Intelligence")
        st.caption("বর্তমান media signal বিশ্লেষণ করে আগামী ২–৪ সপ্তাহের পূর্বাভাস")

        preds = predict_issues(successful)
        for i, p in enumerate(preds, 1):
            intensity = p["intensity"]
            color = "#dc2626" if intensity >= 70 else ("#d97706" if intensity >= 40 else "#16a34a")
            st.markdown(f"""
            <div class="predict-card" style="border-left:6px solid {color};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="font-size:1.05rem;">#{i} {p['theme']}</b>
                    <span style="background:{color}; color:white; padding:4px 12px;
                                 border-radius:12px; font-size:0.82rem; font-weight:bold;">
                        {intensity}% Signal
                    </span>
                </div>
                <p style="margin:8px 0 0 0; color:#374151;">{p['prediction']}</p>
                <span style="font-size:0.78rem; color:#9ca3af;">Media mentions: {p['count']}</span>
            </div>
            """, unsafe_allow_html=True)

        if preds:
            st.markdown("---")
            df_p = pd.DataFrame(preds)
            fig_p = px.bar(df_p, x="theme", y="intensity",
                           color="intensity", color_continuous_scale="RdYlGn_r",
                           title="Predicted Issue Intensity (Next 2–4 Weeks)",
                           labels={"theme": "Political Theme", "intensity": "Signal Strength (%)"})
            fig_p.update_layout(showlegend=False)
            st.plotly_chart(fig_p, use_container_width=True)

    # ── TAB 6: Raw Data ───────────────────────────────────────
    with tab6:
        st.subheader("🔬 Raw Scrape Data")
        for r in results:
            status_icon = "✅" if r["status"] == "success" else "❌"
            tier_class = {
                "Tier1 (aiohttp)":    "tier1",
                "Tier2 (Playwright)": "tier2",
                "Tier3 (Stealth)":    "tier3",
            }.get(r.get("tier",""), "tierfail")

            with st.expander(f"{status_icon} {r['name']} — {r['count']} headlines — {r.get('elapsed_sec','?')}s"):
                st.markdown(f"""
                <span class="tier-badge {tier_class}">{r.get('tier','Failed')}</span>
                &nbsp; URL: <code>{r.get('url','—')}</code>
                """, unsafe_allow_html=True)
                if r["headlines"]:
                    for hl in r["headlines"][:20]:
                        st.write(f"• {hl}")
                    if len(r["headlines"]) > 20:
                        st.caption(f"... এবং আরো {len(r['headlines'])-20}টি")
                else:
                    st.warning("No headlines scraped.")

        st.markdown("---")
        if st.button("📥 Download Full JSON"):
            st.download_button(
                label="Download Results",
                data=json.dumps(
                    [{k: v for k, v in r.items() if k != "analyzed_headlines"} for r in results],
                    ensure_ascii=False, indent=2
                ),
                file_name=f"media_intel_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )


if __name__ == "__main__":
    main()
