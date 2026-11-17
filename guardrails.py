"""Deterministic guardrails (SRS GRD-1 to GRD-4, SAFE-1 to SAFE-6, DIS-1).

`check(text)`          content produced by a model (landing page, product, posts, replies).
`check_request(text)`  a founder or judge request ("write 50 five-star reviews").
`excluded(text)`       excluded product categories (physical goods; financial, investment or
                       crypto; health or legal advice). Never overridable.

Pattern rules can miss paraphrases; the eval set in tests/evals/ measures this and the README
quotes recall and false-positive rate only from its latest run.
"""
import re
from dataclasses import dataclass

I = re.IGNORECASE


@dataclass
class Refusal:
    rule: str
    match: str

    def __str__(self):
        return f"{self.rule}: '{self.match}'"


CONTENT_RULES = [
    ("income_promise", r"\bguarantee[sd]?\b|\bguaranteeing\b"),
    ("income_promise", r"\b(promis\w*|ensur\w*)\b[^.\n]{0,40}\b(income|earn\w*|profit\w*|revenue|money|sales|success|results)\b"),
    ("income_promise", r"\b(earn|make|making|generate)\b[^.\n]{0,25}\$\s?\d"),
    ("income_promise", r"\$\s?\d[\d,]*(\.\d+)?\s*(k\b)?\s*(/|per|a|every)\s*(month|mo|week|day|year)\b"),
    ("income_promise", r"\b(passive income|get rich|financial freedom|quit your (day )?job|six[- ]figure|risk[- ]free)\b"),
    ("fake_social_proof", r"\btestimonials?\b"),
    ("fake_social_proof", r"\b(\d+|five|four)[- ]stars?\b|★"),
    ("fake_social_proof", r"\brated\s+\d(\.\d)?\b|\b\d(\.\d)?\s*/\s*5\b|\b\d(\.\d)?\s+out of\s+5\b"),
    ("fake_social_proof", r"\b(customer|user|client)\s+reviews?\b|\breviews?\s+from\b|\bwhat (our )?(customers|users|clients) (say|are saying)\b"),
    ("fake_signup_count", r"\b\d[\d,]*\+?\s+(happy\s+)?(people|users|founders|customers|planners|members|students|subscribers|buyers)\b[^.\n]{0,30}\b(joined|signed|registered|use|trust|love|bought|already)\b"),
    ("fake_signup_count", r"\bjoin\s+(over\s+|more than\s+)?\d[\d,]*\b"),
    ("urgency", r"\bcountdown\b|\bcountdown timer\b"),
    ("urgency", r"\bonly\s+\d+\s+(left|spots?|seats?|copies|places)\b|\b(offer|sale|deal|price)\s+ends\b"),
    ("urgency", r"\blimited[- ]time\b|\bhurry\b|\bact now\b|\blast chance\b|\bbefore it'?s gone\b|\bdon'?t miss out\b"),
    ("impersonation", r"\bas a (customer|user|client|buyer)\b[^.\n]{0,20}\bI\b"),
    ("impersonation", r"\bI (love|loved|bought|use|used|recommend)\s+(this|it|these)\b"),
    ("impersonation", r"\b(official|endorsed by|partnered with|in partnership with)\s+(notion|google|microsoft|apple|etsy|canva|amazon)\b"),
]

