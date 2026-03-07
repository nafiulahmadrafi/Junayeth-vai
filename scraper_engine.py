"""
╔══════════════════════════════════════════════════════════════╗
║   SCRAPER ENGINE v4.0 — ULTRA ADVANCED                       ║
║   Political Media Intelligence System                        ║
║   Full Article Scraping: Title + Body + Meta                 ║
╠══════════════════════════════════════════════════════════════╣
║  TIER 1  ⚡  aiohttp + BeautifulSoup   (lightweight/fast)    ║
║  TIER 2  🎭  Playwright async          (JS-rendered)         ║
║  TIER 3  🥷  Playwright stealth        (anti-bot bypass)     ║
║  TIER 4  📡  Google News RSS           (reliable fallback)   ║
║  TIER 5  📰  Direct RSS/Atom feed      (last resort)         ║
╠══════════════════════════════════════════════════════════════╣
║  94+ outlets | BD TV · BD Newspapers · India · Intl · Asia  ║
║  Each article: title + full_text + summary + url + time     ║
╚══════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
import random
import logging
import json
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urljoin, quote_plus

# ── Optional dependency guards ────────────────────────────
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger("scraper_engine")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# ============================================================
# ARTICLE DATA STRUCTURE
# ============================================================

def _empty_article(url: str = "", title: str = "") -> dict:
    """Return a blank article skeleton."""
    return {
        "title":        title,
        "url":          url,
        "summary":      "",
        "full_text":    "",
        "published_at": "",
        "author":       "",
        "image_url":    "",
        "tags":         [],
        "word_count":   0,
        "scraped_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ============================================================
# SITE SELECTORS — Title · Article links · Content · Meta
# ============================================================
# headline_sel   : CSS selectors for article titles on homepage
# link_sel       : CSS selectors to extract article URLs
# content_sel    : CSS selectors for full article body
# summary_sel    : CSS selectors for article summary/lead
# author_sel     : CSS selectors for author name
# date_sel       : CSS selectors for publish date
# image_sel      : CSS selectors for lead image
# rss            : Direct RSS/Atom feed URL
# tier           : Preferred scrape tier (1/2/3)
# article_tier   : Tier for individual article scraping

SITE_SELECTORS: dict[str, dict] = {

    # ══════════════════════════════════════════════════════
    # BANGLADESH TV CHANNELS
    # ══════════════════════════════════════════════════════

    "somoynews.tv": {
        "headline_sel": ["h3.title a", "h2.title a", ".news-title a", ".card-title a", "h3 a"],
        "link_sel":     ["h3.title a", "h2.title a", ".news-title a", ".card-title a", "h3 a"],
        "content_sel":  [".details-body p", ".news-details p", ".article-content p", ".entry-content p", "article p"],
        "summary_sel":  [".details-lead", ".news-lead", ".article-summary", ".excerpt", "p.intro"],
        "author_sel":   [".reporter-name", ".author-name", ".byline", ".writer"],
        "date_sel":     [".news-time", ".publish-time", "time", ".date", ".post-date"],
        "image_sel":    [".details-img img", ".news-img img", "article img", ".featured-img img"],
        "rss":          "https://www.somoynews.tv/rss.xml",
        "tier":         2,
        "article_tier": 2,
    },
    "jamuna.tv": {
        "headline_sel": [".news-title a", "h3.title a", "h2 a", ".latest-news a", ".card-title a"],
        "link_sel":     [".news-title a", "h3.title a", ".card-title a", "h2 a"],
        "content_sel":  [".details-body p", ".news-body p", ".content-details p", "article p", ".entry-content p"],
        "summary_sel":  [".news-lead", ".article-excerpt", ".summary", "p.lead"],
        "author_sel":   [".reporter", ".author", ".byline", ".written-by"],
        "date_sel":     ["time", ".publish-date", ".news-time", ".date-time"],
        "image_sel":    [".news-details img", "article img", ".thumb img"],
        "rss":          "https://www.jamuna.tv/feed",
        "tier":         2,
        "article_tier": 2,
    },
    "channel24bd.tv": {
        "headline_sel": ["h3 a", ".news-card-title a", ".top-news-title a", "h2 a", ".headline a"],
        "link_sel":     ["h3 a", ".news-card-title a", ".top-news-title a", "h2 a"],
        "content_sel":  [".details-content p", ".news-content p", ".article-body p", "article p"],
        "summary_sel":  [".lead-para", ".article-lead", ".intro-text", "p.summary"],
        "author_sel":   [".author-name", ".reporter", ".byline"],
        "date_sel":     ["time", ".publish-time", ".article-time", ".date"],
        "image_sel":    ["article img.featured", ".news-thumb img", "article img"],
        "rss":          "https://www.channel24bd.tv/feed",
        "tier":         2,
        "article_tier": 2,
    },
    "ekattor.tv": {
        "headline_sel": [".title a", "h3 a", ".news-item a", "h2 a", ".article-title a"],
        "link_sel":     [".title a", "h3 a", ".news-item a", "h2 a"],
        "content_sel":  [".entry-content p", ".post-content p", "article p", ".news-body p"],
        "summary_sel":  [".entry-summary", ".post-excerpt", ".lead"],
        "author_sel":   [".author", ".byline", ".writer-name"],
        "date_sel":     ["time", ".entry-date", ".published", ".date"],
        "image_sel":    [".entry-content img", "article img", ".post-thumbnail img"],
        "rss":          "https://ekattor.tv/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "independent24.com": {
        "headline_sel": ["h3 a", ".news-title a", ".card-title a", "h2 a", ".headline-text a"],
        "link_sel":     ["h3 a", ".news-title a", ".card-title a", "h2 a"],
        "content_sel":  [".entry-content p", ".post-body p", "article p", ".news-details p"],
        "summary_sel":  [".excerpt", ".post-excerpt", ".lead", ".summary"],
        "author_sel":   [".author-name", ".byline", ".reporter"],
        "date_sel":     ["time", ".post-date", ".publish-date", ".date"],
        "image_sel":    ["article img", ".post-thumbnail img", ".featured-image img"],
        "rss":          "https://www.independent24.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "ntvbd.com": {
        "headline_sel": [".news-title a", "h3 a", ".title-link", "h2.post-title a", ".card-title a"],
        "link_sel":     [".news-title a", "h3 a", ".title-link", "h2.post-title a"],
        "content_sel":  [".details-text p", ".article-text p", ".entry-content p", "article p"],
        "summary_sel":  [".news-summary", ".article-lead", ".excerpt"],
        "author_sel":   [".reporter-name", ".author", ".byline"],
        "date_sel":     ["time", ".date", ".news-date", ".publish-time"],
        "image_sel":    [".news-details img", ".article-image img", "article img"],
        "rss":          "https://www.ntvbd.com/rss",
        "tier":         1,
        "article_tier": 1,
    },
    "channelionline.com": {
        "headline_sel": ["h3 a", ".news-heading a", ".title a", "h2 a", ".post-title a"],
        "link_sel":     ["h3 a", ".news-heading a", ".title a", "h2 a"],
        "content_sel":  [".post-content p", ".entry-content p", "article p", ".news-content p"],
        "summary_sel":  [".post-excerpt", ".entry-summary", ".lead-text"],
        "author_sel":   [".author", ".byline", ".post-author"],
        "date_sel":     ["time", ".post-date", ".published-date"],
        "image_sel":    [".post-thumbnail img", "article img", ".featured img"],
        "rss":          "https://www.channelionline.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "atnnewsltd.com": {
        "headline_sel": ["h3 a", ".news-title a", "h2 a", ".article-title a", ".headline a"],
        "link_sel":     ["h3 a", ".news-title a", "h2 a", ".article-title a"],
        "content_sel":  ["article p", ".content p", ".news-body p", ".entry-content p"],
        "summary_sel":  [".summary", ".lead", ".excerpt"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date", ".published"],
        "image_sel":    ["article img", ".featured-img img"],
        "rss":          None,
        "tier":         2,
        "article_tier": 2,
    },
    "dbcnews.tv": {
        "headline_sel": [".title a", "h3 a", ".news-card a", "h2 a", ".story-title a"],
        "link_sel":     [".title a", "h3 a", ".news-card a", "h2 a"],
        "content_sel":  [".article-body p", ".news-body p", ".content-text p", "article p"],
        "summary_sel":  [".article-summary", ".news-lead", ".intro"],
        "author_sel":   [".reporter", ".author-name", ".byline"],
        "date_sel":     ["time", ".date", ".news-time"],
        "image_sel":    ["article img", ".news-img img"],
        "rss":          "https://www.dbcnews.tv/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "news24bd.tv": {
        "headline_sel": ["h3 a", ".news-title a", ".top-news a", "h2 a", ".breaking a"],
        "link_sel":     ["h3 a", ".news-title a", ".top-news a", "h2 a"],
        "content_sel":  [".details-content p", ".news-content p", "article p", ".post-content p"],
        "summary_sel":  [".news-lead", ".article-summary", ".lead"],
        "author_sel":   [".reporter-name", ".author", ".byline"],
        "date_sel":     ["time", ".publish-date", ".date"],
        "image_sel":    ["article img", ".details-img img"],
        "rss":          "https://www.news24bd.tv/rss",
        "tier":         1,
        "article_tier": 1,
    },
    "rtvonline.com": {
        "headline_sel": [".news-title a", "h3 a", "h2 a", ".article-title a", ".card-title a"],
        "link_sel":     [".news-title a", "h3 a", "h2 a", ".article-title a"],
        "content_sel":  [".news-details p", ".article-content p", "article p", ".entry-content p"],
        "summary_sel":  [".news-intro", ".article-lead", ".summary"],
        "author_sel":   [".reporter", ".byline", ".author-name"],
        "date_sel":     ["time", ".publish-time", ".date"],
        "image_sel":    [".news-img img", "article img"],
        "rss":          "https://www.rtvonline.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "bvnews24.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".headline-text a"],
        "link_sel":     ["h3 a", ".title a", ".news-title a", "h2 a"],
        "content_sel":  [".entry-content p", ".post-content p", "article p"],
        "summary_sel":  [".excerpt", ".entry-summary", ".lead"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date", ".post-date"],
        "image_sel":    [".featured img", "article img"],
        "rss":          "https://www.bvnews24.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "ekushey-tv.com": {
        "headline_sel": [".news-title a", "h3 a", "h2 a", ".post-title a", ".card-title a"],
        "link_sel":     [".news-title a", "h3 a", "h2 a", ".post-title a"],
        "content_sel":  [".entry-content p", ".post-content p", "article p"],
        "summary_sel":  [".entry-summary", ".excerpt"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date", ".published"],
        "image_sel":    ["article img", ".post-thumbnail img"],
        "rss":          "https://ekushey-tv.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "maasranga.tv": {
        "headline_sel": ["h3 a", ".title a", ".news-item-title a", "h2 a", ".article a"],
        "link_sel":     ["h3 a", ".title a", ".news-item-title a", "h2 a"],
        "content_sel":  ["article p", ".news-content p", ".details-text p", ".entry-content p"],
        "summary_sel":  [".lead", ".summary", ".intro"],
        "author_sel":   [".reporter", ".author", ".byline"],
        "date_sel":     ["time", ".date", ".news-date"],
        "image_sel":    ["article img", ".thumb img"],
        "rss":          "https://www.maasranga.tv/feed",
        "tier":         2,
        "article_tier": 2,
    },
    "btv.gov.bd": {
        "headline_sel": ["h3 a", ".news-title a", "h2 a", ".headline a", ".article-title a"],
        "link_sel":     ["h3 a", ".news-title a", "h2 a"],
        "content_sel":  [".entry-content p", "article p", ".news-body p"],
        "summary_sel":  [".excerpt", ".summary"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img", ".featured img"],
        "rss":          None,
        "tier":         1,
        "article_tier": 1,
    },
    "boishakhionline.com": {
        "headline_sel": [".news-title a", "h3 a", "h2 a", ".article-title a", ".card-title a"],
        "link_sel":     [".news-title a", "h3 a", "h2 a"],
        "content_sel":  [".entry-content p", ".post-content p", "article p"],
        "summary_sel":  [".excerpt", ".lead"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date", ".post-date"],
        "image_sel":    ["article img", ".featured img"],
        "rss":          "https://www.boishakhionline.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "desh.tv": {
        "headline_sel": ["h3 a", ".title a", ".news-card-title a", "h2 a", ".headline a"],
        "link_sel":     ["h3 a", ".title a", ".news-card-title a", "h2 a"],
        "content_sel":  ["article p", ".news-content p", ".details-body p"],
        "summary_sel":  [".news-lead", ".summary", ".intro"],
        "author_sel":   [".reporter", ".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.desh.tv/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "nagorik.tv": {
        "headline_sel": ["h3 a", ".news-title a", "h2 a", ".post-title a", ".card-title a"],
        "link_sel":     ["h3 a", ".news-title a", "h2 a"],
        "content_sel":  ["article p", ".entry-content p", ".post-content p"],
        "summary_sel":  [".excerpt", ".lead"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          None,
        "tier":         2,
        "article_tier": 2,
    },
    "globaltvbd.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".article-title a"],
        "link_sel":     ["h3 a", ".title a", ".news-title a", "h2 a"],
        "content_sel":  ["article p", ".news-content p", ".entry-content p"],
        "summary_sel":  [".lead", ".summary"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          None,
        "tier":         2,
        "article_tier": 2,
    },
    "asiantvonline.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a"],
        "link_sel":     ["h3 a", ".title a", "h2 a"],
        "content_sel":  ["article p", ".entry-content p"],
        "summary_sel":  [".excerpt", ".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          None,
        "tier":         1,
        "article_tier": 1,
    },

    # ══════════════════════════════════════════════════════
    # BANGLADESH NEWSPAPERS
    # ══════════════════════════════════════════════════════

    "prothomalo.com": {
        "headline_sel": ["h3.title a", ".story-card__title a", "h2 a", ".headline-text a", "h3 a"],
        "link_sel":     ["h3.title a", ".story-card__title a", "h2 a"],
        "content_sel":  [".story-element-text p", ".article-text p", ".palo-content p", "article p"],
        "summary_sel":  [".story-element-text-summary", ".article-summary", ".lead"],
        "author_sel":   [".reporter-name a", ".author-name", ".byline-name"],
        "date_sel":     ["time", ".story-time", ".publish-date"],
        "image_sel":    [".story-element-image img", "article img"],
        "rss":          "https://www.prothomalo.com/feed",
        "tier":         2,
        "article_tier": 2,
    },
    "bd-pratidin.com": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".post-title a"],
        "link_sel":     [".title a", "h3 a", "h2 a", ".news-title a"],
        "content_sel":  [".details-body p", ".news-details p", "article p", ".content p"],
        "summary_sel":  [".news-lead", ".summary", ".intro-text"],
        "author_sel":   [".reporter-name", ".author", ".byline"],
        "date_sel":     ["time", ".date", ".publish-time"],
        "image_sel":    [".news-details img", "article img"],
        "rss":          "https://www.bd-pratidin.com/rss",
        "tier":         1,
        "article_tier": 1,
    },
    "jugantor.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".headline a"],
        "link_sel":     ["h3 a", ".title a", ".news-title a", "h2 a"],
        "content_sel":  [".news-body p", ".article-content p", "article p", ".entry-content p"],
        "summary_sel":  [".news-summary", ".lead", ".excerpt"],
        "author_sel":   [".reporter", ".author-name", ".byline"],
        "date_sel":     ["time", ".news-date", ".published-date"],
        "image_sel":    [".news-details img", "article img", ".featured-img img"],
        "rss":          "https://www.jugantor.com/rss",
        "tier":         1,
        "article_tier": 1,
    },
    "kalerkantho.com": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".headline a"],
        "link_sel":     [".title a", "h3 a", "h2 a", ".news-title a"],
        "content_sel":  [".detail-body p", ".article-text p", "article p", ".content-area p"],
        "summary_sel":  [".detail-summary", ".article-lead", ".news-intro"],
        "author_sel":   [".reporter", ".author", ".byline-name"],
        "date_sel":     ["time", ".news-time", ".date"],
        "image_sel":    [".detail-photo img", "article img"],
        "rss":          "https://www.kalerkantho.com/rss.xml",
        "tier":         1,
        "article_tier": 1,
    },
    "ittefaq.com.bd": {
        "headline_sel": ["h3 a", ".news-title a", "h2 a", ".title a", ".story-title a"],
        "link_sel":     ["h3 a", ".news-title a", "h2 a", ".title a"],
        "content_sel":  [".article-detail p", ".news-content p", "article p"],
        "summary_sel":  [".article-intro", ".news-lead", ".summary"],
        "author_sel":   [".author-name", ".reporter", ".byline"],
        "date_sel":     ["time", ".date", ".publish-time"],
        "image_sel":    ["article img", ".article-image img"],
        "rss":          "https://www.ittefaq.com.bd/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "samakal.com": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".card-title a"],
        "link_sel":     [".title a", "h3 a", "h2 a", ".news-title a"],
        "content_sel":  [".article-body p", ".news-article p", "article p", ".content p"],
        "summary_sel":  [".article-summary", ".lead-text", ".intro"],
        "author_sel":   [".reporter-name", ".byline", ".author"],
        "date_sel":     ["time", ".article-time", ".date"],
        "image_sel":    ["article img", ".article-img img"],
        "rss":          "https://samakal.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "dainikamadershomoy.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".post-title a"],
        "link_sel":     ["h3 a", ".title a", ".news-title a", "h2 a"],
        "content_sel":  [".entry-content p", ".post-content p", "article p"],
        "summary_sel":  [".excerpt", ".entry-summary", ".lead"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".post-date", ".date"],
        "image_sel":    ["article img", ".post-thumbnail img"],
        "rss":          "https://www.dainikamadershomoy.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "dailyjanakantha.com": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".headline a"],
        "link_sel":     [".title a", "h3 a", "h2 a", ".news-title a"],
        "content_sel":  [".details-body p", ".article-content p", "article p"],
        "summary_sel":  [".news-lead", ".article-summary", ".intro"],
        "author_sel":   [".reporter", ".author-name", ".byline"],
        "date_sel":     ["time", ".date", ".news-date"],
        "image_sel":    ["article img", ".news-img img"],
        "rss":          "https://www.dailyjanakantha.com/rss",
        "tier":         1,
        "article_tier": 1,
    },
    "mzamin.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".post-title a"],
        "link_sel":     ["h3 a", ".title a", ".news-title a", "h2 a"],
        "content_sel":  [".entry-content p", ".article-body p", "article p"],
        "summary_sel":  [".excerpt", ".lead"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://mzamin.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "dailynayadiganta.com": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".headline a"],
        "link_sel":     [".title a", "h3 a", "h2 a"],
        "content_sel":  [".news-body p", ".article-text p", "article p"],
        "summary_sel":  [".news-lead", ".summary"],
        "author_sel":   [".reporter", ".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.dailynayadiganta.com/rss",
        "tier":         1,
        "article_tier": 1,
    },
    "bhorerkagoj.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".card-title a"],
        "link_sel":     ["h3 a", ".title a", ".news-title a", "h2 a"],
        "content_sel":  [".entry-content p", ".post-content p", "article p"],
        "summary_sel":  [".excerpt", ".lead"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.bhorerkagoj.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "dailyinqilab.com": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".post-title a"],
        "link_sel":     [".title a", "h3 a", "h2 a"],
        "content_sel":  ["article p", ".entry-content p", ".news-content p"],
        "summary_sel":  [".excerpt", ".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.dailyinqilab.com/rss",
        "tier":         1,
        "article_tier": 1,
    },
    "jaijaidinbd.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".headline a"],
        "link_sel":     ["h3 a", ".title a", "h2 a"],
        "content_sel":  [".entry-content p", ".article-body p", "article p"],
        "summary_sel":  [".excerpt", ".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.jaijaidinbd.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "sangbad.net.bd": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".post-title a"],
        "link_sel":     [".title a", "h3 a", "h2 a"],
        "content_sel":  ["article p", ".entry-content p"],
        "summary_sel":  [".excerpt"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://sangbad.net.bd/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "ajkerpatrika.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".card-title a"],
        "link_sel":     ["h3 a", ".title a", "h2 a"],
        "content_sel":  ["article p", ".news-content p", ".entry-content p"],
        "summary_sel":  [".lead", ".excerpt"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.ajkerpatrika.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "kalbela.com": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".headline a"],
        "link_sel":     [".title a", "h3 a", "h2 a"],
        "content_sel":  [".details-content p", ".article-text p", "article p"],
        "summary_sel":  [".news-lead", ".intro"],
        "author_sel":   [".reporter", ".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://kalbela.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "bonikbarta.net": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".post-title a"],
        "link_sel":     ["h3 a", ".title a", "h2 a"],
        "content_sel":  [".entry-content p", "article p", ".post-content p"],
        "summary_sel":  [".excerpt", ".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://bonikbarta.net/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "deshrupantor.com": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".card-title a"],
        "link_sel":     [".title a", "h3 a", "h2 a"],
        "content_sel":  ["article p", ".entry-content p", ".news-body p"],
        "summary_sel":  [".lead", ".excerpt"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://deshrupantor.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "alokitobangladesh.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a", ".headline a"],
        "link_sel":     ["h3 a", ".title a", "h2 a"],
        "content_sel":  ["article p", ".entry-content p"],
        "summary_sel":  [".lead", ".excerpt"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.alokitobangladesh.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "dainikbangla.com.bd": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a", ".post-title a"],
        "link_sel":     [".title a", "h3 a", "h2 a"],
        "content_sel":  ["article p", ".entry-content p", ".news-content p"],
        "summary_sel":  [".lead", ".excerpt"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://dainikbangla.com.bd/feed",
        "tier":         1,
        "article_tier": 1,
    },

    # ══════════════════════════════════════════════════════
    # INDIAN NEWS OUTLETS
    # ══════════════════════════════════════════════════════

    "timesofindia.indiatimes.com": {
        "headline_sel": ["figcaption.caption a", "h3.w_tle a", "span.w_tle", "h2 a", ".news-card-title a"],
        "link_sel":     ["figcaption.caption a", "h3.w_tle a", "h2 a"],
        "content_sel":  ["div._s30J p", "div.ga4G3p p", "article p", "div[class*='articleText'] p"],
        "summary_sel":  ["p._3HHqE", ".article-intro", ".summary"],
        "author_sel":   [".author", ".byline", "span._2byYu"],
        "date_sel":     ["time", "span.ZxBIG", ".article-time"],
        "image_sel":    ["article img", ".article-image img"],
        "rss":          "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "tier":         3,
        "article_tier": 3,
    },
    "ndtv.com": {
        "headline_sel": [".news_Itm-title", "h2 a", ".NwSLstPg_ttl", ".article__heading a", "h3 a"],
        "link_sel":     [".news_Itm-title", "h2 a", ".NwSLstPg_ttl a"],
        "content_sel":  [".sp-cn p", "div.Art_KV3s p", ".article__content p", "article p"],
        "summary_sel":  [".article__intro", ".sp-smry", ".news-intro"],
        "author_sel":   [".author__name", ".byline__name", ".posted-by"],
        "date_sel":     ["time", ".article__time", "span._pubtime"],
        "image_sel":    ["article img", ".article__image img"],
        "rss":          "https://feeds.feedburner.com/ndtvnews-top-stories",
        "tier":         3,
        "article_tier": 3,
    },
    "hindustantimes.com": {
        "headline_sel": ["h3.hdg3 a", ".storycard__headline a", "h2 a", ".listingPage h3 a", "h3 a"],
        "link_sel":     ["h3.hdg3 a", ".storycard__headline a", "h2 a"],
        "content_sel":  ["div.storyDetails p", ".detail p", "article p", ".storyDetail p"],
        "summary_sel":  [".intro-txt", ".story-summary", ".lead"],
        "author_sel":   [".authorInformation", ".byline", ".author"],
        "date_sel":     ["time", ".datePublish", ".story-date"],
        "image_sel":    ["article img", ".storyImgCont img"],
        "rss":          "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "tier":         3,
        "article_tier": 3,
    },
    "thehindu.com": {
        "headline_sel": ["h3.title a", "h2.title a", ".story-card-33sq__title a", "h3 a", ".card-title a"],
        "link_sel":     ["h3.title a", "h2.title a", ".story-card-33sq__title a"],
        "content_sel":  ["div._3WrFV p", ".article p", "article p", ".paywall p"],
        "summary_sel":  [".intro", ".article-intro", "p.intro-para"],
        "author_sel":   [".author-name", ".byline-name", ".lft span"],
        "date_sel":     ["time", ".publish-time-new", ".update-time"],
        "image_sel":    ["article img", ".lead-img img"],
        "rss":          "https://www.thehindu.com/news/national/feeder/default.rss",
        "tier":         2,
        "article_tier": 2,
    },
    "indianexpress.com": {
        "headline_sel": ["h2.title a", "h3 a", ".articles h2 a", "h2 a"],
        "link_sel":     ["h2.title a", "h3 a", ".articles h2 a"],
        "content_sel":  ["div.story_details p", ".ie-content p", "article p"],
        "summary_sel":  [".story-intro", ".ie-intro", ".lead"],
        "author_sel":   [".ie-byline-name", ".author-name", ".byline"],
        "date_sel":     ["time", ".ie-updated-date", ".date-updated"],
        "image_sel":    ["article img", ".custom-caption img"],
        "rss":          "https://indianexpress.com/feed/",
        "tier":         2,
        "article_tier": 2,
    },
    "aajtak.in": {
        "headline_sel": [".story__title a", "h3 a", ".news-title a", "h2 a"],
        "link_sel":     [".story__title a", "h3 a", "h2 a"],
        "content_sel":  [".story-with-style p", ".field-items p", "article p"],
        "summary_sel":  [".story-intro", ".field-intro p"],
        "author_sel":   [".author-name", ".byline"],
        "date_sel":     ["time", ".story-date"],
        "image_sel":    ["article img"],
        "rss":          "https://feeds.feedburner.com/aajtak/fZAf",
        "tier":         3,
        "article_tier": 3,
    },
    "indiatoday.in": {
        "headline_sel": [".story__title a", "h2 a", ".listingNew h2 a", ".field-title a", "h3 a"],
        "link_sel":     [".story__title a", "h2 a", ".field-title a"],
        "content_sel":  [".story-with-style p", ".description p", "article p"],
        "summary_sel":  [".story-kicker", ".intro-text", ".lead"],
        "author_sel":   [".author-name", ".story__author"],
        "date_sel":     ["time", ".story-date"],
        "image_sel":    ["article img", ".media-element img"],
        "rss":          "https://www.indiatoday.in/rss/home",
        "tier":         3,
        "article_tier": 3,
    },
    "economictimes.indiatimes.com": {
        "headline_sel": ["h3.clr a", "figcaption a", ".eachStory h3 a", "h2 a"],
        "link_sel":     ["h3.clr a", "figcaption a", ".eachStory h3 a"],
        "content_sel":  [".artText p", ".article-body p", "article p"],
        "summary_sel":  [".summary", ".article-intro", ".lead"],
        "author_sel":   [".author-name", ".byline"],
        "date_sel":     ["time", ".publish_on", ".art_time"],
        "image_sel":    ["article img"],
        "rss":          "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "tier":         3,
        "article_tier": 3,
    },
    "news18.com": {
        "headline_sel": ["h3 a", ".jsx-story-list h3 a", ".top_story h3 a", "h2 a"],
        "link_sel":     ["h3 a", ".top_story h3 a", "h2 a"],
        "content_sel":  [".article-body p", ".story-content p", "article p"],
        "summary_sel":  [".article-intro", ".story-intro"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".story-date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.news18.com/rss/india.xml",
        "tier":         2,
        "article_tier": 2,
    },
    "livemint.com": {
        "headline_sel": ["h2.headline a", "h3 a", ".listingNew h2 a", ".storyCard__headline a", "h2 a"],
        "link_sel":     ["h2.headline a", "h3 a", ".storyCard__headline a"],
        "content_sel":  ["div.storyPage__content p", ".mint-content p", "article p"],
        "summary_sel":  [".storyPage__intro", ".story-summary"],
        "author_sel":   [".author-name", ".byline"],
        "date_sel":     ["time", ".storyDate"],
        "image_sel":    ["article img"],
        "rss":          "https://www.livemint.com/rss/news",
        "tier":         3,
        "article_tier": 3,
    },

    # ══════════════════════════════════════════════════════
    # INTERNATIONAL SOURCES
    # ══════════════════════════════════════════════════════

    "aljazeera.com": {
        "headline_sel": ["h3.article-card__title a", "h2 a", ".article-card a h3", "h3 a"],
        "link_sel":     ["h3.article-card__title a", "h2 a", ".article-card__title a"],
        "content_sel":  [".wysiwyg p", ".article-body p", "article p", "div[class*='article-p-wrapper'] p"],
        "summary_sel":  [".article-header__sub-title", ".article-intro", ".article__subline"],
        "author_sel":   [".article-author__name", ".author-link", ".author"],
        "date_sel":     ["time", ".date-simple span", ".article-dates__published"],
        "image_sel":    ["figure.article-featured-image img", "article img"],
        "rss":          "https://www.aljazeera.com/xml/rss/all.xml",
        "tier":         1,
        "article_tier": 1,
    },
    "bbc.com": {
        "headline_sel": ["h3[data-testid='card-headline']", "h2[data-testid='card-headline']", ".gs-c-promo-heading__title", "h3 a"],
        "link_sel":     ["h3[data-testid='card-headline']", "h2[data-testid='card-headline']", ".gs-c-promo-heading__title"],
        "content_sel":  ["article[data-component='text-block'] p", "div[data-component='text-block'] p", ".ssrcss-uf6wea p", "article p"],
        "summary_sel":  ["p[class*='Intro']", ".ssrcss-intro p", ".article-headline__intro"],
        "author_sel":   [".ssrcss-1pjc44a-Contributor", ".author", "[data-testid='byline-name']"],
        "date_sel":     ["time", "[data-testid='timestamp']"],
        "image_sel":    ["article img", "[data-testid='hero-image'] img"],
        "rss":          "http://feeds.bbci.co.uk/news/rss.xml",
        "tier":         2,
        "article_tier": 2,
    },
    "theguardian.com": {
        "headline_sel": ["h3.fc-item__title a", ".js-headline-text", "h3 a", "h2 a"],
        "link_sel":     ["h3.fc-item__title a", ".js-headline-text", "h3 a"],
        "content_sel":  ["div.article-body-commercial-selector p", ".dcr-1kas2f8 p", "article p"],
        "summary_sel":  ["div.dcr-standfirst p", ".standfirst p", ".article-intro"],
        "author_sel":   [".byline", ".contributor a", ".dcr-1kcl8ec"],
        "date_sel":     ["time", "[data-testid='date-line']"],
        "image_sel":    ["article img", "figure.dcr-f9dqld img"],
        "rss":          "https://www.theguardian.com/world/rss",
        "tier":         1,
        "article_tier": 1,
    },
    "reuters.com": {
        "headline_sel": ["a[data-testid='Heading']", "h3 a", ".story-title", "h2 a"],
        "link_sel":     ["a[data-testid='Heading']", ".story-title a", "h3 a"],
        "content_sel":  ["p[class*='article__paragraph']", ".article-body p", "article p"],
        "summary_sel":  ["p[class*='ArticleHeader_intro']", ".article-summary"],
        "author_sel":   [".author-name", ".byline", "[class*='byline']"],
        "date_sel":     ["time", "[class*='date']"],
        "image_sel":    ["article img", "[class*='image'] img"],
        "rss":          "https://feeds.reuters.com/reuters/topNews",
        "tier":         3,
        "article_tier": 3,
    },
    "apnews.com": {
        "headline_sel": [".PagePromo-title a", "h3 a", ".CardHeadline a", ".Component-headline a", "h2 a"],
        "link_sel":     [".PagePromo-title a", "h3 a", ".CardHeadline a"],
        "content_sel":  [".RichTextStoryBody p", ".Article p", "article p"],
        "summary_sel":  [".RichTextStoryBody p:first-child", ".article-intro"],
        "author_sel":   [".Component-bylines", ".byline"],
        "date_sel":     ["time", "[data-key='timestamp']"],
        "image_sel":    ["article img", ".Image img"],
        "rss":          "https://rsshub.app/apnews/topics/apf-topnews",
        "tier":         2,
        "article_tier": 2,
    },
    "asia.nikkei.com": {
        "headline_sel": ["h3.t-story__title a", "h2 a", ".article-title a", "h3 a"],
        "link_sel":     ["h3.t-story__title a", "h2 a"],
        "content_sel":  [".article-body__content p", ".c-article__body p", "article p"],
        "summary_sel":  [".article-intro", ".story-intro"],
        "author_sel":   [".author-name", ".byline"],
        "date_sel":     ["time", ".article-date"],
        "image_sel":    ["article img"],
        "rss":          "https://asia.nikkei.com/rss/feed/nar",
        "tier":         3,
        "article_tier": 3,
    },
    "scmp.com": {
        "headline_sel": ["h2[itemprop='headline'] a", "h3 a", ".article__title a", "h2 a"],
        "link_sel":     ["h2[itemprop='headline'] a", ".article__title a", "h3 a"],
        "content_sel":  ["div[class*='articleBody'] p", ".article-body p", "article p"],
        "summary_sel":  [".article__description", ".article-intro"],
        "author_sel":   [".author__link", ".byline"],
        "date_sel":     ["time", "[itemprop='datePublished']"],
        "image_sel":    ["article img"],
        "rss":          "https://www.scmp.com/rss/91/feed",
        "tier":         3,
        "article_tier": 3,
    },
    "dw.com": {
        "headline_sel": [".news-item__title", "h3 a", ".small-teaser__headline", "h2 a"],
        "link_sel":     [".news-item__title a", "h3 a", ".small-teaser__headline a"],
        "content_sel":  [".longText p", ".article-text p", "article p"],
        "summary_sel":  [".intro p", ".article-intro", ".teaser p"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://rss.dw.com/rdf/rss-en-all",
        "tier":         1,
        "article_tier": 1,
    },
    "voabangla.com": {
        "headline_sel": ["h4.media-block__title a", "h3 a", ".title a", "h2 a"],
        "link_sel":     ["h4.media-block__title a", "h3 a", ".title a"],
        "content_sel":  ["div.wsw p", ".article-content p", "article p"],
        "summary_sel":  [".description p", ".article-intro"],
        "author_sel":   [".authors", ".byline"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.voabangla.com/api/zmorqmveiq",
        "tier":         1,
        "article_tier": 1,
    },

    # ══════════════════════════════════════════════════════
    # ASIAN / REGIONAL
    # ══════════════════════════════════════════════════════

    "channelnewsasia.com": {
        "headline_sel": ["h6 a", "h3.h6 a", ".card-title a", ".media-object__title a", "h3 a"],
        "link_sel":     ["h6 a", "h3.h6 a", ".card-title a"],
        "content_sel":  [".text-long p", ".article__body p", "article p"],
        "summary_sel":  [".article__summary", ".lead"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".article__date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.channelnewsasia.com/rssfeeds/8395986",
        "tier":         2,
        "article_tier": 2,
    },
    "straitstimes.com": {
        "headline_sel": ["h5 a.stretched-link", "h2 a", ".story-headline a", "h3 a"],
        "link_sel":     ["h5 a.stretched-link", "h2 a", ".story-headline a"],
        "content_sel":  ["div[class*='article-body'] p", ".field-body p", "article p"],
        "summary_sel":  [".article__summary", ".intro"],
        "author_sel":   [".article-author", ".byline"],
        "date_sel":     ["time", ".article__date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.straitstimes.com/news/asia/rss.xml",
        "tier":         3,
        "article_tier": 3,
    },
    "asiatimes.com": {
        "headline_sel": ["h3.entry-title a", "h2.entry-title a", ".post-title a", "h3 a", "h2 a"],
        "link_sel":     ["h3.entry-title a", "h2.entry-title a", ".post-title a"],
        "content_sel":  [".entry-content p", ".post-content p", "article p"],
        "summary_sel":  [".entry-summary p", ".excerpt"],
        "author_sel":   [".author-name", ".byline"],
        "date_sel":     ["time", ".post-date"],
        "image_sel":    ["article img", ".post-thumbnail img"],
        "rss":          "https://asiatimes.com/feed/",
        "tier":         1,
        "article_tier": 1,
    },
    "japantimes.co.jp": {
        "headline_sel": ["h2.article-title a", "h3 a", ".article__title a", "h2 a"],
        "link_sel":     ["h2.article-title a", "h3 a", ".article__title a"],
        "content_sel":  [".article__text p", ".article-content p", "article p"],
        "summary_sel":  [".article__intro", ".intro"],
        "author_sel":   [".article__author", ".byline"],
        "date_sel":     ["time", ".article__date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.japantimes.co.jp/feed/",
        "tier":         2,
        "article_tier": 2,
    },
    "bangkokpost.com": {
        "headline_sel": ["h3.article-title a", "h2 a", ".news-list h3 a", "h3 a"],
        "link_sel":     ["h3.article-title a", "h2 a", ".news-list h3 a"],
        "content_sel":  [".article-content p", ".story-body p", "article p"],
        "summary_sel":  [".article-intro", ".intro-text"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".article-date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.bangkokpost.com/rss/data/topstories.xml",
        "tier":         2,
        "article_tier": 2,
    },
    "asianews.network": {
        "headline_sel": ["h2 a", "h3 a", ".entry-title a", ".post-title a"],
        "link_sel":     ["h2 a", "h3 a", ".entry-title a"],
        "content_sel":  [".entry-content p", ".post-content p", "article p"],
        "summary_sel":  [".entry-summary", ".excerpt"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://asianews.network/feed/",
        "tier":         1,
        "article_tier": 1,
    },

    # ══════════════════════════════════════════════════════
    # PREVIOUSLY CONFIGURED OUTLETS
    # ══════════════════════════════════════════════════════

    "bangla.bdnews24.com": {
        "headline_sel": [".archive-title a", "h2.entry-title a", "h3 a", ".title a"],
        "link_sel":     [".archive-title a", "h2.entry-title a", "h3 a"],
        "content_sel":  [".entry-content p", ".article-body p", "article p"],
        "summary_sel":  [".excerpt", ".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://bangla.bdnews24.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "jagonews24.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a"],
        "link_sel":     ["h3 a", ".title a", "h2 a"],
        "content_sel":  [".news-details p", "article p", ".entry-content p"],
        "summary_sel":  [".news-lead", ".lead"],
        "author_sel":   [".reporter", ".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.jagonews24.com/rss",
        "tier":         1,
        "article_tier": 1,
    },
    "banglatribune.com": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".news-title a"],
        "link_sel":     [".title a", "h3 a", "h2 a"],
        "content_sel":  ["article p", ".news-content p", ".entry-content p"],
        "summary_sel":  [".lead", ".intro"],
        "author_sel":   [".reporter", ".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.banglatribune.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "thedailystar.net": {
        "headline_sel": ["h3.title a", ".title-news a", "h2 a", ".card-title a", "h3 a"],
        "link_sel":     ["h3.title a", ".title-news a", "h2 a"],
        "content_sel":  [".field-body p", ".article-body p", "article p"],
        "summary_sel":  [".field-intro p", ".article-intro"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.thedailystar.net/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "dhakatribune.com": {
        "headline_sel": ["h3.title a", "h2 a", ".card-title a", ".article-title a", "h3 a"],
        "link_sel":     ["h3.title a", "h2 a", ".card-title a"],
        "content_sel":  [".article-body p", ".entry-content p", "article p"],
        "summary_sel":  [".article-intro", ".lead"],
        "author_sel":   [".author", ".byline"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.dhakatribune.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "tbsnews.net": {
        "headline_sel": [".title a", "h3 a", "h2 a", ".card-title a"],
        "link_sel":     [".title a", "h3 a", "h2 a"],
        "content_sel":  ["article p", ".story-content p", ".entry-content p"],
        "summary_sel":  [".lead", ".intro"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.tbsnews.net/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "anandabazar.com": {
        "headline_sel": ["h2 a", "h3 a", ".title a", ".story-title a"],
        "link_sel":     ["h2 a", "h3 a", ".title a"],
        "content_sel":  [".articleBody p", ".story-content p", "article p"],
        "summary_sel":  [".story-intro", ".summary"],
        "author_sel":   [".reporter-name", ".author"],
        "date_sel":     ["time", ".published-date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.anandabazar.com/rss",
        "tier":         3,
        "article_tier": 3,
    },
    "sangbadpratidin.in": {
        "headline_sel": ["h2 a", "h3 a", ".title a", ".news-title a"],
        "link_sel":     ["h2 a", "h3 a", ".title a"],
        "content_sel":  [".article-body p", ".entry-content p", "article p"],
        "summary_sel":  [".lead", ".intro"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.sangbadpratidin.in/feed",
        "tier":         2,
        "article_tier": 2,
    },
    "bengali.abplive.com": {
        "headline_sel": ["h3 a", ".post-title a", "h2 a", ".card-title a"],
        "link_sel":     ["h3 a", ".post-title a", "h2 a"],
        "content_sel":  [".article-body p", ".story-content p", "article p"],
        "summary_sel":  [".article-intro", ".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://bengali.abplive.com/feed",
        "tier":         2,
        "article_tier": 2,
    },
    "zee24ghanta.com": {
        "headline_sel": ["h2 a", "h3 a", ".title a", ".news-title a"],
        "link_sel":     ["h2 a", "h3 a", ".title a"],
        "content_sel":  [".article-body p", ".story-content p", "article p"],
        "summary_sel":  [".article-intro", ".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.zee24ghanta.com/feed",
        "tier":         2,
        "article_tier": 2,
    },
    "eisamay.com": {
        "headline_sel": ["h3 a", "h2 a", ".title a", ".news-title a"],
        "link_sel":     ["h3 a", "h2 a", ".title a"],
        "content_sel":  [".article-body p", ".entry-content p", "article p"],
        "summary_sel":  [".intro", ".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://eisamay.com/rss",
        "tier":         2,
        "article_tier": 2,
    },
    "bartamanpatrika.com": {
        "headline_sel": ["h2 a", "h3 a", ".title a"],
        "link_sel":     ["h2 a", "h3 a"],
        "content_sel":  ["article p", ".entry-content p"],
        "summary_sel":  [".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          None,
        "tier":         2,
        "article_tier": 2,
    },
    "observerbd.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a"],
        "link_sel":     ["h3 a", ".title a", "h2 a"],
        "content_sel":  ["article p", ".entry-content p", ".news-content p"],
        "summary_sel":  [".lead", ".excerpt"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.observerbd.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
    "amar-desh24.com": {
        "headline_sel": ["h3 a", ".title a", ".news-title a", "h2 a"],
        "link_sel":     ["h3 a", ".title a", "h2 a"],
        "content_sel":  ["article p", ".news-body p", ".entry-content p"],
        "summary_sel":  [".lead", ".intro"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          None,
        "tier":         2,
        "article_tier": 2,
    },
    "jjdin.com": {
        "headline_sel": ["h3 a", ".title a", "h2 a"],
        "link_sel":     ["h3 a", ".title a", "h2 a"],
        "content_sel":  ["article p", ".entry-content p"],
        "summary_sel":  [".lead"],
        "author_sel":   [".author"],
        "date_sel":     ["time", ".date"],
        "image_sel":    ["article img"],
        "rss":          "https://www.jjdin.com/feed",
        "tier":         1,
        "article_tier": 1,
    },
}

# ── Generic fallback for unconfigured domains ──────────────
_GENERIC_CFG = {
    "headline_sel": ["h3 a", "h2 a", ".title a", ".news-title a", ".headline a", ".card-title a", ".post-title a"],
    "link_sel":     ["h3 a", "h2 a", ".title a", ".news-title a"],
    "content_sel":  ["article p", ".entry-content p", ".post-content p", ".article-body p", ".content p"],
    "summary_sel":  [".lead", ".excerpt", ".intro", ".summary"],
    "author_sel":   [".author", ".byline", ".reporter"],
    "date_sel":     ["time", ".date", ".published", ".post-date"],
    "image_sel":    ["article img", ".featured-image img", ".post-thumbnail img"],
    "rss":          None,
    "tier":         1,
    "article_tier": 1,
}

# ── User agents ────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

def _ua() -> str:
    return random.choice(USER_AGENTS)


# ============================================================
# HTML UTILITIES
# ============================================================

def _clean(text: str) -> str:
    """Normalize whitespace and truncate."""
    if not text:
        return ""
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()[:500]

def _clean_body(text: str) -> str:
    """Clean article body text — allow longer content."""
    if not text:
        return ""
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def _dedupe_titles(items: list) -> list:
    seen, out = set(), []
    for h in items:
        key = re.sub(r'\W+', '', h.lower())[:60]
        if key and key not in seen and len(h) > 8:
            seen.add(key)
            out.append(h)
    return out

def _get_domain(outlet: dict) -> str:
    site = outlet.get("website", "")
    if not site.startswith("http"):
        site = "https://" + site
    return urlparse(site).netloc.lstrip("www.")

def _build_url(outlet: dict) -> str:
    site = outlet.get("website", "")
    if not site.startswith("http"):
        return "https://" + site
    return site

def _abs_url(href: str, base: str) -> str:
    """Convert relative URL to absolute."""
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    return urljoin(base, href)

def _parse_html_articles(html: str, cfg: dict, base_url: str) -> list:
    """
    Parse homepage HTML → list of {title, url} article stubs.
    Returns up to 30 stubs.
    """
    if not HAS_BS4:
        return []
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen_urls = set()

    for sel in cfg.get("link_sel", []):
        try:
            for el in soup.select(sel):
                title = _clean(el.get_text())
                href  = el.get("href", "")
                if not href:
                    # try parent <a>
                    parent = el.find_parent("a")
                    if parent:
                        href = parent.get("href", "")
                url = _abs_url(href, base_url)
                if title and len(title) > 8 and url and url not in seen_urls:
                    seen_urls.add(url)
                    results.append({"title": title, "url": url})
            if len(results) >= 5:
                break
        except Exception:
            continue

    # Generic fallback if selectors failed
    if not results:
        for tag in soup.find_all(["h2", "h3"]):
            a = tag.find("a", href=True)
            if a:
                title = _clean(a.get_text())
                url   = _abs_url(a["href"], base_url)
                if title and len(title) > 8 and url and url not in seen_urls:
                    seen_urls.add(url)
                    results.append({"title": title, "url": url})

    return results[:30]


def _extract_article_content(html: str, cfg: dict, article_url: str) -> dict:
    """
    From a full article HTML page, extract body text + metadata.
    Returns dict with full_text, summary, author, published_at, image_url, tags.
    """
    if not HAS_BS4:
        return {}
    soup = BeautifulSoup(html, "html.parser")

    # ── Full body text ──
    full_text = ""
    for sel in cfg.get("content_sel", []):
        try:
            paras = soup.select(sel)
            if paras:
                full_text = " ".join(_clean(p.get_text()) for p in paras if _clean(p.get_text()))
                if len(full_text) > 100:
                    break
        except Exception:
            continue

    # If structured selectors fail, grab all <p> inside <article>
    if len(full_text) < 80:
        art = soup.find("article")
        if art:
            paras = art.find_all("p")
            full_text = " ".join(_clean(p.get_text()) for p in paras if len(_clean(p.get_text())) > 15)

    # ── Summary / lead ──
    summary = ""
    for sel in cfg.get("summary_sel", []):
        try:
            el = soup.select_one(sel)
            if el:
                summary = _clean(el.get_text())
                if len(summary) > 20:
                    break
        except Exception:
            continue

    # If no summary, use first ~250 chars of full_text
    if not summary and full_text:
        summary = full_text[:250].rsplit(" ", 1)[0] + "…"

    # ── Author ──
    author = ""
    for sel in cfg.get("author_sel", []):
        try:
            el = soup.select_one(sel)
            if el:
                author = _clean(el.get_text())
                if author and len(author) > 1:
                    break
        except Exception:
            continue

    # ── Published date ──
    published_at = ""
    for sel in cfg.get("date_sel", []):
        try:
            el = soup.select_one(sel)
            if el:
                published_at = (
                    el.get("datetime", "")
                    or el.get("content", "")
                    or _clean(el.get_text())
                )
                if published_at:
                    break
        except Exception:
            continue

    # Try JSON-LD structured data as fallback
    if not published_at:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0]
                published_at = (
                    data.get("datePublished", "")
                    or data.get("dateModified", "")
                )
                if not author:
                    auth = data.get("author", {})
                    if isinstance(auth, dict):
                        author = auth.get("name", "")
                    elif isinstance(auth, list) and auth:
                        author = auth[0].get("name", "")
                if published_at:
                    break
            except Exception:
                continue

    # ── Lead image ──
    image_url = ""
    for sel in cfg.get("image_sel", []):
        try:
            el = soup.select_one(sel)
            if el:
                image_url = el.get("src", "") or el.get("data-src", "") or el.get("data-lazy-src", "")
                if image_url:
                    image_url = _abs_url(image_url, article_url)
                    break
        except Exception:
            continue

    # ── Tags / keywords ──
    tags = []
    try:
        meta_kw = soup.find("meta", attrs={"name": "keywords"})
        if meta_kw:
            tags = [t.strip() for t in meta_kw.get("content", "").split(",") if t.strip()][:8]
    except Exception:
        pass

    return {
        "full_text":    _clean_body(full_text)[:8000],
        "summary":      summary[:500],
        "author":       author[:100],
        "published_at": published_at[:50],
        "image_url":    image_url[:500],
        "tags":         tags,
        "word_count":   len(full_text.split()) if full_text else 0,
    }


# ============================================================
# TIER 1: aiohttp (headlines + articles)
# ============================================================

async def _fetch_html_aiohttp(url: str, session) -> Optional[str]:
    headers = {
        "User-Agent": _ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    try:
        async with session.get(
            url, headers=headers,
            timeout=aiohttp.ClientTimeout(total=18),
            allow_redirects=True, ssl=False
        ) as resp:
            if resp.status == 200:
                return await resp.text(errors="replace")
    except Exception as e:
        logger.debug(f"aiohttp {url}: {e}")
    return None


# ============================================================
# TIER 2: Playwright (standard)
# ============================================================

async def _fetch_html_playwright(url: str, browser) -> Optional[str]:
    if not browser:
        return None
    page = None
    try:
        page = await browser.new_page(
            user_agent=_ua(),
            viewport={"width": 1366, "height": 768},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9,bn;q=0.8"},
        )
        await page.goto(url, timeout=28000, wait_until="domcontentloaded")
        await asyncio.sleep(1.8)
        return await page.content()
    except Exception as e:
        logger.debug(f"Playwright {url}: {e}")
        return None
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass


# ============================================================
# TIER 3: Playwright stealth
# ============================================================

async def _fetch_html_stealth(url: str, browser) -> Optional[str]:
    if not browser:
        return None
    context = None
    try:
        context = await browser.new_context(
            user_agent=_ua(),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Dhaka",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
                "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            }
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver',  { get: () => undefined });
            Object.defineProperty(navigator, 'plugins',    { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages',  { get: () => ['en-US', 'en', 'bn'] });
            Object.defineProperty(navigator, 'platform',   { get: () => 'Win32' });
            window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(screen, 'colorDepth',    { get: () => 24 });
        """)
        page = await context.new_page()
        await page.goto(url, timeout=32000, wait_until="domcontentloaded")
        await page.evaluate("window.scrollTo(0, Math.random() * 800 + 100)")
        await asyncio.sleep(random.uniform(1.5, 3.0))
        html = await page.content()
        return html
    except Exception as e:
        logger.debug(f"Stealth {url}: {e}")
        return None
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass


