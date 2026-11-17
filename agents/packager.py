"""Packager (Phase 3, no model call). Builds the release manifest with SHA-256 per file; the
release approval binds the canonical manifest, so any change after approval is refused (BLD-7)."""
import json


def manifest(ctx, roles):
    files = []
    for role in roles:
        a = ctx.final(role["name"], role["ext"])
        files.append({"role": role["role"], "path": a["path"], "sha256": a["sha256"]})
    m = {"run_id": ctx.run_id, "product": ctx.handoffs["H1"]["idea_name"], "archetype": "A1",
         "product_type": "checklist", "delivery_format": {"kind": "download", "file_types": ["md", "csv", "txt"]},
         "license": "MIT", "files": files, "validation_status": ctx.validation_status}
    return m, json.dumps(m, sort_keys=True, separators=(",", ":"))
