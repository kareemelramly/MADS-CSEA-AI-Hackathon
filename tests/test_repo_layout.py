"""Repository layout required by CLAUDE.md (SRS TEST-5, REPO-1 to REPO-10)."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_H = ["Quickstart", "What works and what is mocked", "Architecture", "Models and free resources", "Cost per run",
            "Demo video", "What our system will NOT do", "How the project stays alive after the hackathon"]
ARCH_H = ["Overview", "Phases", "Gates", "Sale to cash", "Data flow", "Built vs. stubbed", "Roadmap"]


def read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


def h2(text):
    return [l[3:].strip() for l in text.splitlines() if l.startswith("## ")]


def test_license_is_full_mit():
    t = read("LICENSE")
    assert t.startswith("MIT License") and "THE SOFTWARE IS PROVIDED \"AS IS\"" in t and "Permission is hereby granted" in t


def test_readme_headings_and_quickstart():
    t = read("README.md")
    assert h2(t) == README_H
    assert re.search(r"```bash\s*\ndocker compose up\s*\n```", t)
    cost = t.split("## Cost per run")[1].split("\n## ")[0]
    assert "$" in cost


def test_architecture_headings_and_text_diagrams():
    t = read("ARCHITECTURE.md")
    assert h2(t) == ARCH_H
    assert "```mermaid" in t
    assert not re.search(r"!\[[^\]]*\]\(", t)
    for p in ("Discover", "Validate", "Build", "Commercial", "Launch", "Operate"):
        assert re.search(rf"^### .*{p}", t, re.M), p


def test_decision_log_is_list_with_keys():
    data = json.loads(read("decision_log.json"))
    assert isinstance(data, list)
    for e in data:
        for k in ("action", "sources", "model", "cost", "approved_by"):
            assert k in e


def test_env_example_placeholders_only():
    t = read(".env.example")
    for line in t.splitlines():
        if line.endswith("_API_KEY=") or not line.split("=")[0].endswith("_API_KEY"):
            continue
        raise AssertionError(f"key value present: {line.split('=')[0]}")
    assert "nvapi-" not in t


def test_compose_ports_local_and_no_gpt():
    t = read("docker-compose.yml")
    for port in re.findall(r'ports:\s*\[([^\]]*)\]', t):
        assert all(p.strip().strip('"').startswith("127.0.0.1:") for p in port.split(",") if p.strip())
    assert "gpt" not in t.lower() and "REPLACE_WITH" not in t
    assert "gpt" not in read(".env.example").lower()


def test_required_paths_exist():
    for p in ("README.md", "LICENSE", "docker-compose.yml", "decision_log.json", "outputs", "tests", "ARCHITECTURE.md",
              ".env.example", "prompts", "orchestrator.py", "gates.py", "approval.py", "payments.py", "delivery.py",
              "refunds.py", "reconcile.py", "CLAUDE.md"):
        assert os.path.exists(os.path.join(ROOT, p)), p


def test_every_agent_has_a_prompt():
    for f in os.listdir(os.path.join(ROOT, "agents")):
        if f.endswith(".py") and f != "__init__.py":
            assert os.path.exists(os.path.join(ROOT, "prompts", f[:-3] + ".md")), f


def test_gitignore_blocks_secrets_and_binaries():
    t = read(".gitignore")
    for p in (".env", "*.pptx", "*.pdf", "*.sqlite", "state/", "~$*", "*.gguf"):
        assert p in t, p
