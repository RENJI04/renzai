"""Static integrity and privacy checks for the Phase 16 adoption assets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).parents[1]

REQUIRED_SCREENSHOTS = (
    "authentication.png",
    "dashboard.png",
    "security-playground.png",
    "incident-workspace.png",
    "applications.png",
    "policies.png",
    "providers.png",
    "analytics.png",
    "ai-intelligence.png",
    "grafana-overview.png",
)

REQUIRED_ASSETS = (
    "CONTRIBUTING.md",
    "SECURITY.md",
    "compose.demo.yaml",
    "docs/architecture.md",
    "docs/assurance.md",
    "docs/demo-storyboard.md",
    "docs/faq.md",
    "docs/limitations.md",
    "docs/quick-start.md",
    "docs/sdk.md",
    "docs/security/claims-and-non-claims.md",
    "docs/security/security-model.md",
    "docs/security/threat-catalog.md",
    "docs/troubleshooting.md",
    "docs/release/v1-rc-checklist.md",
    "examples/attack-lab/scenarios.json",
    "examples/attack-lab/run.py",
    "examples/bruno/bruno.json",
    "examples/bruno/environments/Local.bru",
    "examples/reference-app/app.py",
    "scripts/prepare_demo_env.py",
    "scripts/reset_demo.py",
    "scripts/seed_demo.py",
)

PUBLIC_TEXT_ROOTS = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "docs",
    ROOT / "examples",
)

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
WINDOWS_LOCAL_PATH = re.compile(r"(?i)(?:[A-Z]:\\|C:/Users/|D:/codex/)")
REAL_EMAIL = re.compile(
    r"(?i)\b(?![\w.+-]+@(?:demo\.invalid|example\.com|example\.org"
    r"|users\.noreply\.github\.com))"
    r"[\w.+-]+@[\w.-]+\.[A-Z]{2,}\b"
)


def verify() -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_ASSETS:
        if not (ROOT / relative).is_file():
            errors.append(f"required asset is missing: {relative}")

    screenshot_dir = ROOT / "docs/assets/screenshots"
    for filename in REQUIRED_SCREENSHOTS:
        path = screenshot_dir / filename
        if not path.is_file() or path.stat().st_size < 1_000:
            errors.append(f"screenshot is missing or unexpectedly small: {filename}")

    errors.extend(_verify_attack_lab())
    errors.extend(_verify_architecture())
    errors.extend(_verify_bruno())
    errors.extend(_verify_markdown_links())
    errors.extend(_verify_public_privacy())
    return errors


def _verify_attack_lab() -> list[str]:
    errors: list[str] = []
    path = ROOT / "examples/attack-lab/scenarios.json"
    if not path.is_file():
        return errors
    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = payload if isinstance(payload, list) else payload.get("scenarios", [])
    if not isinstance(scenarios, list):
        return ["Attack Lab scenarios must be a list"]
    categories: dict[str, set[str]] = {}
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            errors.append("Attack Lab contains a non-object scenario")
            continue
        category = scenario.get("category")
        expectation = scenario.get("kind")
        if isinstance(category, str) and isinstance(expectation, str):
            categories.setdefault(category, set()).add(expectation)
    if len(categories) != 11:
        errors.append(f"Attack Lab covers {len(categories)} categories instead of 11")
    for category, expectations in categories.items():
        if not {"malicious", "benign_control"}.issubset(expectations):
            errors.append(f"Attack Lab category lacks malicious/benign controls: {category}")
    scenario_text = json.dumps(scenarios, ensure_ascii=False).casefold()
    for marker in ("base64", "percent", "zero-width", "html"):
        if marker not in scenario_text:
            errors.append(f"Attack Lab lacks an encoded/obfuscated marker: {marker}")
    return errors


def _verify_architecture() -> list[str]:
    path = ROOT / "docs/architecture.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    count = text.count("```mermaid")
    if count < 8:
        return [f"architecture documentation has {count} Mermaid diagrams instead of at least 8"]
    if text.count("```") % 2:
        return ["architecture documentation has an unbalanced fenced block"]
    return []


def _verify_bruno() -> list[str]:
    errors: list[str] = []
    bruno_root = ROOT / "examples/bruno"
    collection_path = bruno_root / "bruno.json"
    if collection_path.is_file():
        collection = json.loads(collection_path.read_text(encoding="utf-8"))
        if collection.get("version") != "1":
            errors.append("Bruno collection version must be 1")
    requests = sorted(bruno_root.rglob("*.bru"))
    if len(requests) < 13:
        errors.append(f"Bruno collection has only {len(requests)} request/environment files")
    for path in requests:
        text = path.read_text(encoding="utf-8")
        if path.parent.name != "environments" and "meta {" not in text:
            errors.append(f"Bruno request lacks metadata: {path.relative_to(ROOT)}")
        if re.search(r"(?im)^\s*(?:apiKey|password|session|csrf)\s*:\s*[^\s{]", text):
            errors.append(
                f"Bruno asset contains a populated secret variable: {path.relative_to(ROOT)}"
            )
    return errors


def _verify_markdown_links() -> list[str]:
    errors: list[str] = []
    for path in _public_text_files("*.md"):
        text = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith(("#", "mailto:")):
                continue
            local = (path.parent / unquote(parsed.path)).resolve()
            if not local.exists():
                errors.append(
                    f"broken local Markdown link in {path.relative_to(ROOT)}: {raw_target}"
                )
    return errors


def _verify_public_privacy() -> list[str]:
    errors: list[str] = []
    for path in _public_text_files("*"):
        if path.suffix.casefold() not in {".md", ".json", ".py", ".bru", ".yml", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        if WINDOWS_LOCAL_PATH.search(text):
            errors.append(f"public asset exposes a local Windows path: {relative}")
        emails = sorted(set(REAL_EMAIL.findall(text)))
        if emails:
            errors.append(f"public asset contains a non-reserved email in {relative}: {emails}")
    return errors


def _public_text_files(pattern: str) -> list[Path]:
    files: set[Path] = set()
    for root in PUBLIC_TEXT_ROOTS:
        if root.is_file():
            files.add(root)
        elif root.is_dir():
            files.update(path for path in root.rglob(pattern) if path.is_file())
    return sorted(files)


def main() -> int:
    errors = verify()
    if errors:
        for error in errors:
            print(f"Phase 16 asset error: {error}", file=sys.stderr)
        return 1
    print("Phase 16 adoption assets verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
