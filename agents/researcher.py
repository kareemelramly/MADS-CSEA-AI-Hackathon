"""Researcher (Phase 1, Core step: find opportunities). No model call: exclusion check, criteria
logged before search, bounded parallel search, registry, coverage counts.

Routine:
1. Exclusion check on the brief; excluded -> return early (gate gives a non-overridable stop).
2. Log `define_research_criteria` with every threshold BEFORE the first search (DIS-2).
3. Search HN Algolia, Stack Exchange and GitHub issues in parallel; Wikipedia for background only.
4. If coverage is thin, one automatic retry with broadened terms (DIS-6).
5. Drop items without a URL, register every item with a source ID, and count identical or
   near-identical excerpts (Jaccard >= 0.85) once, so duplicates cannot inflate the evidence count.
6. Fetch and register founder evidence URLs; a URL that does not load is not registered.
"""
import re

import config
import guardrails
import sources

REQUIRED = ("idea", "skills", "budget_amount", "hours_per_week", "target_market", "values")


def missing_fields(brief):
    return [f for f in REQUIRED if brief.get(f) in (None, "", [])]


def thresholds():
    return {"min_sources_ok": config.discover_min_sources_ok(),
            "min_items_screened": config.discover_min_items_screened(),
            "min_relevant": config.discover_min_relevant(), "min_relevant_sources": 2,
            "min_fit": config.discover_min_fit(), "fit_weights": "skills 35, budget 25, time 25, values 15",
            "max_excerpts_to_model": 20, "broadened_retries": 1}


def run(ctx):
    brief = ctx.brief
    th = thresholds()
    exc = guardrails.excluded(" ".join(str(brief.get(k, "")) for k in ("idea", "target_market")))
    if exc:
        ctx.log("researcher", "exclusion_check", outcome="excluded", category=exc.rule, match=exc.match)
        return {"excluded": exc.rule, "thresholds": th}
    ctx.log("researcher", "exclusion_check", outcome="allowed")
    miss = missing_fields(brief)
    if miss:
        ctx.log("researcher", "brief_incomplete", missing=miss)
        return {"missing": miss, "thresholds": th}
    ctx.log("researcher", "define_research_criteria", thresholds=th)

    def attempt(broaden):
        q = sources.query_terms(brief, broaden=broaden)
        res = sources.search_all(q, timeout=max(3, min(10, ctx.time_left() - 5)))
        return q, res

    q, res = attempt(False)
    retry_used = False
    cov = _coverage(res)
    if cov["sources_ok"] < th["min_sources_ok"] or cov["items"] < th["min_items_screened"]:
        retry_used = True
        q2, res2 = attempt(True)
        for k, v in res2.items():
            if v["status"] == 200:
                if res[k]["status"] != 200:
                    res[k] = v
                else:
                    res[k]["items"] += v["items"]
        q = q + " | " + q2
    demand_ids, per_source, seen, dupes = [], {}, [], []
    for name, r in res.items():
        use = "background" if r.get("background_only") else "demand"
        for it in r["items"]:
            if not it.get("url"):
                continue
            sid = sources.register(ctx, url=it["url"], source=name, status=r["status"], title=it.get("title", ""),
                                   excerpt=it.get("excerpt", ""), use=use)
            if use == "demand" and sid not in demand_ids:
                words = _words(it.get("title", "") + " " + it.get("excerpt", ""))
                twin = next((s for s, w in seen if _same(words, w)), None)
                if twin:                      # duplicate text is one piece of evidence, not two
                    dupes.append({"dropped": sid, "duplicate_of": twin})
                    continue
                seen.append((sid, words))
                demand_ids.append(sid)
                per_source[name] = per_source.get(name, 0) + 1
    for ev in brief.get("founder_evidence") or []:
        sid = sources.fetch_founder_url(ctx, ev.get("url"), ev.get("claim", ""))
        if sid and sid not in demand_ids:
            demand_ids.append(sid)
            per_source["founder"] = per_source.get("founder", 0) + 1
    coverage = {"sources_ok": sum(1 for k, r in res.items() if r["status"] == 200 and not r.get("background_only")),
                "items_screened": len(demand_ids), "raw_hits": {k: len(r["items"]) for k, r in res.items()},
                "failed": [f"{k} ({r['error']})" for k, r in res.items() if r["status"] != 200],
                "retry_used": retry_used, "query": q, "duplicates_removed": len(dupes)}
    if dupes:
        ctx.log("researcher", "remove_duplicate_evidence", duplicates=dupes)
    ctx.log("researcher", "search_sources", sources=[ctx.sources[s]["url"] for s in demand_ids[:25]],
            coverage=coverage)
    # Keyword pre-screen in code picks the excerpts the model reads (at most 20).
    terms = set(re.findall(r"[a-z]{4,}", (brief.get("idea", "") + " " + brief.get("search_terms", "")).lower()))
    ranked = sorted(demand_ids, key=lambda s: -len(terms & set(re.findall(r"[a-z]{4,}", ctx.sources[s]["excerpt"].lower()))))
    return {"coverage": coverage, "demand_ids": demand_ids, "to_screen": ranked[:th["max_excerpts_to_model"]],
            "thresholds": th, "per_source": per_source}


def _words(text):
    return set(re.findall(r"[a-z]{2,}|\d+", re.sub(r"<[^>]+>", " ", (text or "").lower())))


def _same(a, b):
    """Identical or near-identical excerpts (Jaccard >= 0.85 on word sets) count once."""
    if not a or not b:
        return False
    return a == b or (min(len(a), len(b)) >= 6 and len(a & b) / len(a | b) >= 0.85)


def _coverage(res):
    ok = sum(1 for r in res.values() if r["status"] == 200 and not r.get("background_only"))
    items = sum(len(r["items"]) for r in res.values() if not r.get("background_only"))
    return {"sources_ok": ok, "items": items}
