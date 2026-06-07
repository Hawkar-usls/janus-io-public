#!/usr/bin/env python3
"""Dry-run secret and local-identifier scrubber for Janus Io artifacts."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv"}
TEXT_EXTENSIONS = {
    ".bat",
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".py",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class PatternRule:
    name: str
    regex: re.Pattern[str]
    replacement: str


RULES: Tuple[PatternRule, ...] = (
    PatternRule(
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    PatternRule(
        "windows_path",
        re.compile(r"\b[A-Za-z]:\\[^\r\n\"'<>|]+"),
        "[REDACTED_WINDOWS_PATH]",
    ),
    PatternRule(
        "openai_key",
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        "[REDACTED_TOKEN]",
    ),
    PatternRule(
        "github_token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        "[REDACTED_TOKEN]",
    ),
    PatternRule(
        "aws_access_key",
        re.compile(r"\bA(?:KIA|SIA)[A-Z0-9]{16}\b"),
        "[REDACTED_TOKEN]",
    ),
    PatternRule(
        "credential_label",
        re.compile(
            r"(?i)\b(api[_-]?key|authorization|bearer|password|passwd|private[_-]?key|secret|token|user)\b"
            r"(\s*[:=]\s*[\"']?)([^\s\"',;]+)"
        ),
        r"\1\2[REDACTED_SECRET]",
    ),
    PatternRule(
        "wallet_or_worker",
        re.compile(r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}(?:\.[A-Za-z0-9_.-]{1,64})?\b"),
        "[REDACTED_WALLET_OR_WORKER]",
    ),
)


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for start in paths:
        if start.is_file():
            yield start
            continue
        if not start.exists():
            continue
        for path in start.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_file():
                yield path


def is_text_candidate(path: Path, max_bytes: int) -> bool:
    if path.name.endswith(".redacted"):
        return False
    try:
        if path.stat().st_size > max_bytes:
            return False
    except OSError:
        return False
    return path.suffix.lower() in TEXT_EXTENSIONS or path.suffix == ""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def scan_text(path: Path, text: str) -> List[Tuple[str, int, str]]:
    findings: List[Tuple[str, int, str]] = []
    for rule in RULES:
        for match in rule.regex.finditer(text):
            if rule.name == "credential_label":
                value = match.group(3).strip().strip("\"'").lower()
                if value in {"str", "int", "float", "bool", "none", "true", "false", "x"}:
                    continue
                if value == match.group(1).strip().lower():
                    continue
                if value.startswith("args.") or "{" in value or "}" in value:
                    continue
            line = text.count("\n", 0, match.start()) + 1
            sample = match.group(0).strip().replace("\t", " ")
            if len(sample) > 120:
                sample = sample[:117] + "..."
            findings.append((rule.name, line, sample))
    return findings


def redact_text(text: str) -> str:
    redacted = text
    for rule in RULES:
        redacted = rule.regex.sub(rule.replacement, redacted)
    return redacted


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Scan text files for secrets and local identifiers.")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(".")])
    parser.add_argument("--apply", action="store_true", help="write .redacted copies; never edits originals")
    parser.add_argument("--limit", type=int, default=80, help="maximum findings to print")
    parser.add_argument("--max-bytes", type=int, default=5_000_000, help="skip files larger than this")
    args = parser.parse_args()

    total = 0
    printed = 0
    touched = 0
    for path in iter_files(args.paths):
        if not is_text_candidate(path, args.max_bytes):
            continue
        try:
            text = read_text(path)
        except OSError:
            continue
        findings = scan_text(path, text)
        if not findings:
            continue
        total += len(findings)
        for name, line, sample in findings:
            if printed < args.limit:
                print(f"{path}:{line}: {name}: {sample}")
                printed += 1
        if args.apply:
            target = path.with_name(path.name + ".redacted")
            target.write_text(redact_text(text), encoding="utf-8")
            touched += 1

    if total > printed:
        print(f"... {total - printed} additional findings not shown")
    mode = "apply" if args.apply else "dry-run"
    print(f"scrub_secrets: mode={mode} findings={total} redacted_copies={touched}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