async def _fetch_html(url: str, tier: int, session, browser) -> Optional[str]:
    """Fetch HTML using appropriate tier."""
    if tier == 1:
        return await _fetch_html_aiohttp(url, session)
    elif tier == 2:
        html = await _fetch_html_playwright(url, browser)
        if not html:
            html = await _fetch_html_aiohttp(url, session)
        return html
    elif tier == 3:
        html = await _fetch_html_stealth(url, browser)
        if not html:
            html = await _fetch_html_playwright(url, browser)
        if not html:
            html = await _fetch_html_aiohttp(url, session)
        return html
    return None


# ============================================================
# TIER 4: Google News RSS
# ============================================================

async def _gnews_rss(domain: str, session) -> list:
    if not HAS_AIOHTTP:
        return []
    url = f"https://news.google.com/rss/search?q=site:{domain}&hl=en&gl=BD&ceid=BD:en"
    try:
        async with session.get(
            url, headers={"User-Agent": _ua()},
            timeout=aiohttp.ClientTimeout(total=12), ssl=False
        ) as resp:
            if resp.status == 200:
                return _parse_rss_to_stubs(await resp.text(errors="replace"))
    except Exception as e:
        logger.debug(f"GNews {domain}: {e}")
    return []


# ============================================================
# TIER 5: Direct RSS
# ============================================================