REQUEST_RULES = [
    ("fake_social_proof", r"\b(write|generate|create|make|draft|give me|produce)\b[^.\n]{0,40}\b(reviews?|testimonials?|ratings?)\b"),
    ("fake_social_proof", r"\bfake\b[^.\n]{0,20}\b(reviews?|testimonials?|ratings?|sign[- ]?ups?|followers|users)\b"),
    ("fake_signup_count", r"\b(inflate|invent|make up|fabricate|pad)\b[^.\n]{0,30}\b(sign[- ]?ups?|numbers|counts?|users|waitlist|results)\b"),
    ("fake_signup_count", r"\b(add|put|say|claim)\b[^.\n]{0,30}\b\d[\d,]*\s+(people|users|customers|sign[- ]?ups?|planners|members|buyers|subscribers|students|founders)\b"),
    ("income_promise", r"\b(promise|guarantee|tell (them|users|buyers) they will)\b[^.\n]{0,40}(\$|income|earn|money|profit|results|success|month)"),
    ("urgency", r"\b(add|include|put|create)\b[^.\n]{0,30}\b(countdown|timer|urgency|scarcity|only \d+ left)\b"),
    ("payment", r"\b(charge|bill|debit)\b[^.\n]{0,20}\b(my|the|their|a|his|her)?\s*(card|customer|account|buyer|user)s?\b"),
    ("payment", r"\b(process|take|collect|run)\b[^.\n]{0,15}\b(payment|card|charge)s?\b|\bsandbox payment|\btest[- ]mode payment"),
    ("money_movement", r"\b(refund|transfer|send|wire|move|withdraw|pay out)\b[^.\n]{0,25}\b(money|funds|\$\d|payment|payout|the customer|to my bank)\b"),
    ("credentials", r"\b(store|save|keep|remember|log)\b[^.\n]{0,25}\b(passwords?|card numbers?|credit cards?|cvv|credentials)\b"),
    ("account_creation", r"\b(create|open|register|sign up for)\b[^.\n]{0,15}\b(an? )?(accounts?|stripe|paypal|bank)\b"),
    ("bypass", r"\b(skip|bypass|disable|ignore|turn off)\b[^.\n]{0,20}\b(tests?|checks?|gates?|approval|guardrails?|qa)\b"),
    ("impersonation", r"\b(pretend|pose|act|write|post)\b[^.\n]{0,15}\b(as|to be)\b[^.\n]{0,15}\b(the founder|me|a customer|a real customer|a user|another brand|notion|google|apple)\b"),
    ("impersonation", r"\bimpersonat\w*\b"),
    ("publish_without_approval", r"\b(publish|post|send|email|tweet)\b[^.\n]{0,30}\bwithout\b[^.\n]{0,15}\b(approval|asking|review|me)\b"),
    ("paywall", r"\b(paywall|lock|hide)\b[^.\n]{0,25}\b(core|main|basic)\s+features?\b"),
]

# Educational or analytical requests about banned practices are allowed (GRD-4).
EDUCATIONAL = re.compile(
    r"^\s*(explain|why|what|how (do|does|can|could)|is it|are|should|describe|tell me why|summari[sz]e|list the rules|which)\b"
    r"(?![^.\n]{0,60}\b(then|and) (write|generate|create|make)\b)", I)

EXCLUDED = [
    ("financial_or_crypto", r"\b(crypto\w*|bitcoin|ethereum|blockchain token|nft|defi|forex|day[- ]?trading|trading (signals?|bot)|stock (picks?|tips|signals?)|investment (advice|signals?|fund|product)|invest(ing)? for you|loans?|lending|credit score repair|insurance product|robo[- ]?advis\w*|tax advice)\b"),
    ("health_advice", r"\b(medical|diagnos\w*|symptom\w*|treatment plans?|therapy|therapist|mental health advice|supplements?|diet plans?|meal plans?|nutrition plans?|workout plans?|fitness plans?|weight loss|prescriptions?|dosage|telehealth|health advice)\b"),
    ("legal_advice", r"\b(legal advice|lawyer|attorney|legal opinion|contract review service|immigration advice|lawsuit|legal counsel)\b"),
    ("physical_goods", r"\b(handmade|leather|wallets?|t-?shirts?|merch(andise)?|furniture|jewel(le)?ry|candles?|cosmetics|clothing|shoes|physical (product|goods)|dropshipping|print[- ]on[- ]demand|food delivery|baked goods|hardware device)\b"),
]


NEGATION = re.compile(r"\b(not|no|never|cannot|can't|don't|doesn't|won't|without|nor)\b[^.\n]{0,30}$", I)


def _scan(text, rules):
    text = text or ""
    for rule, pat in rules:
        for m in re.finditer(pat, text, I):
            # "We do not guarantee income" is an honest disclaimer, not a promise.
            if rule in ("income_promise", "fake_social_proof", "urgency") and NEGATION.search(text[max(0, m.start() - 40):m.start()]):
                continue
            return Refusal(rule, m.group(0)[:80])
    return None


def check(text):
    """Content check for anything a model produced. Returns a Refusal or None."""
    return _scan(text, CONTENT_RULES)


def check_request(text):
    """Request check for founder/judge instructions (trick prompts)."""
    text = text or ""
    if EDUCATIONAL.search(text):
        return None
    return _scan(text, REQUEST_RULES) or _scan(text, CONTENT_RULES)


def excluded(text):
    """Returns a Refusal naming the excluded category, or None."""
    return _scan(text, EXCLUDED)


def stamp_override(text):
    banner = "UNVALIDATED · FOUNDER OVERRIDE"
    return text if text.startswith(banner) else banner + "\n\n" + text


def check_obj(obj):
    """Run check() over every string in a nested object; return the first Refusal."""
    if isinstance(obj, str):
        return check(obj)
    if isinstance(obj, dict):
        for v in obj.values():
            r = check_obj(v)
            if r:
                return r
    if isinstance(obj, list):
        for v in obj:
            r = check_obj(v)
            if r:
                return r
    return None
