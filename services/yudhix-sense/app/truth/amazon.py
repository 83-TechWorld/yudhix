"""Amazon product reviews: read a listing's reviews from a product URL.

Two ways to read, chosen by configuration:
  direct    (default) one ordinary request for the public product page, like a browser would make,
            and the reviews shown on it (usually 8-13 per check). No proxies, no CAPTCHA solving: if
            Amazon answers with a robot check, the check stops and says so. Repeated checks on a
            schedule collect new reviews over time.
  provider  with AMAZON_REVIEWS_API_KEY set, reviews come from a review-data API (Rainforest API),
            newest first, several pages per check. Use this for complete, reliable collection.
Amazon's Conditions of Use restrict automated access; the workspace owner is responsible for using
this in line with them, and the provider route is the one meant for production use.
"""
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from app.core import config

logger = logging.getLogger(__name__)

ASIN = re.compile(r"(?:/dp/|/gp/product/|/gp/aw/d/|/product-reviews/|/ASIN/)([A-Z0-9]{10})(?:[/?#]|$)", re.I)
MARKETPLACES = ("amazon.com", "amazon.in", "amazon.co.uk", "amazon.de", "amazon.fr", "amazon.it", "amazon.es",
                "amazon.ca", "amazon.com.au", "amazon.co.jp", "amazon.ae", "amazon.sa", "amazon.sg", "amazon.nl",
                "amazon.se", "amazon.pl", "amazon.com.br", "amazon.com.mx", "amazon.com.tr")
SHORT_HOSTS = ("amzn.in", "amzn.to", "amzn.eu", "a.co", "amzn.asia")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
PROVIDER_URL = "https://api.rainforestapi.com/request"


class AmazonError(Exception):
    """A message that is safe and useful to show the user."""


class AmazonBlocked(AmazonError):
    pass


@dataclass
class Review:
    review_id: str
    title: str
    body: str
    rating: Optional[float]
    date: Optional[str]          # ISO date
    helpful_votes: int = 0
    verified: bool = False
    author: str = ""
    country: Optional[str] = None


@dataclass
class Listing:
    marketplace: str
    asin: str
    url: str
    title: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    ratings_count: Optional[int] = None
    reviews: List[Review] = field(default_factory=list)
    source: str = "direct"


# ----------------------------------------------------------------------------- URLs

