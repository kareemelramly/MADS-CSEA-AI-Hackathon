"""Evidence sources and the per-run source registry (SRS DIS-3 to DIS-6, COMM-3).

Sources: HN Algolia search, Stack Exchange search, GitHub issues search (demand evidence) and
Wikipedia (background only, never demand evidence). Reddit is not used: its data terms require
API credentials. Every fetched item gets a registry entry (S001, S002 ...) with canonical URL,
source name, HTTP status, fetched_at and excerpt. The model sees IDs and excerpts only; code
renders URLs. Fetched text is untrusted data: nothing in it can trigger an action.
"""
import gzip
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import log as logmod

UA = "AgenticVentureBuilder/1.0 (open-source hackathon prototype; read-only evidence search)"
STOP = set("a an the and or for of to in on with by from my our your their is are be as at it this that "
           "into using use tool app apps based online simple small new help helps people who want".split())


def _http_get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/html;q=0.9",
                                               "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(2_000_000)
            if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return r.status, raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


_get = _http_get


def set_http(fn):
    global _get
    _get = fn


def clean(text, n=320):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:n]


def query_terms(brief, broaden=False):
    if brief.get("search_terms"):
        terms = brief["search_terms"]
        return terms if not broaden else " ".join(terms.split()[:2])
    words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]+", brief.get("idea", "").lower()) if w not in STOP]
    return " ".join(words[: (2 if broaden else 4)])


# ------------------------------------------------------------------ registry
def register(ctx, *, url, source, status, excerpt, title="", use="demand"):
    for sid, rec in ctx.sources.items():
        if rec["url"] == url:
            return sid
    sid = f"S{len(ctx.sources) + 1:03d}"
    ctx.sources[sid] = {"source_id": sid, "url": url, "source": source, "http_status": status,
                        "fetched_at": logmod.now_iso(), "title": clean(title, 160), "excerpt": clean(excerpt), "use": use}
    return sid


# ------------------------------------------------------------------ fetchers
def hn(q, timeout):
    url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode({"query": q, "tags": "(story,comment)", "hitsPerPage": 25})
    st, body = _get(url, timeout)
    items = []
    if st == 200:
        for h in json.loads(body).get("hits", []):
            text = h.get("comment_text") or h.get("story_text") or ""
            items.append({"url": f"https://news.ycombinator.com/item?id={h['objectID']}",
                          "title": h.get("title") or h.get("story_title") or "", "excerpt": (h.get("title") or "") + " " + clean(text)})
    return st, items


def stackexchange(q, timeout, sites=("webapps", "stackoverflow")):
    items, last = [], 0
    for site in sites:
        url = "https://api.stackexchange.com/2.3/search/excerpts?" + urllib.parse.urlencode(
            {"order": "desc", "sort": "relevance", "q": q, "site": site, "pagesize": 15})
        st, body = _get(url, timeout)
        last = st if st != 200 or not last else last
        if st == 200:
            for it in json.loads(body).get("items", []):
                qid = it.get("question_id")
                if not qid:
                    continue
                items.append({"url": f"https://{site}.stackexchange.com/q/{qid}" if site != "stackoverflow" else f"https://stackoverflow.com/q/{qid}",
                              "title": it.get("title", ""), "excerpt": clean(it.get("title", "")) + " " + clean(it.get("excerpt", ""))})
            last = 200
    return last, items


def github(q, timeout):
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode({"q": f"{q} is:issue", "per_page": 20})
    st, body = _get(url, timeout)
    items = []
    if st == 200:
        for it in json.loads(body).get("items", []):
            items.append({"url": it.get("html_url"), "title": it.get("title", ""),
                          "excerpt": clean(it.get("title", "")) + " " + clean(it.get("body") or "")})
    return st, items


def wikipedia(q, timeout):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 3})
    st, body = _get(url, timeout)
    items = []
    if st == 200:
        for it in json.loads(body).get("query", {}).get("search", []):
            items.append({"url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(it["title"].replace(" ", "_")),
                          "title": it["title"], "excerpt": clean(it.get("snippet", ""))})
    return st, items


FETCHERS = {"hn_algolia": hn, "stackexchange": stackexchange, "github_issues": github}


def search_all(q, timeout=10):
    """Parallel bounded fetch. Returns {source: {status, items, error}}."""
    out = {}

    def run(name):
        try:
            st, items = FETCHERS[name](q, timeout)
            return name, {"status": st, "items": [i for i in items if i.get("url")], "error": None if st == 200 else f"HTTP {st}"}
        except Exception as e:  # noqa: BLE001 - an outage is data for the coverage gate
            return name, {"status": 0, "items": [], "error": type(e).__name__}

    with ThreadPoolExecutor(max_workers=3) as ex:
        for name, res in ex.map(run, FETCHERS):
            out[name] = res
    try:
        st, items = wikipedia(q, timeout)
        out["wikipedia"] = {"status": st, "items": items, "error": None if st == 200 else f"HTTP {st}", "background_only": True}
    except Exception as e:  # noqa: BLE001
        out["wikipedia"] = {"status": 0, "items": [], "error": type(e).__name__, "background_only": True}
    return out


def fetch_founder_url(ctx, url, claim, timeout=10):
    """DIS-5: fetch and register a founder-supplied URL; a URL that does not load is not registered."""
    if not re.match(r"^https?://", url or ""):
        return None
    try:
        st, body = _get(url, timeout)
    except Exception:  # noqa: BLE001
        st, body = 0, ""
    if st != 200:
        ctx.log("researcher", "founder_url_not_registered", sources=[], url_status=st)
        return None
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
    sid = register(ctx, url=url, source="founder", status=st, title=title.group(1) if title else url,
                   excerpt=f"Founder claim: {claim}. Page text: {clean(body, 400)}")
    ctx.log("researcher", "register_founder_evidence", sources=[url], source_id=sid)
    return sid


def page_contains(url, needle, timeout=10):
    """Used by the pricer: does the fetched page load, and does it show the quoted price?"""
    try:
        st, body = _get(url, timeout)
    except Exception:  # noqa: BLE001
        return 0, False, ""
    return st, (needle in body) if st == 200 else False, clean(body, 300)
