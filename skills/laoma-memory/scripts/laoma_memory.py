#!/usr/bin/env python3
"""Portable bridge between a global Codex Skill and Laoma's memory repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


CORE_FILES = ("CURRENT_STATUS.md", "SECURITY_RULES.md", "MEMORY_INDEX.md")
PROJECT_FILES = ("PROJECT_CONTEXT.md", "NEXT_ACTIONS.md", "AI_WORKLOG.md", "DECISIONS.md")
DEFAULT_NAMES = ("老馬的完全AI記憶", "laoma-ai-work-memory")


def run(command: list[str], cwd: Path | None = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result


def config_path() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "laoma-memory.json"


def valid_repo(path: Path) -> bool:
    return path.is_dir() and (path / "MEMORY_INDEX.md").is_file() and (path / "SECURITY_RULES.md").is_file()


def resolve_repo(explicit: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("LAOMA_MEMORY_REPO"):
        candidates.append(Path(os.environ["LAOMA_MEMORY_REPO"]).expanduser())
    cfg = config_path()
    if cfg.is_file():
        try:
            value = json.loads(cfg.read_text(encoding="utf-8"))
            if value.get("repo"):
                candidates.append(Path(value["repo"]).expanduser())
        except (OSError, json.JSONDecodeError):
            pass
    documents = Path.home() / "Documents"
    candidates.extend(documents / name for name in DEFAULT_NAMES)
    if documents.is_dir():
        for child in documents.iterdir():
            if child.is_dir() and (child / ".git").exists() and (child / "MEMORY_INDEX.md").exists():
                candidates.append(child)
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen and valid_repo(resolved):
            return resolved
        seen.add(resolved)
    raise FileNotFoundError(
        "找不到記憶庫。設定 LAOMA_MEMORY_REPO、建立 ~/.codex/laoma-memory.json，或在新設備 Clone Repository。"
    )


def git(repo: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(repo), *args], check=check)


def git_summary(repo: Path) -> dict[str, object]:
    branch = git(repo, "branch", "--show-current").stdout.strip()
    status = git(repo, "status", "--short", "--branch").stdout.strip()
    hook_path = git(repo, "config", "--get", "core.hooksPath").stdout.strip()
    return {"branch": branch, "status": status, "hooks_path": hook_path or None}


def safe_pull(repo: Path) -> str:
    dirty = git(repo, "status", "--porcelain").stdout.strip()
    if dirty:
        return "skipped-dirty"
    result = git(repo, "pull", "--ff-only")
    if result.returncode:
        return "failed:" + (result.stderr.strip() or result.stdout.strip())
    return "updated" if "Already up to date" not in result.stdout else "already-current"


def read_bounded(path: Path, remaining: int) -> tuple[str, int]:
    if remaining <= 0 or not path.is_file():
        return "", remaining
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > remaining:
        text = text[:remaining] + "\n[TRUNCATED]"
    return text, max(0, remaining - len(text))


def matching_project(repo: Path, cwd: Path) -> Path | None:
    projects = repo / "projects"
    if not projects.is_dir():
        return None
    names = [part.casefold() for part in cwd.parts if part]
    exact = projects / cwd.name
    if exact.is_dir() and exact.name != "_template":
        return exact
    matches = [path for path in projects.iterdir() if path.is_dir() and path.name != "_template" and path.name.casefold() in names]
    return matches[0] if len(matches) == 1 else None


def candidate_summaries(repo: Path) -> list[dict[str, str]]:
    folder = repo / ".memory-growth" / "candidates"
    result = []
    if not folder.is_dir():
        return result
    for path in sorted(folder.glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            result.append({
                "id": str(item.get("id", path.stem)),
                "title": str(item.get("title", "")),
                "category": str(item.get("category", "")),
                "confidence": str(item.get("confidence", "")),
            })
        except (OSError, json.JSONDecodeError):
            result.append({"id": path.stem, "title": "[unreadable]", "category": "", "confidence": ""})
    return result


def memory_tool(repo: Path) -> Path:
    path = repo / "tools" / "memory_growth.py"
    if not path.is_file():
        raise FileNotFoundError("記憶庫缺少 tools/memory_growth.py；請先同步最新版。")
    return path


def mempalace_executable() -> Path | None:
    found = shutil.which("mempalace")
    if found:
        return Path(found)
    candidate = Path.home() / "Documents" / "mempalace" / ".venv" / "Scripts" / "mempalace.exe"
    return candidate if candidate.is_file() else None


def wing_name(repo: Path) -> str:
    config = repo / "mempalace.yaml"
    if config.is_file():
        match = re.search(r"(?m)^wing:\s*(.+?)\s*$", config.read_text(encoding="utf-8", errors="replace"))
        if match:
            raw = match.group(1).strip()
            if raw.startswith('"') and raw.endswith('"'):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    pass
            return raw.strip("'\"")
    return repo.name


def cmd_doctor(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    payload = {
        "repo": str(repo),
        "git": git_summary(repo),
        "memory_tool": str(memory_tool(repo)),
        "candidate_count": len(candidate_summaries(repo)),
        "mempalace": str(mempalace_executable()) if mempalace_executable() else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    pull_status = safe_pull(repo) if args.pull else "not-requested"
    remaining = args.max_chars
    files: dict[str, str] = {}
    for rel in CORE_FILES:
        text, remaining = read_bounded(repo / rel, remaining)
        if text:
            files[rel] = text
    cwd = Path(args.cwd or os.getcwd()).resolve()
    project = matching_project(repo, cwd)
    if project:
        for name in PROJECT_FILES:
            text, remaining = read_bounded(project / name, remaining)
            if text:
                files[(project / name).relative_to(repo).as_posix()] = text
    payload = {
        "repo": str(repo),
        "pull_status": pull_status,
        "git": git_summary(repo),
        "current_working_directory": str(cwd),
        "matched_project": project.name if project else None,
        "candidates": candidate_summaries(repo),
        "files": files,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def fallback_search(repo: Path, query: str, limit: int) -> int:
    terms = [term.casefold() for term in re.findall(r"[\w\u4e00-\u9fff-]+", query) if len(term) > 1]
    hits: list[tuple[int, Path, str]] = []
    for path in repo.rglob("*.md"):
        if any(part in {".git", ".memory-growth"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        score = sum(text.casefold().count(term) for term in terms)
        if score:
            snippet = " ".join(line.strip() for line in text.splitlines() if any(term in line.casefold() for term in terms))
            hits.append((score, path, snippet[:700]))
    for score, path, snippet in sorted(hits, reverse=True)[:limit]:
        print(f"[{score}] {path.relative_to(repo)}\n{snippet}\n")
    return 0 if hits else 1


def cmd_search(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    executable = mempalace_executable()
    if executable:
        result = run([str(executable), "search", args.query, "--wing", wing_name(repo)])
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode
    print("MemPalace 未安裝；改用本機 Markdown 文字搜尋。", file=sys.stderr)
    return fallback_search(repo, args.query, args.limit)


def proxy_memory_command(args: argparse.Namespace, command: list[str]) -> int:
    repo = resolve_repo(args.repo)
    result = run([sys.executable, str(memory_tool(repo)), *command], cwd=repo)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def cmd_candidate(args: argparse.Namespace) -> int:
    command = [
        "capture", "--title", args.title, "--category", args.category,
        "--scope", args.scope, "--source", args.source,
        "--confidence", args.confidence, "--content", args.content,
    ]
    if args.expires:
        command.extend(["--expires", args.expires])
    for tag in args.tag:
        command.extend(["--tag", tag])
    return proxy_memory_command(args, command)


def cmd_candidates(args: argparse.Namespace) -> int:
    return proxy_memory_command(args, ["list"])


def cmd_show(args: argparse.Namespace) -> int:
    return proxy_memory_command(args, ["show", args.id])


def cmd_approve(args: argparse.Namespace) -> int:
    return proxy_memory_command(args, ["approve", args.id])


def cmd_reject(args: argparse.Namespace) -> int:
    return proxy_memory_command(args, ["reject", args.id, "--reason", args.reason])


def cmd_device_setup(args: argparse.Namespace) -> int:
    repo = resolve_repo(args.repo)
    result = run([sys.executable, str(memory_tool(repo)), "install-hooks"], cwd=repo)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode:
        return result.returncode
    cfg = config_path()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"repo": str(repo)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.mine:
        executable = mempalace_executable()
        if not executable:
            print("MemPalace 未安裝；已完成 Git hooks 與路徑設定。", file=sys.stderr)
            return 0
        mined = run([str(executable), "mine", str(repo)])
        sys.stdout.write(mined.stdout)
        sys.stderr.write(mined.stderr)
        return mined.returncode
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Global bridge for Laoma's long-term work memory")
    root.add_argument("--repo", help="Override the canonical memory repository path")
    sub = root.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)
    context = sub.add_parser("context")
    context.add_argument("--cwd")
    context.add_argument("--pull", action="store_true")
    context.add_argument("--max-chars", type=int, default=30000)
    context.set_defaults(func=cmd_context)
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.set_defaults(func=cmd_search)
    candidate = sub.add_parser("candidate")
    candidate.add_argument("--title", required=True)
    candidate.add_argument("--category", choices=("fact", "decision", "pattern", "playbook", "preference", "project"), default="fact")
    candidate.add_argument("--scope", default="general")
    candidate.add_argument("--source", default="manual")
    candidate.add_argument("--confidence", choices=("CONFIRMED", "OBSERVED", "TODO-VERIFY"), default="OBSERVED")
    candidate.add_argument("--content", required=True)
    candidate.add_argument("--expires")
    candidate.add_argument("--tag", action="append", default=[])
    candidate.set_defaults(func=cmd_candidate)
    candidates = sub.add_parser("candidates")
    candidates.set_defaults(func=cmd_candidates)
    show = sub.add_parser("show")
    show.add_argument("id")
    show.set_defaults(func=cmd_show)
    approve = sub.add_parser("approve")
    approve.add_argument("id")
    approve.set_defaults(func=cmd_approve)
    reject = sub.add_parser("reject")
    reject.add_argument("id")
    reject.add_argument("--reason", default="not-useful")
    reject.set_defaults(func=cmd_reject)
    setup = sub.add_parser("device-setup")
    setup.add_argument("--mine", action="store_true")
    setup.set_defaults(func=cmd_device_setup)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