async def _direct_rss(rss_url: str, session) -> list:
    if not rss_url or not HAS_AIOHTTP:
        return []
    try:
        async with session.get(
            rss_url, headers={"User-Agent": _ua()},
            timeout=aiohttp.ClientTimeout(total=12), ssl=False
        ) as resp:
            if resp.status == 200:
                return _parse_rss_to_stubs(await resp.text(errors="replace"))
    except Exception as e:
        logger.debug(f"RSS {rss_url}: {e}")
    return []


def _parse_rss_to_stubs(content: str) -> list:
    """Parse RSS/Atom XML into list of {title, url, summary, published_at}."""
    stubs = []
    if HAS_FEEDPARSER:
        try:
            feed = feedparser.parse(content)
            for entry in feed.entries[:30]:
                title = _clean(entry.get("title", ""))
                url   = entry.get("link", "")
                summ  = _clean(
                    BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()
                    if HAS_BS4 else entry.get("summary", "")
                )
                pub   = entry.get("published", "") or entry.get("updated", "")
                if title and len(title) > 8:
                    stubs.append({
                        "title":        title,
                        "url":          url,
                        "summary":      summ[:400],
                        "published_at": pub,
                        "full_text":    summ,
                        "author":       "",
                        "image_url":    "",
                        "tags":         [],
                        "word_count":   len(summ.split()),
                        "scraped_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source":       "rss",
                    })
            if stubs:
                return stubs
        except Exception:
            pass

    # Regex fallback
    title_re = re.compile(r'<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', re.DOTALL)
    link_re  = re.compile(r'<link[^>]*>([^<]+)</link>|<link[^>]+href=["\']([^"\']+)["\']', re.DOTALL)
    desc_re  = re.compile(r'<description[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>', re.DOTALL)

    titles = title_re.findall(content)[1:]  # skip feed title
    links  = [m[0] or m[1] for m in link_re.findall(content)]
    descs  = desc_re.findall(content)[1:]

    for i, raw_title in enumerate(titles[:30]):
        title = _clean(re.sub(r'<[^>]+>', '', raw_title))
        url   = links[i + 1] if i + 1 < len(links) else ""
        summ  = _clean(re.sub(r'<[^>]+>', '', descs[i])) if i < len(descs) else ""
        if title and len(title) > 8:
            stubs.append({
                "title":        title,
                "url":          url.strip(),
                "summary":      summ[:400],
                "published_at": "",
                "full_text":    summ,
                "author":       "",
                "image_url":    "",
                "tags":         [],
                "word_count":   len(summ.split()),
                "scraped_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source":       "rss",
            })
    return stubs


