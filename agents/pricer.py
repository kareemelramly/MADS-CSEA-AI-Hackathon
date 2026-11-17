"""Pricer (Phase 4, Core step: set the price and policies; no model call).

Routine: log `define_pricing_criteria` first; take founder-entered competitor quotes (URL,
amount, currency, kind); fetch each URL and register it only if it loads; count only paid
one-time prices in one currency; price = median of at least 3, computed in code. Fewer than 3 ->
`repeat`; an experimental price is possible only by founder override, labelled ASSUMPTION (COM-1).
"""
import statistics

import sources


def criteria():
    return {"method": "median of paid one-time competitor prices", "min_quotes": 3, "same_currency": True,
            "free_items": "counted as comparables, excluded from the median", "subscriptions": "excluded"}


def run(ctx, quotes):
    ctx.log("pricer", "define_pricing_criteria", criteria=criteria())
    verified, rows = [], []
    for q in quotes or []:
        url, amount, cur, kind = q.get("url", ""), q.get("amount"), (q.get("currency") or "").upper(), q.get("kind", "one_time")
        st, shown, _ = sources.page_contains(url, str(q.get("display") or amount)) if url.startswith("http") else (0, False, "")
        sid = None
        if st == 200:
            sid = sources.register(ctx, url=url, source="founder_price_quote", status=st, title=q.get("name", url),
                                   excerpt=f"Founder-entered price {amount} {cur} ({kind}); price text found on page: {shown}")
        row = {"name": q.get("name", ""), "url": url, "amount": amount, "currency": cur, "kind": kind,
               "http_status": st, "registered": sid, "price_text_on_page": shown}
        rows.append(row)
        if sid and kind == "one_time" and isinstance(amount, (int, float)) and amount > 0:
            verified.append(row)
    cur_counts = {}
    for r in verified:
        cur_counts[r["currency"]] = cur_counts.get(r["currency"], 0) + 1
    currency = max(cur_counts, key=cur_counts.get) if cur_counts else None
    same = [r for r in verified if r["currency"] == currency]
    price = round(statistics.median([r["amount"] for r in same]), 2) if len(same) >= 3 else None
    ctx.log("pricer", "compute_price", sources=[r["url"] for r in rows if r["registered"]],
            paid_quotes=len(same), currency=currency, median=price)
    return {"rows": rows, "paid_quotes": len(same), "currency": currency, "price": price}
