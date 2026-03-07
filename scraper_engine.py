"""
============================================================
POLITICAL MEDIA INTELLIGENCE — ADVANCED SCRAPING ENGINE
============================================================
Tier 1: aiohttp + BeautifulSoup  (fast, lightweight)
Tier 2: Playwright async          (JS-rendered pages)
Tier 3: Playwright + stealth      (bot-protected sites)

Features:
- Concurrent async scraping (all 24 sites simultaneously)
- Site-specific CSS selectors for every BD news outlet
- Rotating user-agents + headers
- Exponential backoff retry (3 attempts)
- Auto-fallback: Tier1 → Tier2 → Tier3
- Timeout management per tier
- Deduplication + quality filtering
============================================================
"""

import asyncio
import aiohttp
import random
import time
import re
import logging
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)

# ============================================================
# USER AGENT POOL (Rotating)
# ============================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
]

def get_headers(referer: str = "") -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "bn-BD,bn;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
        **({"Referer": referer} if referer else {}),
    }

# ============================================================
# SITE-SPECIFIC SELECTORS (Tuned for each BD outlet)
# ============================================================

SITE_SELECTORS = {
    # ── Bangla Newspapers ─────────────────────────────────
    "dailyjanakantha.com": {
        "selectors": [".headline", ".news-title", "h2 a", "h3 a", ".lead-news h2", ".top-news h3"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "jjdin.com": {
        "selectors": [".news-title", ".headline a", "h2.title", "h3 a", ".latest-news h4"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "bhorerkagoj.com": {
        "selectors": [".news-title a", "h2 a", "h3 a", ".lead h2", ".top-story h3", ".khabar-title"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "dailyinqilab.com": {
        "selectors": [".news-title", "h2 a", "h3 a", ".headline a", ".lead-news a", ".top-news h2"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "sangbad.net.bd": {
        "selectors": [".news-title a", "h2 a", "h3 a", ".lead a", ".top a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "daily-dinkal.com": {
        "selectors": ["h2 a", "h3 a", ".headline", ".news-heading a", ".title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "kalbela.com": {
        "selectors": [".news-title a", "h2 a", "h3 a", ".top-lead h2", ".headline a", ".khabar h3"],
        "js_required": True,   # React-based
        "encoding": "utf-8",
    },
    "deshrupantor.com": {
        "selectors": [".headline a", "h2 a", "h3 a", ".news-title", ".lead h2"],
        "js_required": False,
        "encoding": "utf-8",
    },

    # ── English Newspapers ────────────────────────────────
    "thedailystar.net": {
        "selectors": [
            ".headline-wrapper h3 a", ".card__title a", "h3.title a",
            ".story-meta h3 a", ".widget-title a", "h2 a", ".news-headline a"
        ],
        "js_required": False,
        "encoding": "utf-8",
    },
    "observerbd.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a", ".top-news h3"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "tbsnews.net": {
        "selectors": [
            ".card-title a", "h3 a", "h2 a", ".article-title a",
            ".story-title a", ".headline a"
        ],
        "js_required": False,
        "encoding": "utf-8",
    },
    "dhakatribune.com": {
        "selectors": [
            ".article-title a", "h3 a", "h2 a", ".card-title a",
            ".headline a", ".story-title"
        ],
        "js_required": False,
        "encoding": "utf-8",
    },

    # ── Digital Portals ───────────────────────────────────
    "bangla.bdnews24.com": {
        "selectors": [
            ".lead-news h2 a", ".timeline-item h3 a", "h2 a", "h3 a",
            ".headline a", ".news-title a", ".latestNews h4 a"
        ],
        "js_required": False,
        "encoding": "utf-8",
    },
    "jagonews24.com": {
        "selectors": [
            ".headline a", "h2 a", "h3 a", ".news-title a",
            ".top-news-title a", ".lead h2 a"
        ],
        "js_required": False,
        "encoding": "utf-8",
    },
    "banglatribune.com": {
        "selectors": [
            ".headline-title a", "h2 a", "h3 a", ".news-title",
            ".article-title a", ".lead-news a"
        ],
        "js_required": True,
        "encoding": "utf-8",
    },
    "amar-desh24.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },

    # ── TV Channels ───────────────────────────────────────
    "somoynews.tv": {
        "selectors": [
            ".headline a", "h2 a", "h3 a", ".news-title a",
            ".latest-news h4 a", ".top-news-title a"
        ],
        "js_required": True,   # Heavy JS
        "encoding": "utf-8",
    },
    "jamuna.tv": {
        "selectors": [
            ".headline a", "h2 a", "h3 a", ".news-title a",
            ".video-title a", ".top-headline a"
        ],
        "js_required": True,
        "encoding": "utf-8",
    },
    "channelionline.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a", ".article-title"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "ekattor.tv": {
        "selectors": [
            ".news-title a", "h2 a", "h3 a", ".headline a",
            ".latest h4 a", ".top-news a"
        ],
        "js_required": True,
        "encoding": "utf-8",
    },

    # ── Regional ──────────────────────────────────────────
    "coxsbazarnews.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "lakshmipur24.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },

    # ── International ─────────────────────────────────────
    "bbc.com": {
        "selectors": [
            "[data-testid='card-headline']", "h3[class*='headline']",
            ".gs-c-promo-heading__title", "h1", "h2", "h3"
        ],
        "js_required": False,
        "encoding": "utf-8",
        "url_override": "https://www.bbc.com/bengali",
    },
    "anandabazar.com": {
        "selectors": [
            ".story-title a", "h2 a", "h3 a", ".headline a",
            ".article-title a", "[class*='headline'] a",
            "[class*='StoryTitle'] a", "[class*='story-card'] h3"
        ],
        "js_required": True,
        "encoding": "utf-8",
    },

    # ── Indian Bengali Media ──────────────────────────────
    "sangbadpratidin.in": {
        "selectors": [
            ".news-title a", "h2 a", "h3 a", ".headline a",
            ".article-title a", ".lead-news h2 a", "[class*='title'] a"
        ],
        "js_required": False,
        "encoding": "utf-8",
    },
    "bengali.abplive.com": {
        "selectors": [
            "[class*='story-title'] a", "[class*='card-title'] a",
            "h2 a", "h3 a", ".headline a", "[class*='headline']",
            "[data-story-title]", ".abp-story-title"
        ],
        "js_required": True,
        "encoding": "utf-8",
        "url_override": "https://bengali.abplive.com",
    },
    "zee24ghanta.com": {
        "selectors": [
            ".news-title a", "h2 a", "h3 a", ".headline a",
            "[class*='story-title'] a", ".card-headline a",
            "[class*='Title'] a"
        ],
        "js_required": True,
        "encoding": "utf-8",
    },
    "eisamay.com": {
        "selectors": [
            "[class*='headline'] a", "[class*='Title'] a",
            "h2 a", "h3 a", ".article-title a",
            "[class*='story'] h3 a", "._3WlLe a", "._1dmo6"
        ],
        "js_required": True,
        "encoding": "utf-8",
    },
    "bartamanpatrika.com": {
        "selectors": [
            "h2 a", "h3 a", ".headline a", ".news-title a",
            ".article-title a", ".lead h2 a"
        ],
        "js_required": False,
        "encoding": "utf-8",
    },

    # ── International News Agencies ───────────────────────
    "afp.com": {
        "selectors": [
            "h2 a", "h3 a", ".article-title a", ".story-title a",
            "[class*='headline'] a", ".title a"
        ],
        "js_required": False,
        "encoding": "utf-8",
        "url_override": "https://www.afp.com/en/news-hub",
    },
    "theguardian.com": {
        "selectors": [
            ".fc-item__title a", "[data-link-name='article'] span",
            "h3.fc-item__title", ".js-headline-text",
            "[class*='card__headline']", "h3 a", "h2 a",
            "[data-component='card'] h3"
        ],
        "js_required": False,
        "encoding": "utf-8",
        "url_override": "https://www.theguardian.com/world/bangladesh",
    },
    "abcnews.go.com": {
        "selectors": [
            ".AnchorLink span", "h2 a", "h3 a",
            "[class*='headline'] a", ".ContentRoll__Headline",
            "[data-testid*='headline']", ".News__Item h2"
        ],
        "js_required": True,
        "encoding": "utf-8",
        "url_override": "https://abcnews.go.com/International",
    },
    "news.yahoo.com": {
        "selectors": [
            "h3 a", "h2 a", "[class*='Fw(b)'] a",
            "[class*='headline'] a", "li.js-stream-content h3 a",
            "[data-test-locator='stream-item-title']"
        ],
        "js_required": True,
        "encoding": "utf-8",
        "url_override": "https://news.yahoo.com/world/",
    },
    "nytimes.com": {
        # NYT is heavily JS + paywall — use RSS feed endpoint as fallback
        "selectors": [
            "[class*='headline'] a", "[data-testid='headline'] a",
            "h3 a", "h2 a", "p.summary-class",
            "[class*='css-'] h3", "section h2 a"
        ],
        "js_required": True,
        "encoding": "utf-8",
        "url_override": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "is_rss": True,
    },
    "hindustantimes.com": {
        "selectors": [
            "h3.hdg3 a", "h2 a", "h3 a", ".story-title a",
            "[class*='storyShortDetail'] h3 a", ".newsContent h3 a",
            "[class*='detail'] h3 a"
        ],
        "js_required": False,
        "encoding": "utf-8",
        "url_override": "https://www.hindustantimes.com/world-news/bangladesh",
    },
    "edition.cnn.com": {
        "selectors": [
            ".container__headline-text", "span.cd__headline-text",
            "h3.cd__headline a", "[class*='container_lead-plus-headlines'] h3",
            ".headline a", "h2 a", "h3 a",
            "[data-component-name='card'] span[data-editable='headline']"
        ],
        "js_required": True,
        "encoding": "utf-8",
        "url_override": "https://edition.cnn.com/world/asia",
    },
    "aljazeera.com": {
        "selectors": [
            ".article-card__title", "h3.article-card__title",
            "[class*='article-card'] h3", "h2 a", "h3 a",
            ".topics-sec-item h4 a", "[class*='ArticleTitle']",
            ".u-clickable-card__link span"
        ],
        "js_required": False,
        "encoding": "utf-8",
        "url_override": "https://www.aljazeera.com/tag/bangladesh/",
    },

    # ── Regional / Local BD Portals ───────────────────────
    "dailycoxsbazar.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a", ".title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "uttorpurbo.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "ajkerjamalpur.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "amaderbarisal.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a", ".title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "surmatimes.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "chandpurtimes.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "muktokhobor24.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "bograsangbad.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a", ".title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "rajshahirsomoy.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "prothom-feni.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
    "gamerkagoj.com": {
        "selectors": ["h2 a", "h3 a", ".headline a", ".news-title a"],
        "js_required": False,
        "encoding": "utf-8",
    },
}

# Fallback for unknown sites
DEFAULT_SELECTORS = {
    "selectors": ["h1", "h2", "h3", "h4", ".headline", ".news-title", ".title a", "article h2"],
    "js_required": False,
    "encoding": "utf-8",
}

# ============================================================
# RSS SCRAPER (Paywall bypass for NYT, AFP, etc.)
# ============================================================

async def scrape_rss(session: aiohttp.ClientSession, url: str) -> list:
    """Parse RSS/Atom feed — bypasses JS and paywalls"""
    headlines = []
    try:
        async with session.get(
            url, headers=get_headers(), timeout=aiohttp.ClientTimeout(total=12), ssl=False
        ) as resp:
            raw = await resp.read()
            # Try XML parsers
            for parser in ["xml", "lxml-xml", "html.parser"]:
                try:
                    soup = BeautifulSoup(raw, parser)
                    break
                except Exception:
                    continue

            # RSS <title> tags inside <item> or <entry>
            items = soup.find_all("item") or soup.find_all("entry")
            for item in items[:30]:
                title_tag = item.find("title")
                if title_tag:
                    text = title_tag.get_text(strip=True)
                    # Strip CDATA
                    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text)
                    if len(text) > 15:
                        headlines.append(text)
    except Exception as e:
        logger.debug(f"RSS scrape error {url}: {e}")
    return headlines[:30]


# ============================================================
# TIER 1: aiohttp (Fast, lightweight)
# ============================================================

async def scrape_tier1(session: aiohttp.ClientSession, url: str, config: dict) -> list:
    """Async HTTP scraping with BeautifulSoup. Supports RSS feeds for paywall sites."""

    # ── RSS Mode (for NYT, AFP etc.) ──────────────────────
    if config.get("is_rss"):
        return await scrape_rss(session, url)

    headlines = []
    for attempt in range(3):
        try:
            async with session.get(
                url,
                headers=get_headers(url),
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=True,
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    await asyncio.sleep(2 ** attempt)
                    continue

                # Try to detect encoding
                content_type = resp.headers.get("Content-Type", "")
                if "charset=" in content_type:
                    encoding = content_type.split("charset=")[-1].strip()
                else:
                    encoding = config.get("encoding", "utf-8")

                try:
                    html = await resp.text(encoding=encoding, errors="replace")
                except:
                    raw = await resp.read()
                    html = raw.decode("utf-8", errors="replace")

                soup = BeautifulSoup(html, "lxml")
                headlines = extract_headlines(soup, config["selectors"])
                if headlines:
                    return headlines

        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.debug(f"Tier1 error for {url}: {e}")
            break

    return headlines


# ============================================================
# TIER 2: Playwright (JS-rendered pages)
# ============================================================

async def scrape_tier2(playwright_ctx, url: str, config: dict) -> list:
    """Playwright-based scraping for JS-heavy sites"""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    headlines = []
    browser = None
    try:
        browser = await playwright_ctx.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--no-first-run",
                "--disable-default-apps",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=random.choice(USER_AGENTS),
            locale="bn-BD",
            timezone_id="Asia/Dhaka",
            java_script_enabled=True,
            # Stealth: override navigator properties
            extra_http_headers={
                "Accept-Language": "bn-BD,bn;q=0.9,en-US;q=0.8",
            }
        )

        # Block images/fonts/media to speed up
        await context.route(
            "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,mp4,mp3,webm}",
            lambda route: route.abort()
        )

        page = await context.new_page()

        # Stealth patches
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            window.chrome = {runtime: {}};
        """)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            # Wait for content to render
            await page.wait_for_timeout(2000)
        except PWTimeout:
            pass
        except Exception:
            pass

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")
        headlines = extract_headlines(soup, config["selectors"])

        await context.close()
        await browser.close()

    except Exception as e:
        logger.debug(f"Tier2 error for {url}: {e}")
        if browser:
            try:
                await browser.close()
            except:
                pass

    return headlines


# ============================================================
# TIER 3: Playwright + Aggressive Stealth (Anti-bot bypass)
# ============================================================

async def scrape_tier3(playwright_ctx, url: str, config: dict) -> list:
    """Maximum stealth mode for heavily protected sites"""
    if not PLAYWRIGHT_AVAILABLE:
        return []

    headlines = []
    browser = None
    try:
        browser = await playwright_ctx.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=random.choice(USER_AGENTS),
            locale="bn-BD",
            timezone_id="Asia/Dhaka",
        )

        page = await context.new_page()

        # Full stealth patches
        await page.add_init_script("""
            // Override webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {get: () => [
                {name: 'Chrome PDF Plugin'}, {name: 'Chrome PDF Viewer'},
                {name: 'Native Client'}
            ]});
            // Override languages
            Object.defineProperty(navigator, 'languages', {get: () => ['bn-BD', 'en-US', 'en']});
            // Add chrome object
            window.chrome = {runtime: {}, loadTimes: () => {}};
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) =>
                parameters.name === 'notifications'
                    ? Promise.resolve({state: Notification.permission})
                    : originalQuery(parameters);
        """)

        # Human-like behavior: random delays
        await page.goto(url, wait_until="networkidle", timeout=35000)
        await page.wait_for_timeout(random.randint(1500, 3000))

        # Scroll to trigger lazy-loaded content
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await page.wait_for_timeout(1000)

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")
        headlines = extract_headlines(soup, config["selectors"])

        await context.close()
        await browser.close()

    except Exception as e:
        logger.debug(f"Tier3 error for {url}: {e}")
        if browser:
            try:
                await browser.close()
            except:
                pass

    return headlines


# ============================================================
# HEADLINE EXTRACTOR (Smart deduplication + quality filter)
# ============================================================

MIN_LENGTH = 15
MAX_LENGTH = 300

GARBAGE_PATTERNS = [
    r"^(home|about|contact|login|register|subscribe|follow us|facebook|twitter|youtube)$",
    r"^\d+$",
    r"^[\W\s]+$",
    r"^(আরো|আরও|সব খবর|বিস্তারিত|পড়ুন|more|read more|see more|click here|loading)$",
]
GARBAGE_RE = re.compile("|".join(GARBAGE_PATTERNS), re.IGNORECASE)


def is_valid_headline(text: str) -> bool:
    """Filter out garbage, nav links, and too-short strings"""
    text = text.strip()
    if len(text) < MIN_LENGTH or len(text) > MAX_LENGTH:
        return False
    if GARBAGE_RE.match(text.lower()):
        return False
    # Must have at least some Bengali or meaningful Latin chars
    has_bengali = bool(re.search(r'[\u0980-\u09FF]', text))
    has_latin_words = len(re.findall(r'[a-zA-Z]{3,}', text)) >= 2
    return has_bengali or has_latin_words


def extract_headlines(soup: BeautifulSoup, selectors: list) -> list:
    """Extract and deduplicate headlines using site-specific selectors"""
    seen = set()
    headlines = []

    # Strategy 1: Site-specific selectors (priority)
    for selector in selectors:
        try:
            elements = soup.select(selector, limit=50)
            for el in elements:
                text = el.get_text(separator=" ", strip=True)
                normalized = re.sub(r'\s+', ' ', text).strip()
                key = normalized[:80].lower()
                if key not in seen and is_valid_headline(normalized):
                    seen.add(key)
                    headlines.append(normalized)
        except Exception:
            continue

    # Strategy 2: Generic fallback if selectors yielded < 5
    if len(headlines) < 5:
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5"], limit=100):
            text = tag.get_text(separator=" ", strip=True)
            normalized = re.sub(r'\s+', ' ', text).strip()
            key = normalized[:80].lower()
            if key not in seen and is_valid_headline(normalized):
                seen.add(key)
                headlines.append(normalized)

    # Strategy 3: Anchor text for remaining gaps
    if len(headlines) < 8:
        for a in soup.find_all("a", href=True, limit=300):
            text = a.get_text(separator=" ", strip=True)
            normalized = re.sub(r'\s+', ' ', text).strip()
            key = normalized[:80].lower()
            if key not in seen and is_valid_headline(normalized) and len(normalized) > 30:
                seen.add(key)
                headlines.append(normalized)

    return headlines[:35]


# ============================================================
# MAIN SCRAPER — Auto-Tier with Fallback
# ============================================================

async def scrape_outlet(
    session: aiohttp.ClientSession,
    playwright_ctx,
    outlet: dict
) -> dict:
    """
    Scrape a single outlet with automatic tier selection and fallback.
    Tier 1 (aiohttp) → Tier 2 (Playwright) → Tier 3 (Stealth)
    """
    website = outlet.get("website")

    # Skip outlets with no website
    if not website:
        return {
            "name":        outlet.get("name", "Unknown"),
            "website":     None,
            "category":    outlet.get("category", ""),
            "key_person":  outlet.get("key_person", ""),
            "headlines":   [],
            "count":       0,
            "tier":        "No Website",
            "elapsed_sec": 0,
            "status":      "skipped",
            "url":         None,
            "scraped_at":  datetime.now().isoformat(),
        }
    config = SITE_SELECTORS.get(website, DEFAULT_SELECTORS)
    url_override = config.get("url_override")
    url = url_override if url_override else f"https://{website}"

    start_time = time.time()
    headlines = []
    tier_used = None
    error = None

    # Tier 1: Fast aiohttp (skip if JS required)
    if not config.get("js_required", False):
        headlines = await scrape_tier1(session, url, config)
        if headlines:
            tier_used = "Tier1 (aiohttp)"

    # Tier 2: Playwright
    if not headlines and playwright_ctx:
        headlines = await scrape_tier2(playwright_ctx, url, config)
        if headlines:
            tier_used = "Tier2 (Playwright)"

    # Tier 3: Stealth Playwright (last resort)
    if not headlines and playwright_ctx:
        headlines = await scrape_tier3(playwright_ctx, url, config)
        tier_used = "Tier3 (Stealth)" if headlines else None

    elapsed = round(time.time() - start_time, 2)

    return {
        "name":        outlet["name"],
        "website":     website,
        "category":    outlet.get("category", ""),
        "key_person":  outlet.get("key_person", ""),
        "headlines":   headlines,
        "count":       len(headlines),
        "tier":        tier_used or "Failed",
        "elapsed_sec": elapsed,
        "status":      "success" if headlines else "failed",
        "url":         url,
        "scraped_at":  datetime.now().isoformat(),
    }


# ============================================================
# CONCURRENT BATCH SCRAPER
# ============================================================

async def scrape_all_outlets(outlets: list, concurrency: int = 6) -> list:
    """
    Scrape all outlets concurrently with a semaphore to avoid overwhelming servers.
    concurrency=6 means 6 outlets are scraped simultaneously.
    """
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    connector = aiohttp.TCPConnector(
        limit=20,
        limit_per_host=2,
        ssl=False,
        ttl_dns_cache=300,
        force_close=False,
    )

    async def scrape_with_semaphore(session, pw_ctx, outlet):
        async with semaphore:
            # Slight random delay to avoid synchronized requests
            await asyncio.sleep(random.uniform(0.1, 0.8))
            return await scrape_outlet(session, pw_ctx, outlet)

    async with aiohttp.ClientSession(connector=connector) as session:
        if PLAYWRIGHT_AVAILABLE:
            async with async_playwright() as pw:
                tasks = [
                    scrape_with_semaphore(session, pw, outlet)
                    for outlet in outlets
                ]
                results = await asyncio.gather(*tasks, return_exceptions=False)
        else:
            tasks = [
                scrape_with_semaphore(session, None, outlet)
                for outlet in outlets
            ]
            results = await asyncio.gather(*tasks, return_exceptions=False)

    return list(results)


# ============================================================
# SYNC WRAPPER (for Streamlit compatibility)
# ============================================================

def run_scraper(outlets: list, concurrency: int = 6) -> list:
    """Sync wrapper — handles event loop for Streamlit"""
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(scrape_all_outlets(outlets, concurrency))
    finally:
        loop.close()
