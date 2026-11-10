"""Polite, safe web page fetcher (SYSTEM_ARCHITECTURE §8.4).

- http/https only; DNS resolved and private / loopback / link-local / metadata ranges blocked (SSRF)
- redirects followed manually (max 3), each hop re-validated
- robots.txt honoured (cached per host), 1 request/second per domain
- size and time limits; HTML/plain text only
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
import threading
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin, urldefrag, urlparse

import httpx
import tldextract
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.providers.http import Throttle, client
from app.workflow.errors import PermanentError, TransientError

_settings = get_settings()
_throttle = Throttle(_settings.fetch_per_domain_interval_s)
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_robots_lock = threading.Lock()
_extract = tldextract.TLDExtract(suffix_list_urls=())  # offline snapshot, no network at import

BLOCKED_NETS = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
    "192.168.0.0/16", "224.0.0.0/4", "240.0.0.0/4", "::1/128", "fc00::/7", "fe80::/10")]


@dataclass
class FetchedPage:
    url: str
    final_url: str
    status: int
    title: str | None
    text: str
    description: str | None
    published_at: datetime | None
    links: list[tuple[str, str]] = field(default_factory=list)  # (absolute url, anchor text)
    content_hash: bytes = b""


def registrable_domain(url_or_host: str) -> str | None:
    host = urlparse(url_or_host).hostname if "//" in url_or_host else url_or_host
    if not host:
        return None
    ext = _extract(host)
    if not ext.domain or not ext.suffix:
        return None
    return f"{ext.domain}.{ext.suffix}".lower()


def normalize_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url.lstrip("/")
    return urldefrag(url)[0]


def _check_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise PermanentError(f"Could not resolve {host}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if any(ip in net for net in BLOCKED_NETS):
            raise PermanentError(f"Blocked address for {host}")


def _robots_allows(url: str) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    with _robots_lock:
        cached = _robots.get(base, "missing")
    if cached == "missing":
        rp: urllib.robotparser.RobotFileParser | None = urllib.robotparser.RobotFileParser()
        try:
            r = client.get(base + "/robots.txt", timeout=6.0, follow_redirects=True)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            elif r.status_code in (401, 403):
                rp.disallow_all = True
            else:
                rp.allow_all = True
        except httpx.HTTPError:
            rp = None  # robots unreachable → treat as allowed but don't cache forever
        with _robots_lock:
            _robots[base] = rp
        cached = rp
    if cached is None:
        return True
    return cached.can_fetch(_settings.http_user_agent, url)


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s.replace("Z", "+0000"), fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def extract(html: str, base_url: str) -> tuple[str | None, str, str | None, datetime | None, list[tuple[str, str]]]:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True)[:300] if soup.title else None
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    description = desc_tag.get("content", "").strip()[:500] if desc_tag else None
    pub = None
    for attrs in ({"property": "article:published_time"}, {"name": "date"}, {"itemprop": "datePublished"}):
        t = soup.find("meta", attrs=attrs)
        if t and t.get("content"):
            pub = _parse_date(t["content"])
            if pub:
                break
    links: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        links.append((urldefrag(urljoin(base_url, href))[0], a.get_text(" ", strip=True)[:80]))
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return title, text, description, pub, links


def fetch(url: str) -> FetchedPage:
    url = normalize_url(url)
    current = url
    for _ in range(4):
        p = urlparse(current)
        if p.scheme not in ("http", "https") or not p.hostname:
            raise PermanentError(f"Unsupported URL: {current}")
        _check_host(p.hostname)
        if not _robots_allows(current):
            raise PermanentError(f"robots.txt disallows {p.hostname}{p.path or '/'}")
        _throttle.wait(registrable_domain(p.hostname) or p.hostname)
        try:
            with client.stream("GET", current) as r:
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    current = urljoin(current, r.headers["location"])
                    continue
                if r.status_code == 429 or r.status_code >= 500:
                    raise TransientError(f"{p.hostname} returned HTTP {r.status_code}")
                if r.status_code >= 400:
                    raise PermanentError(f"{p.hostname} returned HTTP {r.status_code}")
                ctype = r.headers.get("content-type", "")
                if not any(t in ctype for t in ("text/html", "text/plain", "application/xhtml")):
                    raise PermanentError(f"Not an HTML page ({ctype.split(';')[0] or 'unknown type'})")
                body = b""
                for chunk in r.iter_bytes():
                    body += chunk
                    if len(body) > _settings.fetch_max_bytes:
                        break
                html = body.decode(r.encoding or "utf-8", errors="replace")
                title, text, desc, pub, links = extract(html, current)
                return FetchedPage(url=url, final_url=current, status=r.status_code, title=title, text=text,
                                   description=desc, published_at=pub, links=links,
                                   content_hash=hashlib.sha256(text.encode()).digest())
        except httpx.TimeoutException as e:
            raise TransientError(f"Timed out fetching {p.hostname}") from e
        except httpx.HTTPError as e:
            raise TransientError(f"Network error fetching {p.hostname}: {type(e).__name__}") from e
    raise PermanentError("Too many redirects")


INTERESTING = re.compile(
    r"(about|company|who-we-are|overview|profile|careers?|jobs|contact|locations?|offices?|news|press|media|events?|clients?|customers?|industries)",
    re.I)


def candidate_links(page: FetchedPage, limit: int = 15) -> list[str]:
    """Same-site links likely to hold company facts, ranked by keyword match."""
    site = registrable_domain(page.final_url)
    seen, out = set(), []
    for href, anchor in page.links:
        if registrable_domain(href) != site:
            continue
        path = urlparse(href).path.lower()
        if not path or path == "/" or re.search(r"\.(pdf|jpg|png|zip|docx?)$", path):
            continue
        if INTERESTING.search(path) or INTERESTING.search(anchor or ""):
            key = path.rstrip("/")
            if key not in seen:
                seen.add(key)
                out.append(href)
    return out[:limit]
