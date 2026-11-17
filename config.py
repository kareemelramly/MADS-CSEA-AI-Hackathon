"""Settings read from the environment. Every default here is the value a fresh clone runs with.

Planning values are marked ASSUMPTION in .env.example; they are fixed before a run and never
changed after seeing results.
"""
import os


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return int(default)


def _float(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return float(default)


def get(name, default=""):
    return os.environ.get(name, default)


def state_dir():
    d = os.environ.get("STATE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "state"))
    os.makedirs(d, exist_ok=True)
    return d


def outputs_dir():
    d = os.environ.get("OUTPUTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs"))
    os.makedirs(d, exist_ok=True)
    return d


def decision_log_path():
    return os.environ.get("DECISION_LOG_PATH",
                          os.path.join(os.path.dirname(os.path.abspath(__file__)), "decision_log.json"))


# Model access (SRS 4.2)
def llm_order():
    return [t.strip() for t in os.environ.get("LLM_ORDER", "groq,nvidia,local").split(",") if t.strip()]


def remote_timeout():
    return _float("LLM_REMOTE_TIMEOUT_S", 20)


def local_timeout():
    return _float("LLM_LOCAL_TIMEOUT_S", 300)


def max_attempts():
    return _int("LLM_MAX_ATTEMPTS_PER_CALL", 4)


def min_attempt_s():
    return _float("LLM_MIN_ATTEMPT_S", 5)


def cooldown_default():
    return _float("LLM_COOLDOWN_DEFAULT_S", 60)


def timeout_cooldown():
    return _float("LLM_TIMEOUT_COOLDOWN_S", 30)


def max_tokens():
    return _int("LLM_MAX_TOKENS", 2000)


def workflow_budget():
    return _float("WORKFLOW_TIME_BUDGET_S", 1800)


def run_budget():
    return _float("RUN_TIME_BUDGET_S", 0)


# Thresholds (ASSUMPTION planning values, locked before any run)
def discover_min_sources_ok():
    return _int("DISCOVER_MIN_SOURCES_OK", 2)


def discover_min_items_screened():
    return _int("DISCOVER_MIN_ITEMS_SCREENED", 20)


def discover_min_relevant():
    return _int("DISCOVER_MIN_RELEVANT", 3)


def discover_min_fit():
    return _float("DISCOVER_MIN_FIT", 3.0)


def validate_repeat_floor():
    return _float("VALIDATE_REPEAT_FLOOR", 0.5)


def validate_max_attempts():
    return _int("VALIDATE_MAX_ATTEMPTS", 2)


def validate_target_signups():
    return _int("VALIDATE_TARGET_SIGNUPS", 100)


def validate_target_days():
    return _int("VALIDATE_TARGET_DAYS", 14)


def validate_min_visitors():
    return _int("VALIDATE_MIN_VISITORS", 200)


def max_build_attempts():
    return _int("MAX_BUILD_ATTEMPTS", 3)


def mock_fee_rate():
    return _float("MOCK_FEE_RATE", 0.05)


def mock_token_expiry_hours():
    return _int("MOCK_TOKEN_EXPIRY_HOURS", 24)
