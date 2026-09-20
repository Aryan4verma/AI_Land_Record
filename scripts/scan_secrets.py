"""Lightweight repository secret scan.

The scanner examines Git-tracked files and non-ignored working-tree files,
never prints matched content, and returns non-zero on a likely credential.
Ignored local `.env`/tool files are not scanned unless they are force-added to
Git; this keeps developer secrets out of output while catching accidental
commits during CI or pre-commit use.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS = (
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("openai-api-key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("github-token", re.compile(r"(?:ghp|github_pat)_[A-Za-z0-9_]{20,}")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}")),
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("jwt-like-token", re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
)

ASSIGNMENT = re.compile(
    r"^\s*(?:[A-Z0-9_]*API[_-]?KEY|AUTH[_-]?SECRET|[A-Z0-9_]*SERVICE[_-]?ROLE[_-]?KEY|CLIENT[_-]?SECRET)\s*=\s*(\S+)"
)
PLACEHOLDER = re.compile(r"^(?:''|\"\"|\{env:[^}]+\}|\$\{[^}]+\}|<[^>]+>|your[-_].*|replace[-_].*|placeholder|changeme|change-me)$", re.I)


def scan_text(text: str) -> list[str]:
    """Return rule names only; never return secret values or source lines."""
    findings: list[str] = []
    for name, pattern in PATTERNS:
        if pattern.search(text):
            findings.append(name)
    for line in text.splitlines():
        match = ASSIGNMENT.match(line)
        if match:
            value = match.group(1).strip().strip(",;")
            if value and value not in {"''", '""'} and not PLACEHOLDER.match(value):
                findings.append("sensitive-assignment")
                break
    return sorted(set(findings))


def repository_files(root: Path = ROOT) -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return [root / line for line in output.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        return [
            path for path in root.rglob("*")
            if path.is_file() and ".git" not in path.parts
            and "node_modules" not in path.parts and ".venv" not in path.parts
        ]


def scan_repository(root: Path = ROOT) -> list[tuple[str, list[str]]]:
    findings: list[tuple[str, list[str]]] = []
    for path in repository_files(root):
        try:
            raw = path.read_bytes()
            if b"\x00" in raw:
                continue
            rules = scan_text(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if rules:
            findings.append((path.relative_to(root).as_posix(), rules))
    return findings


def main() -> int:
    findings = scan_repository()
    if not findings:
        print("secret scan passed")
        return 0
    for path, rules in findings:
        print(f"secret-like content: {path} ({', '.join(rules)})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
