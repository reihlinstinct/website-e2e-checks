"""Two-way doc-vs-code check for the environment-variable surface.

Every environment variable the code reads must be documented, and every
variable the docs present as configuration must be read by the code.
Stdlib only, offline. CI plumbing under scripts/ci/ is out of scope: it reads
the runner's own environment, not user configuration.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_FILES = [ROOT / "README.md"] + sorted((ROOT / "docs").rglob("*.md"))
ALLOWLIST = ROOT / ".github" / "docs-vs-code-allowlist.txt"
ENV_RE = re.compile(
    r"""os\.environ(?:\.get)?\[\s*["']([A-Z][A-Z0-9_]+)["']\s*\]"""
    r"""|os\.environ\.get\(\s*["']([A-Z][A-Z0-9_]+)["']"""
    r"""|os\.getenv\(\s*["']([A-Z][A-Z0-9_]+)["']"""
)
SPAN_RE = re.compile(r"```[^\n]*\n(.*?)```|`([^`\n]+)`", re.S)
ASSIGN_RE = re.compile(r"\b([A-Z][A-Z0-9_]{2,})=")


def _allowlist() -> dict[str, str]:
    out: dict[str, str] = {}
    if ALLOWLIST.is_file():
        for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            token, _, reason = line.partition("#")
            token = token.strip()
            assert reason.strip(), f"allowlist entry without a reason: {line}"
            out[token] = reason.strip()
    return out


def code_env() -> set[str]:
    out: set[str] = set()
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith("scripts/ci/") or ".git/" in rel:
            continue
        for m in ENV_RE.finditer(path.read_text(encoding="utf-8")):
            token = next(g for g in m.groups() if g)
            if token.startswith(("GITHUB_", "RUNNER_")) or token == "CI":
                continue
            out.add(token)
    return out


def doc_env(text: str) -> set[str]:
    """Variables the docs present as configuration: backticked UPPER_SNAKE
    tokens anywhere, plus NAME=value assignments in code spans and fences."""
    out = set(re.findall(r"`([A-Z][A-Z0-9_]{2,})`", text))
    for m in SPAN_RE.finditer(text):
        span = m.group(1) if m.group(1) is not None else m.group(2)
        out.update(ASSIGN_RE.findall(span))
    return out


def test_every_env_var_is_documented():
    text = "\n".join(p.read_text(encoding="utf-8") for p in DOC_FILES)
    allowed = _allowlist()
    missing = sorted(t for t in code_env() if f"`{t}`" not in text and t not in allowed)
    assert not missing, f"environment variables missing from docs: {missing}"


def test_every_documented_var_exists():
    known = code_env() | set(_allowlist())
    stale: set[str] = set()
    for doc in DOC_FILES:
        for token in doc_env(doc.read_text(encoding="utf-8")):
            if token not in known:
                stale.add(f"{doc.relative_to(ROOT)}: {token}")
    assert not stale, f"documented variables missing from code: {sorted(stale)}"


def test_doc_env_catches_fake_var_in_fence():
    fence = "```bash\nTOTALLY_FAKE_VAR=1 pytest -q\n```\n"
    assert "TOTALLY_FAKE_VAR" in doc_env(fence)


def test_doc_env_catches_fake_var_inline():
    assert "TOTALLY_FAKE_VAR" in doc_env("`TOTALLY_FAKE_VAR=1 pytest -q`")
