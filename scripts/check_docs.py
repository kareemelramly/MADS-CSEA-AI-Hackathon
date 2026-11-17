"""Documentation checks (runbook Step 10): README eight headings, ARCHITECTURE seven headings and
text-only diagrams, a prompt file per agent, Working rows backed by a test name, no text that
addresses reviewers."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_H = ["Quickstart", "What works and what is mocked", "Architecture", "Models and free resources", "Cost per run",
            "Demo video", "What our system will NOT do", "How the project stays alive after the hackathon"]
ARCH_H = ["Overview", "Phases", "Gates", "Sale to cash", "Data flow", "Built vs. stubbed", "Roadmap"]
FORBIDDEN = re.compile(r"\b(dear (judge|reviewer|evaluator)s?|full marks?|give (us|this) (a )?(high|full|top)|please (score|grade|rate) (us|this)|"
                       r"to the (judges|reviewers)|as an ai (judge|grader))\b", re.I)


def headings(path):
    return [l[3:].strip() for l in open(path, encoding="utf-8") if l.startswith("## ")]


def main():
    p = []
    rh = headings(os.path.join(ROOT, "README.md"))
    if rh != README_H:
        p.append(f"README headings {rh}")
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    if not re.search(r"```bash\s*\ndocker compose up\s*\n```", readme):
        p.append("README Quickstart lacks a bash block with exactly `docker compose up`")
    cost = readme.split("## Cost per run")[1].split("\n## ")[0]
    if "$" not in cost:
        p.append("Cost per run has no $ figure")
    ah = headings(os.path.join(ROOT, "ARCHITECTURE.md"))
    if ah != ARCH_H:
        p.append(f"ARCHITECTURE headings {ah}")
    arch = open(os.path.join(ROOT, "ARCHITECTURE.md"), encoding="utf-8").read()
    if re.search(r"!\[[^\]]*\]\(|\.(png|jpg|jpeg|gif|svg|pdf)\)", arch):
        p.append("ARCHITECTURE has image or PDF links")
    if "```mermaid" not in arch:
        p.append("ARCHITECTURE has no Mermaid diagram")
    for f in os.listdir(os.path.join(ROOT, "agents")):
        if f.endswith(".py") and f != "__init__.py" and not os.path.exists(os.path.join(ROOT, "prompts", f[:-3] + ".md")):
            p.append(f"missing prompts/{f[:-3]}.md")
    tests = " ".join(open(os.path.join(ROOT, "tests", f), encoding="utf-8").read() for f in os.listdir(os.path.join(ROOT, "tests")) if f.startswith("test_"))
    for m in re.finditer(r"\|\s*Working\s*\|\s*`?(test_[a-z0-9_]+)", readme):
        if f"def {m.group(1)}" not in tests and not os.path.exists(os.path.join(ROOT, "tests", m.group(1) + ".py")):
            p.append(f"README Working row cites unknown test {m.group(1)}")
    for dirpath, _, fs in os.walk(ROOT):
        if any(x in dirpath for x in (".git", ".venv", "state", "__pycache__", "Claude", "documents", "Phases-Research")):
            continue
        for f in fs:
            if f.endswith((".md", ".py", ".json", ".txt", ".yml", ".html")) and f not in ("CLAUDE.md", "check_docs.py"):
                t = open(os.path.join(dirpath, f), encoding="utf-8", errors="replace").read()
                if FORBIDDEN.search(t):
                    p.append(f"reviewer-addressing text in {os.path.relpath(os.path.join(dirpath, f), ROOT)}")
    for x in p:
        print("FAIL:", x)
    print("OK" if not p else f"{len(p)} problem(s)")
    return 0 if not p else 1


if __name__ == "__main__":
    sys.exit(main())