def parse_url(url: str) -> tuple:
    """(marketplace, ASIN, canonical product URL). Follows amzn.to / amzn.in short links."""
    url = (url or "").strip()
    if not url:
        raise AmazonError("Paste an Amazon product link.")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    host = (urlparse(url).hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host in SHORT_HOSTS:
        try:
            res = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
            url = str(res.url)
            host = (urlparse(url).hostname or "").lower().removeprefix("www.").removeprefix("m.")
        except httpx.HTTPError as e:
            raise AmazonError("Couldn't open that short link. Paste the full amazon product URL.") from e
    market = next((m for m in sorted(MARKETPLACES, key=len, reverse=True) if host == m or host.endswith("." + m)), None)
    if not market:
        raise AmazonError("That isn't an Amazon product link (e.g. https://www.amazon.in/dp/B0CL5KNB9M).")
    m = ASIN.search(urlparse(url).path + "/")
    if not m:
        raise AmazonError("No product ID (ASIN) in that link. Open the product on Amazon and copy the address again.")
    asin = m.group(1).upper()
    return market, asin, f"https://www.{market}/dp/{asin}"


# ----------------------------------------------------------------------------- reading

def fetch(url: str, max_reviews: int = 100) -> Listing:
    market, asin, canonical = parse_url(url)
    if config.AMAZON_REVIEWS_API_KEY:
        return _from_provider(market, asin, canonical, max_reviews)
    return _direct(market, asin, canonical)


def _direct(market: str, asin: str, canonical: str) -> Listing:
    try:
        res = httpx.get(canonical, headers=HEADERS, follow_redirects=True, timeout=25)
    except httpx.HTTPError as e:
        raise AmazonError(f"Couldn't reach {market} ({type(e).__name__}). Try again in a minute.") from e
    if res.status_code == 404:
        raise AmazonError("Amazon says this product doesn't exist (404). Check the link.")
    if res.status_code in (503, 429) or is_robot_check(res.text):
        raise AmazonBlocked("Amazon showed a robot check instead of the product page, so no reviews were read. "
                            "Try again later, or set AMAZON_REVIEWS_API_KEY to collect reviews through a review-data "
                            "provider.")
    if res.status_code >= 400:
        raise AmazonError(f"Amazon answered {res.status_code}. Try again later.")
    listing = parse_page(res.text, market, asin, canonical)
    if not listing.title:
        raise AmazonBlocked("Amazon returned a page without the product on it (likely a robot check). Try again later.")
    return listing


def is_robot_check(html: str) -> bool:
    h = (html or "")[:20000].lower()
    return ("captcha" in h and "robot" in h) or "api-services-support@amazon.com" in h or "/errors/validatecaptcha" in h


def parse_page(html: str, market: str, asin: str, url: str) -> Listing:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    text = lambda el: " ".join(el.get_text(" ", strip=True).split()) if el else ""  # noqa: E731
    listing = Listing(market, asin, url, title=text(soup.select_one("#productTitle")) or None)
    img = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
    if img:
        listing.image_url = img.get("data-old-hires") or img.get("src")
    listing.rating = _stars(text(soup.select_one("#acrPopover")) or (soup.select_one("#acrPopover") or {}).get("title", ""))
    count = text(soup.select_one("#acrCustomerReviewText"))
    listing.ratings_count = _int(count)

    seen = set()
    for el in soup.select('[data-hook="review"]'):
        rid = el.get("id") or ""
        # Amazon ships two layouts: classic (review-body/review-title) and cards (reviewRichContentContainer/reviewTitle).
        # select_one takes the first match, so copies inside photo pop-ups are skipped.
        body = text(el.select_one('[data-hook="review-body"], [data-hook="reviewRichContentContainer"]'))
        if not rid or rid in seen or not body:
            continue
        seen.add(rid)
        title_el = el.select_one('[data-hook="review-title"], [data-hook="reviewTitle"]')
        # the title link also contains the star text; keep the last span (the title itself)
        spans = title_el.select("span") if title_el else []
        title = text(spans[-1]) if spans else text(title_el)
        body = re.sub(r"^(Brief|Full) content visible, double tap to read (full|brief) content\.?\s*", "", body)
        stars = el.select_one('[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]')
        date_text = text(el.select_one('[data-hook="review-date"]'))
        listing.reviews.append(Review(
            review_id=rid,
            title=re.sub(r"^\d(?:\.\d)? out of 5 stars\s*", "", title),
            body=re.sub(r"\s*Read (more|less)(\s+Read less)?$", "", body),
            rating=_stars(text(stars)),
            date=_date(date_text),
            helpful_votes=_helpful(text(el.select_one('[data-hook="helpful-vote-statement"]'))),
            verified=bool(el.select_one('[data-hook="avp-badge"], [data-hook="avp-badge-linkless"]')),
            author=text(el.select_one(".a-profile-name")),
            country=_country(date_text),
        ))
    return listing


def _from_provider(market: str, asin: str, canonical: str, max_reviews: int) -> Listing:
    listing = Listing(market, asin, canonical, source="provider")
    page = 1
    while len(listing.reviews) < max_reviews and page <= 10:
        try:
            res = httpx.get(PROVIDER_URL, params={"api_key": config.AMAZON_REVIEWS_API_KEY, "type": "reviews",
                                                  "amazon_domain": market, "asin": asin, "sort_by": "most_recent",
                                                  "page": page}, timeout=60)
        except httpx.HTTPError as e:
            raise AmazonError(f"The review provider is unreachable ({type(e).__name__}).") from e
        if res.status_code in (401, 403):
            raise AmazonError("The review provider rejected AMAZON_REVIEWS_API_KEY.")
        if res.status_code >= 400:
            raise AmazonError(f"The review provider answered {res.status_code}: {res.text[:200]}")
        data = res.json()
        if page == 1:
            product = data.get("product") or {}
            summary = data.get("summary") or {}
            listing.title = product.get("title")
            listing.image_url = product.get("image") or (product.get("main_image") or {}).get("link")
            listing.rating = _float(summary.get("rating") or product.get("rating"))
            listing.ratings_count = _int(str(summary.get("ratings_total") or product.get("ratings_total") or ""))
        items = data.get("reviews") or []
        for r in items:
            date = r.get("date") or {}
            listing.reviews.append(Review(
                review_id=str(r.get("id") or hashlib.sha1((r.get("body") or "").encode()).hexdigest()[:16]),
                title=r.get("title") or "", body=r.get("body") or "", rating=_float(r.get("rating")),
                date=(date.get("utc") or "")[:10] or _date(date.get("raw") or ""),
                helpful_votes=int(r.get("helpful_votes") or 0), verified=bool(r.get("verified_purchase")),
                author=(r.get("profile") or {}).get("name") or "", country=None))
        if not items or not (data.get("pagination") or {}).get("next_page") and len(items) < 10:
            break
        page += 1
    return listing


# ----------------------------------------------------------------------------- small parsers

def _stars(t: str) -> Optional[float]:
    m = re.search(r"(\d(?:[.,]\d)?)\s*out of\s*5", t or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _float(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _int(t: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", (t or "").split(" ")[0] if t else "")
    return int(digits) if digits else None


def _helpful(t: str) -> int:
    if not t:
        return 0
    if t.lower().startswith("one person"):
        return 1
    return _int(t) or 0


_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"], start=1)}


def _date(t: str) -> Optional[str]:
    """'Reviewed in India on 3 March 2025' / 'Reviewed in the United States on March 3, 2025' -> 2025-03-03."""
    t = (t or "").lower()
    m = re.search(r"(\d{1,2}) ([a-z]+),? (\d{4})", t) or re.search(r"([a-z]+) (\d{1,2}),? (\d{4})", t)
    if not m:
        return None
    a, b, year = m.groups()
    day, month = (a, b) if a.isdigit() else (b, a)
    if month not in _MONTHS:
        return None
    return f"{int(year):04d}-{_MONTHS[month]:02d}-{int(day):02d}"


def _country(t: str) -> Optional[str]:
    m = re.search(r"reviewed in (?:the )?(.+?) on ", (t or ""), re.I)
    return m.group(1) if m else None


def sentiment_for(rating: Optional[float]) -> Optional[str]:
    """Stars decide the sentiment of a review: 4-5 positive, 3 neutral, 1-2 negative."""
    if rating is None:
        return None
    return "POSITIVE" if rating >= 4 else "NEGATIVE" if rating <= 2 else "NEUTRAL"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