# ============================================================
# ARTICLE FETCHER — fetch individual article content
# ============================================================

async def _fetch_article(stub: dict, cfg: dict, session, browser, art_tier: int) -> dict:
    """
    Given a {title, url} stub, fetch and parse the full article.
    Returns enriched article dict.
    """
    url = stub.get("url", "")
    if not url or not url.startswith("http"):
        return {**_empty_article(url, stub.get("title", "")), **stub}

    html = await _fetch_html(url, art_tier, session, browser)
    if not html:
        return {**_empty_article(url, stub.get("title", "")), **stub}

    extracted = _extract_article_content(html, cfg, url)
    return {
        "title":        stub.get("title", ""),
        "url":          url,
        "summary":      extracted.get("summary") or stub.get("summary", ""),
        "full_text":    extracted.get("full_text", ""),
        "published_at": extracted.get("published_at") or stub.get("published_at", ""),
        "author":       extracted.get("author", ""),
        "image_url":    extracted.get("image_url", ""),
        "tags":         extracted.get("tags", []),
        "word_count":   extracted.get("word_count", 0),
        "scraped_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source":       stub.get("source", "scraped"),
    }


# ============================================================
# SINGLE OUTLET SCRAPER
# ============================================================

async def _scrape_one(outlet: dict, session, browser, semaphore: asyncio.Semaphore) -> dict:
    async with semaphore:
        domain     = _get_domain(outlet)
        base_url   = _build_url(outlet)
        name       = outlet.get("name", domain)
        start      = time.time()

        cfg        = SITE_SELECTORS.get(domain, _GENERIC_CFG)
        rss_url    = cfg.get("rss")
        tier       = cfg.get("tier", 1)
        art_tier   = cfg.get("article_tier", 1)
        max_arts   = outlet.get("max_articles", 15)

        logger.info(f"► {name} ({domain})  tier={tier}  art_tier={art_tier}")

        article_stubs = []
        used_tier     = "Failed"

        # ── Step 1: Get article stubs from homepage ──────

        # Try direct HTML scrape
        html = await _fetch_html(base_url, tier, session, browser)
        if html:
            stubs = _parse_html_articles(html, cfg, base_url)
            if stubs:
                article_stubs = stubs
                used_tier = {1: "Tier1 (aiohttp)", 2: "Tier2 (Playwright)", 3: "Tier3 (Stealth)"}.get(tier, "Tier1 (aiohttp)")

        # Try direct RSS feed
        if not article_stubs and rss_url:
            rss_stubs = await _direct_rss(rss_url, session)
            if rss_stubs:
                article_stubs = rss_stubs
                used_tier = "Tier4 (GNews RSS)"

        # Try Google News RSS
        if not article_stubs:
            gnews_stubs = await _gnews_rss(domain, session)
            if gnews_stubs:
                article_stubs = gnews_stubs
                used_tier = "Tier4 (GNews RSS)"

        # ── Step 2: Fetch full article content ───────────
        articles = []
        if article_stubs:
            # RSS stubs already have basic content — only fetch full text for non-RSS
            fetch_tasks = []
            for stub in article_stubs[:max_arts]:
                if stub.get("source") == "rss" and stub.get("full_text"):
                    # RSS already has content — still try to enrich if URL is good
                    if stub.get("url", "").startswith("http"):
                        fetch_tasks.append(_fetch_article(stub, cfg, session, browser, art_tier))
                    else:
                        articles.append(stub)
                else:
                    fetch_tasks.append(_fetch_article(stub, cfg, session, browser, art_tier))

            if fetch_tasks:
                # Batch article fetches with small delay between them
                for i in range(0, len(fetch_tasks), 3):
                    batch = fetch_tasks[i:i+3]
                    batch_results = await asyncio.gather(*batch, return_exceptions=True)
                    for r in batch_results:
                        if isinstance(r, dict):
                            articles.append(r)
                    if i + 3 < len(fetch_tasks):
                        await asyncio.sleep(0.3)

        elapsed = round(time.time() - start, 2)
        status  = "success" if articles else "failed"

        if articles:
            titles = [a["title"] for a in articles]
            # Deduplicate
            seen, unique = set(), []
            for a in articles:
                key = re.sub(r'\W+', '', a["title"].lower())[:60]
                if key and key not in seen:
                    seen.add(key)
                    unique.append(a)
            articles = unique
            logger.info(f"  ✅ {name}: {len(articles)} articles via {used_tier} ({elapsed}s)")
        else:
            titles = []
            logger.warning(f"  ❌ {name}: failed ({elapsed}s)")

        return {
            # App.py compatibility fields
            "name":             name,
            "website":          domain,
            "url":              base_url,
            "key_person":       outlet.get("key_person", "—"),
            "category":         outlet.get("category", "general"),
            "status":           status,
            "tier":             used_tier,
            "headlines":        [a["title"] for a in articles],   # backward compat
            "count":            len(articles),
            "elapsed_sec":      elapsed,
            "scraped_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error":            None if articles else "All scraping tiers exhausted",
            # NEW: full article data
            "articles":         articles,
            "total_words":      sum(a.get("word_count", 0) for a in articles),
        }


