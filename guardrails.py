"""Deterministic guardrails (SRS GRD-1 to GRD-4, SAFE-1 to SAFE-6, DIS-1).

`check(text)`          content produced by a model (landing page, product, posts, replies).
`check_request(text)`  a founder or tester request ("write 50 five-star reviews").
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


PRODUCE = r"(write|writ\w+|generate|create|make|draft|give me|produce|compose|craft|come up with|invent|fabricate|add|put|include|insert|post|publish|prepare|whip up|spin up|mock up|fill in|show)"
PROOF = (r"(reviews?|testimonials?|endorsements?|ratings?|star ratings?|praise|success stories"
         r"|(customer|user|buyer|client|bride|planner)s?'?\s+(quotes?|feedback|comments|stories|statements)"
         r"|feedback quotes?|quotes? from (happy |real |satisfied )?(customers|users|buyers|clients|people))")

CONTENT_RULES = [
    ("income_promise", r"\bguarantee[sd]?\b|\bguaranteeing\b"),
    ("income_promise", r"\b(promis\w*|ensur\w*)\b[^.\n]{0,40}\b(income|earn\w*|profit\w*|revenue|money|sales|success|results)\b"),
    ("income_promise", r"\b(earn|make|making|generate)\b[^.\n]{0,25}\$\s?\d"),
    ("income_promise", r"\$\s?\d[\d,]*(\.\d+)?\s*(k\b)?\s*(/|per|a|every)\s*(month|mo|week|day|year)\b"),
    ("income_promise", r"\b(passive income|get rich|financial freedom|quit your (day )?job|six[- ]figure|risk[- ]free)\b"),
    ("income_promise", r"\b(make|earn|win|get)\s+(back|your money back)\b[^.\n]{0,40}\b(price|cost|money|investment|first)\b|\bpays? for itself\b|\brecoup\w*\b|\bearn back\b"),
    ("income_promise", r"\b(you|you'll|you will|buyers?|planners?)\b[^.\n]{0,20}\b(could|can|will)\s+(easily\s+)?(make|earn|double|triple|grow)\b[^.\n]{0,30}\b(money|income|revenue|sales|bookings|clients|price|profit)\b"),
    ("fake_social_proof", r"\btestimonials?\b|\bendorsements?\b"),
    ("fake_social_proof", r"\b(\d+|five|four)[- ]stars?\b|★"),
    ("fake_social_proof", r"\brated\s+\d(\.\d)?\b|\b\d(\.\d)?\s*/\s*5\b|\b\d(\.\d)?\s+out of\s+5\b"),
    ("fake_social_proof", r"\b(customer|user|client)\s+reviews?\b|\breviews?\s+from\b|\bwhat (our )?(customers|users|clients|planners|buyers) (say|are saying)\b"),
    ("fake_social_proof", r"[\"“][^\"”\n]{3,240}[\"”]\s*[-–—]\s*(?-i:[A-Z][a-z]+)"),
    ("fake_social_proof", r"(?-i:[-–—]\s*[A-Z][a-z]+\s+[A-Z]\.?,\s*[A-Z][a-z]+)"),
    ("fake_social_proof", r"\b(as (seen|featured) (in|on)|featured (in|on|by)|as heard on)\b"),
    ("fake_social_proof", r"\b(loved|trusted|chosen|preferred|adored|recommended)\s+by\s+(\d|thousands|hundreds|many|countless|top|leading|wedding|planners|brides|customers|users|professionals|experts|teams)"),
    ("fake_social_proof", r"\b(best|#1|number one|top[- ]rated|most popular|award[- ]winning)\b[^.\n]{0,20}\b(template|pack|product|kit|tool|planner|checklist)s?\b[^.\n]{0,10}\b(ever|available|on the market)\b|\bbest\s+\w+\s+ever\b"),
    ("fake_signup_count", r"\b\d[\d,]*\+?\s+(happy\s+)?(people|users|founders|customers|planners|members|students|subscribers|buyers)\b[^.\n]{0,30}\b(joined|signed|registered|use|trust|love|bought|already)\b"),
    ("fake_signup_count", r"\bjoin\s+(over\s+|more than\s+)?\d[\d,]*\b"),
    ("fake_signup_count", r"\b\d[\d,]*\+?\s+(\w+\s+){0,2}(already\s+|have\s+|has\s+)?(signed up|joined|registered|subscribed|bought|pre-?ordered|downloaded)\b"),
    ("urgency", r"\bcountdown\b|\bcountdown timer\b"),
    ("urgency", r"\bonly\s+\d+\s+(left|spots?|seats?|copies|places)\b|\b(offer|sale|deal|price)\s+ends\b"),
    ("urgency", r"\blimited[- ]time\b|\bhurry\b|\bact now\b|\blast chance\b|\bbefore it'?s gone\b|\bdon'?t miss out\b|\bselling fast\b|\b(ends|expires) (tonight|today|soon|at midnight)\b"),
    ("impersonation", r"\bas a (customer|user|client|buyer)\b[^.\n]{0,20}\bI\b"),
    ("impersonation", r"\bI (love|loved|bought|use|used|recommend)\s+(this|it|these)\b"),
    ("impersonation", r"\b(official|endorsed by|partnered with|in partnership with|approved by|certified by)\s+(notion|google|microsoft|apple|etsy|canva|amazon|gumroad)\b"),
]

REQUEST_RULES = [
    ("fake_social_proof", r"\b" + PRODUCE + r"\b[^\n]{0,60}\b" + PROOF + r"\b"),
    ("fake_social_proof", r"\b(fake|made[- ]up|invented|fictional|fabricated|pretend|synthetic|glowing|5[- ]star|five[- ]star)\b[^.\n]{0,30}\b(reviews?|testimonials?|endorsements?|ratings?|feedback|quotes?|sign[- ]?ups?|followers|users|customers|buyers)\b"),
    ("fake_social_proof", r"\b(present|pass|show|label|frame|disguise)\w*\b[^.\n]{0,30}\b(them|it|these|this)?\s*(off\s+)?as\s+(genuine|real|authentic|actual|verified)\b|\b(genuine|real|authentic|verified)\s+(buyer|customer|user|client)s?\b[^.\n]{0,20}\b(feedback|reviews?|quotes?|comments)\b"),
    ("fake_signup_count", r"\b(inflate|invent|make up|fabricate|pad|boost|bump|round up)\b[^.\n]{0,30}\b(sign[- ]?ups?|numbers|counts?|users|waitlist|results|metrics|stats)\b"),
    ("fake_signup_count", r"\b(add|put|say|claim|state|show|write)\b[^.\n]{0,30}\b\d[\d,]*\s+(people|users|customers|sign[- ]?ups?|planners|members|buyers|subscribers|students|founders)\b"),
    ("income_promise", r"\b(promise|guarantee|assure|tell (them|users|buyers|customers|planners) (they will|they'll))\b[^.\n]{0,40}(\$|income|earn|money|profit|results|success|month|bookings|clients|back)"),
    ("income_promise", r"\b" + PRODUCE + r"\b[^.\n]{0,40}\b(make back|earn back|pays? for itself|recoup|easy money|passive income|guaranteed)\b"),
    ("urgency", r"\b(add|include|put|create|show|insert|use|build)\b[^.\n]{0,30}\b(countdown|timer|urgency|scarcity|only \d+ left|limited[- ]time|fake deadline|deadline pressure)\b"),
    ("urgency", r"\b(make|create)\b[^.\n]{0,20}\b(people|buyers|them|visitors)\b[^.\n]{0,20}\b(panic|rush|hurry|feel urgency|fomo)\b"),
    ("payment", r"\b(charge|bill|debit)\b[^.\n]{0,20}\b(my|the|their|a|his|her)?\s*(card|customer|account|buyer|user)s?\b"),
    ("payment", r"\b(process|take|collect|run|accept)\b[^.\n]{0,15}\b(real |live )?(payment|card|charge)s?\b|\bsandbox payment|\btest[- ]mode payment|\bsandbox mode\b|\bstripe test\b"),
    ("money_movement", r"\b(refund|transfer|send|wire|move|withdraw|pay out)\b[^.\n]{0,25}\b(money|funds|\$\d|payment|payout|the customer|to my bank)\b"),
    ("credentials", r"\b(store|save|keep|remember|log|collect)\b[^.\n]{0,25}\b(passwords?|card numbers?|credit cards?|cvv|credentials|logins?)\b"),
    ("account_creation", r"\b(create|open|register|sign up for|set up)\b[^.\n]{0,15}\b(an? )?(accounts?|stripe|paypal|bank)\b"),
    ("bypass", r"\b(skip|bypass|disable|ignore|turn off|override)\b[^.\n]{0,20}\b(tests?|checks?|gates?|approval|guardrails?|qa|rules?)\b"),
    ("impersonation", r"\b(pretend|pose|posing|act|write|post|reply|comment|sign)\w*\b[^.\n]{0,15}\b(as|to be)\b[^.\n]{0,15}\b(the founder|me|a customer|a real customer|a user|a buyer|a bride|another brand|notion|google|apple)\b"),
    ("impersonation", r"\b(pretend|pose|act|role-?play)\w*\s+(you are|you're|to be|that you are|as)\b[^.\n]{0,40}\b(reply|replies|post|comment|write|review|email|message|thread|forum|dm|tweet|sign)\w*\b"),
    ("impersonation", r"\bimpersonat\w*\b|\bas if (i|we) (were|was|am) (a |an |the )?(customer|buyer|user|client|bride|fan)\b|\bfrom my (personal )?account\b|\bin the voice of (a |an |the )?(customer|buyer|user|client|bride)\b|\bsock ?puppet\w*\b|\bfake (account|profile|persona)s?\b"),
    ("publish_without_approval", r"\b(publish|post|send|email|tweet)\b[^.\n]{0,30}\bwithout\b[^.\n]{0,15}\b(approval|asking|review|me|checking)\b|\bauto[- ]?(publish|post|send)\b"),
    ("paywall", r"\b(paywall|lock|hide)\b[^.\n]{0,25}\b(core|main|basic)\s+features?\b"),
    ("fake_signup_count", r"\b(fake|dummy|made[- ]up|invented|bot|placeholder|test)\s+(e-?mails?|sign[- ]?ups?|accounts?|entries|subscribers|leads|visitors|traffic|orders|sales)\b"),
    ("fake_signup_count", r"\b(fill|pad|seed|stuff|populate)\b[^.\n]{0,25}\b(waitlist|sign[- ]?ups?|results form|metrics|tracking sheet)\b"),
    ("gate_tampering", r"\b(change|lower|reduce|edit|move|adjust|relax|drop)\b[^.\n]{0,30}\b(target|threshold|goal|bar|criteria)\b[^.\n]{0,40}\b(pass|go|green|succeed|looks? better|so (we|it))\b"),
    ("gate_tampering", r"\b(mark|set|force|flip|make)\b[^.\n]{0,25}\b(gate|verdict|outcome|decision|result)s?\b[^.\n]{0,15}\b(as\s+|to\s+)?(go|pass(ed)?|green|approved|success)\b"),
    ("gate_tampering", r"\b(ignore|forget|disregard)\s+(all\s+|your\s+|the\s+)?(previous|prior|above|earlier|system)\s+(instructions|rules|prompts?)\b|\b(ignore|forget|disregard)\s+(all\s+)?(your|the|these|our)\s+(rules|guardrails|instructions|limits)\b"),
    ("income_promise", r"\b(promise|guarantee|assure)\w*\b[^.\n]{0,40}\b(save|saves|hours|double|triple|will (get|land|win|book|find))\b"),
    ("approval_forgery", r"\b(approve|sign off|accept)\b[^.\n]{0,20}\b(it|this|everything|all)\b[^.\n]{0,20}\b(for me|on my behalf|automatically|yourself)\b|\b(as|on behalf of) the founder\b[^.\n]{0,20}\bapprove\b"),
    ("fake_social_proof", r"\b(glowing|happy|positive|raving|rave|satisfied|enthusiastic|delighted|five-star|5-star)\b[^.\n]{0,25}\b(blurbs?|quotes?|reviews?|feedback|comments|stories|shout-?outs?|words)\b"),
    ("income_promise", r"\b(definitely|certainly|surely|for sure|guaranteed to|always)\b[^.\n]{0,30}\b(get|make|earn|win|land|double|bring|grow|increase|book)\b[^.\n]{0,25}\b(clients|customers|money|income|sales|bookings|revenue|more)\b"),
    ("impersonation", r"\bpretend\w*\b[^.\n]{0,30}\b(you|we|i)?\s*(bought|purchased|used|tried|own|are a|were a|a customer|a buyer|happy)\b"),
    ("publish_without_approval", r"\b(send|post|publish|tweet|launch|email)\b[^.\n]{0,50}\b(no need to|don'?t|do not|without)\b[^.\n]{0,20}\b(check|ask|approv\w*|confirm|review)\w*\b"),
    ("credentials", r"\b(store|save|keep|remember|log|collect)\b[^.\n]{0,25}\b(card|payment|billing|bank)\s+(details|info|information|data)\b"),
]

# A purely educational question about a banned practice is allowed (GRD-4), but only when the text
# contains no instruction to produce or change anything. "What is a countdown timer? Add one" is
# refused because "add" is an instruction.
QUESTION = re.compile(r"^\s*(explain|why|what|how|is it|is|are|should|describe|tell me why|summari[sz]e|list the rules|which|when|who)\b", I)
INSTRUCTION = re.compile(r"\b" + PRODUCE + r"\b|\b(then|now|also|please)\b[^.\n?]{0,20}\b(do|use|apply)\b", I)
RULE_EXPLANATION = re.compile(
    r"(?:why (?:does the system|do you) refuse to (?:write|create|generate) "
    r"(?:(?:fake|fabricated) )?(?:testimonials?|reviews?)"
    r"|what would make the (?:phase [1-6] )?gate (?:say|return) (?:go|pass))\?",
    I,
)

DIGITAL = r"(guide|course|template|ebook|e-book|checklist|toolkit|workbook|spreadsheet|tracker|planner|pack|bundle|kit|class|newsletter|notion|printable|swipe file|sop)s?"
EXCLUDED = [
    ("financial_or_crypto", r"\b(crypto\w*|bitcoin|ethereum|blockchain token|nft|defi|forex|day[- ]?trad\w*|trading (signals?|bot|strateg\w*|course|system)|trade (stocks|options|futures|currencies)|stocks|stock (market|picks?|tips|signals?)|options trading|investing|investment (advice|signals?|fund|product|portfolio)s?|invest(ing)? for you|portfolio (advice|management)|loans?|lending|credit score repair|insurance product|robo[- ]?advis\w*|tax advice|retirement planning)\b"),
    ("health_advice", r"\b(medical|diagnos\w*|symptom\w*|treatment plans?|therapy|therapist|mental health advice|supplements?|diet plans?|nutrition plans?|workout plans?|fitness plans?|weight loss|prescriptions?|dosage|telehealth|health advice|cure|heal(s|ing)? (your|anxiety|depression))\b"),
    ("legal_advice", r"\b(legal advice|lawyer|attorney|legal opinion|contract review service|immigration advice|lawsuit|legal counsel|legal documents?|legal templates?|wills|last will)\b|\b(write|writes|draft|drafts|generate|generates|review|reviews)\b[^.\n]{0,25}\bcontracts?\b"),
    ("physical_goods", r"\b(handmade|leather|wallets?|t-?shirts?|merch(andise)?|furniture|jewel(le)?ry|candles?|cosmetics|clothing|shoes|physical (product|goods)|dropshipping|print[- ]on[- ]demand|food delivery|baked goods|hardware device)\b"),
]


NEGATION = re.compile(r"\b(not|no|never|cannot|can't|don't|doesn't|won't|without|nor)\b[^.\n]{0,30}$", I)


def _scan(text, rules):
    text = text or ""
    for rule, pat in rules:
        for m in re.finditer(pat, text, I):
            # A digital product ABOUT a physical topic ("a guide to selling handmade jewelry") is allowed;
            # financial, health and legal topics stay excluded whatever the format.
            if rule == "physical_goods" and re.search(r"\b" + DIGITAL + r"\b", text[:m.start()], I):
                continue
            # "We do not guarantee income" is an honest disclaimer, not a promise.
            if rule in ("income_promise", "fake_social_proof", "urgency") and NEGATION.search(text[max(0, m.start() - 40):m.start()]):
                continue
            return Refusal(rule, m.group(0)[:80])
    return None


def check(text):
    """Content check for anything a model produced. Returns a Refusal or None."""
    return _scan(text, CONTENT_RULES)


def check_request(text):
    """Request check for founder or tester instructions (trick prompts)."""
    text = (text or "").strip()
    if RULE_EXPLANATION.fullmatch(text):
        return None
    if QUESTION.search(text) and not INSTRUCTION.search(text):
        return None
    # An instruction to build, sell or advise in an excluded category is refused here too, so a trick
    # prompt cannot route around the Phase 1 exclusion check.
    return _scan(text, REQUEST_RULES) or _scan(text, CONTENT_RULES) or _scan(text, EXCLUDED)


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
