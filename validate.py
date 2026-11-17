"""Model-output validation (SRS MOD-7, X3).

1. jsonschema Draft 2020-12: types, enums, minimum/maximum, required fields.
2. Checks the schema cannot express: every `source_ids` entry exists in the run's source
   registry; a claim object with no source ID must be marked `assumption: true`; no URL field.
"""
from jsonschema import Draft202012Validator

URL_KEYS = ("url", "urls", "link", "links", "href")


class BadModelOutput(Exception):
    def __init__(self, path, message):
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


def validate_output(obj, schema, registry_ids=()):
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(obj), key=lambda e: list(e.absolute_path))
    if errors:
        e = errors[0]
        path = "/" + "/".join(str(p) for p in e.absolute_path)
        raise BadModelOutput(path, e.message[:200])
    _refs(obj, set(registry_ids), "")
    return obj


def _refs(node, ids, path):
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}/{k}"
            if k.lower() in URL_KEYS:
                raise BadModelOutput(p, "URL fields are not allowed; cite source_ids instead")
            if k == "source_ids":
                if not isinstance(v, list):
                    raise BadModelOutput(p, "source_ids must be a list")
                for sid in v:
                    if sid not in ids:
                        raise BadModelOutput(p, f"unknown source ID {sid!r}")
                if not v and node.get("assumption") is not True:
                    raise BadModelOutput(path or "/", "claim without source_ids must set assumption: true")
            else:
                _refs(v, ids, p)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _refs(v, ids, f"{path}/{i}")