# ============================================================
# ASYNC RUNNER
# ============================================================

async def _run_async(outlets: list, concurrency: int) -> list:
    semaphore  = asyncio.Semaphore(concurrency)
    connector  = None
    session    = None

    if HAS_AIOHTTP:
        connector = aiohttp.TCPConnector(
            limit=concurrency * 3,
            ttl_dns_cache=300,
            ssl=False,
            enable_cleanup_closed=True,
        )
        session = aiohttp.ClientSession(
            connector=connector,
            headers={"User-Agent": _ua()},
        )

    browser        = None
    playwright_ctx = None

    if HAS_PLAYWRIGHT:
        try:
            playwright_ctx = await async_playwright().start()
            browser = await playwright_ctx.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--mute-audio",
                    "--ignore-certificate-errors",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            logger.info("✅ Playwright Chromium launched")
        except Exception as e:
            logger.warning(f"⚠️ Playwright unavailable: {e}")
            browser, playwright_ctx = None, None

    results = []
    try:
        tasks   = [_scrape_one(o, session, browser, semaphore) for o in outlets]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    except Exception as e:
        logger.error(f"Gather error: {e}")
    finally:
        for obj, method in [
            (browser,        "close"),
            (playwright_ctx, "stop"),
            (session,        "close"),
            (connector,      "close"),
        ]:
            if obj:
                try:
                    await getattr(obj, method)()
                except Exception:
                    pass

    return list(results)


