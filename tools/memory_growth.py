#!/usr/bin/env python3
"""Safe, review-gated growth loop for the work-memory repository."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(os.environ.get("MEMORY_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
LOCAL = ROOT / ".memory-growth"
CANDIDATES = LOCAL / "candidates"
APPROVED = LOCAL / "approved"
REJECTED = LOCAL / "rejected"
STATE_FILE = LOCAL / "state.json"
KNOWLEDGE = ROOT / "knowledge"

CATEGORIES = ("fact", "decision", "pattern", "playbook", "preference", "project")
CONFIDENCE = ("CONFIRMED", "OBSERVED", "TODO-VERIFY")
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".ps1", ".sh"}
SAFE_PLACEHOLDERS = ("<redacted>", "[redacted]", "redacted", "***", "${", "$env:")

SENSITIVE_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("github-token", re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{20,}\b")),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer-token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I)),
    (
        "assigned-secret",
        re.compile(
            r"\b(?:password|passwd|pwd|api[_ -]?key|access[_ -]?token|refresh[_ -]?token|cookie|secret)"
            r"\s*[:=]\s*['\"]?([^\s'\"]{6,})",
            re.I,
        ),
    ),
    ("email-address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("credit-card-like", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
    ("taiwan-id-like", re.compile(r"\b[A-Z][12]\d{8}\b", re.I)),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")


def ensure_local() -> None:
    for path in (CANDIDATES, APPROVED, REJECTED):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines()).strip()


def fingerprint(text: str) -> str:
    canonical = re.sub(r"\s+", " ", text.strip().casefold())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def slugify(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", text).strip("-").lower()
    return slug[:48] or "memory"


def scan_text(text: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for number, line in enumerate(text.splitlines(), 1):
        lowered = line.casefold()
        if any(marker in lowered for marker in SAFE_PLACEHOLDERS):
            continue
        for label, pattern in SENSITIVE_PATTERNS:
            if pattern.search(line):
                findings.append({"type": label, "line": number})
    return findings


def known_fingerprints() -> set[str]:
    result: set[str] = set()
    for folder in (CANDIDATES, APPROVED):
        if folder.exists():
            for path in folder.glob("*.json"):
                try:
                    value = read_json(path, {})
                    if value.get("fingerprint"):
                        result.add(value["fingerprint"])
                except (OSError, json.JSONDecodeError):
                    pass
    if KNOWLEDGE.exists():
        for path in KNOWLEDGE.rglob("*.md"):
            match = re.search(r"^fingerprint:\s*([0-9a-f]{64})\s*$", path.read_text(encoding="utf-8"), re.M)
            if match:
                result.add(match.group(1))
    return result


def create_candidate(
    *, title: str, category: str, scope: str, source: str, confidence: str,
    content: str, tags: list[str] | None = None, expires: str | None = None,
    source_key: str | None = None,
) -> tuple[Path | None, str]:
    ensure_local()
    content = normalize(content)
    findings = scan_text("\n".join((title, scope, source, content)))
    if findings:
        labels = ", ".join(f"{item['type']}@L{item['line']}" for item in findings)
        return None, f"blocked-sensitive:{labels}"
    digest = fingerprint(content)
    if digest in known_fingerprints():
        return None, "duplicate"
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    memory_id = f"{stamp}-{slugify(title)}-{digest[:8]}"
    payload = {
        "id": memory_id,
        "status": "candidate",
        "created_at": now_iso(),
        "title": title.strip(),
        "category": category,
        "scope": scope.strip(),
        "source": source.strip(),
        "source_key": source_key,
        "confidence": confidence,
        "expires": expires,
        "tags": sorted(set(tags or [])),
        "fingerprint": digest,
        "content": content,
    }
    path = CANDIDATES / f"{memory_id}.json"
    write_json(path, payload)
    return path, "created"


def cmd_capture(args: argparse.Namespace) -> int:
    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    elif args.content:
        content = args.content
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        print("需要 --content、--file 或標準輸入。", file=sys.stderr)
        return 2
    path, status = create_candidate(
        title=args.title,
        category=args.category,
        scope=args.scope,
        source=args.source,
        confidence=args.confidence,
        content=content,
        tags=args.tag,
        expires=args.expires,
    )
    if path:
        print(f"候選記憶已建立：{path.name}")
        return 0
    print(f"未建立候選記憶：{status}", file=sys.stderr)
    return 2 if status.startswith("blocked-sensitive") else 0


def worklog_entries(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", text))
    entries: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = normalize(text[match.end():end])
        if body:
            entries.append((match.group(1).strip(), body))
    return entries


def cmd_harvest(args: argparse.Namespace) -> int:
    ensure_local()
    state = read_json(STATE_FILE, {"harvested": {}})
    harvested = state.setdefault("harvested", {})
    created = duplicate = blocked = 0
    if args.file:
        paths = [Path(args.file).resolve()]
    else:
        paths = [
            path for path in sorted(ROOT.glob("projects/**/AI_WORKLOG.md"))
            if "_template" not in path.relative_to(ROOT).parts
        ]
    wanted = re.compile(
        r"^-\s*(?:GOAL|COMPLETED|RESULT|TEST RESULT|PROBLEMS|OPEN PROBLEMS|NEXT ACTION|EXACT NEXT STEP|SAFETY)[：:]",
        re.I,
    )
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        for heading, body in worklog_entries(path):
            source_key = f"{rel}#{heading}"
            source_hash = fingerprint(body)
            if harvested.get(source_key) == source_hash:
                continue
            selected = [line for line in body.splitlines() if wanted.match(line.strip())]
            content = normalize("\n".join(selected) or body)
            project = path.parent.name
            candidate, status = create_candidate(
                title=f"工作交接：{project}／{heading}",
                category="project",
                scope=project,
                source=source_key,
                source_key=source_key,
                confidence="OBSERVED",
                expires=(dt.date.today() + dt.timedelta(days=180)).isoformat(),
                tags=["worklog", project],
                content=content,
            )
            harvested[source_key] = source_hash
            if candidate:
                created += 1
            elif status == "duplicate":
                duplicate += 1
            else:
                blocked += 1
                print(f"已阻擋 {source_key}：{status}", file=sys.stderr)
    state["last_harvest_at"] = now_iso()
    write_json(STATE_FILE, state)
    print(f"擷取完成：新增 {created}、重複 {duplicate}、阻擋 {blocked}")
    return 2 if blocked else 0


def candidate_path(memory_id: str) -> Path | None:
    direct = CANDIDATES / f"{memory_id}.json"
    if direct.exists():
        return direct
    matches = list(CANDIDATES.glob(f"{memory_id}*.json"))
    return matches[0] if len(matches) == 1 else None


def cmd_list(args: argparse.Namespace) -> int:
    ensure_local()
    paths = sorted(CANDIDATES.glob("*.json"))
    if not paths:
        print("目前沒有候選記憶。")
        return 0
    for path in paths:
        item = read_json(path, {})
        print(f"{item.get('id')} | {item.get('category')} | {item.get('confidence')} | {item.get('title')}")
    print(f"共 {len(paths)} 筆；使用 approve <ID> 或 reject <ID>。")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    path = candidate_path(args.id)
    if not path:
        print("找不到唯一候選記憶。", file=sys.stderr)
        return 2
    print(json.dumps(read_json(path, {}), ensure_ascii=False, indent=2))
    return 0


def yaml_value(value) -> str:
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False)


def cmd_approve(args: argparse.Namespace) -> int:
    path = candidate_path(args.id)
    if not path:
        print("找不到唯一候選記憶。", file=sys.stderr)
        return 2
    item = read_json(path, {})
    findings = scan_text("\n".join(str(item.get(key, "")) for key in ("title", "scope", "source", "content")))
    if findings:
        print("候選記憶含疑似敏感資訊，拒絕批准。", file=sys.stderr)
        return 2
    category = item["category"]
    target_dir = KNOWLEDGE / category
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{item['id']}.md"
    if target.exists():
        print(f"正式記憶已存在：{target.relative_to(ROOT)}")
        return 0
    approved_at = now_iso()
    tags = ", ".join(item.get("tags") or [])
    text = (
        "---\n"
        f"id: {yaml_value(item['id'])}\n"
        f"category: {yaml_value(category)}\n"
        f"scope: {yaml_value(item['scope'])}\n"
        f"confidence: {yaml_value(item['confidence'])}\n"
        f"source: {yaml_value(item['source'])}\n"
        f"created_at: {yaml_value(item['created_at'])}\n"
        f"approved_at: {yaml_value(approved_at)}\n"
        f"last_verified: {yaml_value(approved_at[:10])}\n"
        f"expires: {yaml_value(item.get('expires'))}\n"
        f"fingerprint: {item['fingerprint']}\n"
        f"tags: {yaml_value(tags)}\n"
        "---\n\n"
        f"# {item['title']}\n\n"
        f"{item['content']}\n"
    )
    target.write_text(text, encoding="utf-8")
    item["status"] = "approved"
    item["approved_at"] = approved_at
    write_json(APPROVED / path.name, item)
    path.unlink()
    print(f"已批准並寫入：{target.relative_to(ROOT)}")
    print("請檢查 git diff 後再提交。")
    return 0


def cmd_reject(args: argparse.Namespace) -> int:
    ensure_local()
    path = candidate_path(args.id)
    if not path:
        print("找不到唯一候選記憶。", file=sys.stderr)
        return 2
    item = read_json(path, {})
    item["status"] = "rejected"
    item["rejected_at"] = now_iso()
    item["reason"] = args.reason
    write_json(REJECTED / path.name, item)
    path.unlink()
    print(f"已拒絕：{item['id']}")
    return 0


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def staged_added_text() -> str:
    diff = git_output("diff", "--cached", "--no-color", "--unified=0")
    return "\n".join(
        line[1:] for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def tracked_text_files() -> list[Path]:
    names = git_output("ls-files", "-z").split("\0")
    result = []
    for name in names:
        if not name:
            continue
        path = ROOT / name
        if path.is_file() and path.suffix.casefold() in TEXT_SUFFIXES and path.stat().st_size <= 2_000_000:
            result.append(path)
    return result


def cmd_audit(args: argparse.Namespace) -> int:
    findings: list[str] = []
    if args.staged:
        for item in scan_text(staged_added_text()):
            findings.append(f"staged:{item['type']}@L{item['line']}")
    else:
        for path in tracked_text_files():
            for item in scan_text(path.read_text(encoding="utf-8", errors="replace")):
                findings.append(f"{path.relative_to(ROOT)}:{item['type']}@L{item['line']}")
        if KNOWLEDGE.exists():
            today = dt.date.today()
            for path in KNOWLEDGE.rglob("*.md"):
                if path.name == "README.md":
                    continue
                text = path.read_text(encoding="utf-8")
                required = ("id", "category", "scope", "confidence", "source", "fingerprint")
                for field in required:
                    if not re.search(rf"(?m)^{re.escape(field)}:\s*.+$", text):
                        findings.append(f"{path.relative_to(ROOT)}:missing-{field}")
                match = re.search(r"(?m)^expires:\s*[\"']?(\d{4}-\d{2}-\d{2})", text)
                if match and dt.date.fromisoformat(match.group(1)) < today:
                    findings.append(f"{path.relative_to(ROOT)}:expired-{match.group(1)}")
    if findings:
        print("記憶安全稽核未通過：", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 2
    print("記憶安全稽核通過。")
    return 0


def cmd_install_hooks(args: argparse.Namespace) -> int:
    git_output("config", "core.hooksPath", ".githooks")
    print("已啟用版本庫 Git hooks：提交前敏感資訊掃描、提交後候選擷取。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="老馬 AI 記憶庫的安全自我生長工具")
    sub = parser.add_subparsers(dest="command", required=True)

    capture = sub.add_parser("capture", help="建立一筆本機候選記憶")
    capture.add_argument("--title", required=True)
    capture.add_argument("--category", choices=CATEGORIES, default="fact")
    capture.add_argument("--scope", default="general")
    capture.add_argument("--source", default="manual")
    capture.add_argument("--confidence", choices=CONFIDENCE, default="OBSERVED")
    capture.add_argument("--expires")
    capture.add_argument("--tag", action="append", default=[])
    group = capture.add_mutually_exclusive_group()
    group.add_argument("--content")
    group.add_argument("--file")
    capture.set_defaults(func=cmd_capture)

    harvest = sub.add_parser("harvest", help="從 AI_WORKLOG 自動產生候選記憶")
    harvest.add_argument("--file")
    harvest.set_defaults(func=cmd_harvest)

    listing = sub.add_parser("list", help="列出候選記憶")
    listing.set_defaults(func=cmd_list)
    show = sub.add_parser("show", help="查看候選記憶")
    show.add_argument("id")
    show.set_defaults(func=cmd_show)
    approve = sub.add_parser("approve", help="批准候選並寫入正式記憶")
    approve.add_argument("id")
    approve.set_defaults(func=cmd_approve)
    reject = sub.add_parser("reject", help="拒絕候選")
    reject.add_argument("id")
    reject.add_argument("--reason", default="not-useful")
    reject.set_defaults(func=cmd_reject)
    audit = sub.add_parser("audit", help="掃描敏感資訊、格式與過期記憶")
    audit.add_argument("--staged", action="store_true")
    audit.set_defaults(func=cmd_audit)
    hooks = sub.add_parser("install-hooks", help="啟用 Git 自動安全與擷取鉤子")
    hooks.set_defaults(func=cmd_install_hooks)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