# ============================================================
# PUBLIC API
# ============================================================

def run_scraper(outlets: list, concurrency: int = 5) -> list:
    """
    Main entry point — called by app.py.

    Args:
        outlets:     List of outlet dicts {name, website, key_person, category}
        concurrency: Max parallel outlet scrapers (4-6 recommended on HF Spaces)
                     Note: each outlet may spawn additional article fetches.

    Returns:
        List of result dicts. Each includes:
          - headlines:  [str]          backward-compatible list of titles
          - articles:   [dict]         full article objects with title+body+meta
          - count:      int
          - status:     'success'|'failed'
          - tier:       str
          - ...other metadata fields
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(_run_async(outlets, concurrency))
    except Exception as e:
        logger.error(f"run_scraper fatal: {e}")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return [
            {
                "name":        o.get("name", "?"),
                "website":     _get_domain(o),
                "url":         _build_url(o),
                "key_person":  o.get("key_person", "—"),
                "category":    o.get("category", "general"),
                "status":      "failed",
                "tier":        "Failed",
                "headlines":   [],
                "articles":    [],
                "count":       0,
                "elapsed_sec": 0,
                "scraped_at":  ts,
                "error":       str(e),
                "total_words": 0,
            }
            for o in outlets
        ]


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    import sys

    TEST_OUTLETS = [
        {"name": "Prothom Alo",    "website": "prothomalo.com",   "key_person": "Matiur Rahman", "category": "bd_newspaper",  "max_articles": 5},
        {"name": "Daily Star",     "website": "thedailystar.net", "key_person": "Mahfuz Anam",   "category": "bd_english",    "max_articles": 5},
        {"name": "Al Jazeera",     "website": "aljazeera.com",    "key_person": "—",             "category": "international", "max_articles": 5},
        {"name": "BBC News",       "website": "bbc.com",          "key_person": "—",             "category": "international", "max_articles": 5},
        {"name": "Somoy TV",       "website": "somoynews.tv",     "key_person": "—",             "category": "bd_tv",         "max_articles": 5},
        {"name": "NDTV",           "website": "ndtv.com",         "key_person": "—",             "category": "indian_news",   "max_articles": 5},
    ]

    print("=" * 70)
    print("  SCRAPER ENGINE v4.0 — ULTRA ADVANCED — Standalone Test")
    print("=" * 70)

    results = run_scraper(TEST_OUTLETS, concurrency=3)

    total_articles = 0
    total_words    = 0

    for r in results:
        icon = "✅" if r["status"] == "success" else "❌"
        print(f"\n{icon} {r['name']:28} | {r['tier']:22} | {r['count']:3} arts | {r['total_words']:6} words | {r['elapsed_sec']}s")

        for art in r.get("articles", [])[:3]:
            title   = art.get("title", "")[:65]
            wc      = art.get("word_count", 0)
            auth    = art.get("author", "") or "—"
            pub     = art.get("published_at", "")[:16] or "—"
            has_txt = "✓" if len(art.get("full_text", "")) > 100 else "✗"
            print(f"   [{has_txt}] {title}")
            print(f"       Author: {auth:<20} | Published: {pub} | Words: {wc}")
            if art.get("summary"):
                print(f"       Summary: {art['summary'][:90]}…")

        total_articles += r["count"]
        total_words    += r.get("total_words", 0)

    print(f"\n{'='*70}")
    success = sum(1 for r in results if r["status"] == "success")
    print(f"  Outlets: {len(results)} | Success: {success} | Articles: {total_articles} | Words: {total_words:,}")
    print("=" * 70)
