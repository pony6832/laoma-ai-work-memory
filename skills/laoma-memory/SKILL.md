---
name: laoma-memory
description: Cross-device long-term work memory for Laoma. Use when the user says 繼續、接著做、上次做到哪裡、讀取記憶、長期記憶、記住這件事、收工、交接、候選記憶、換設備、跨裝置、laoma-memory, or when a task needs prior project context, verified preferences, device facts, decisions, or next actions. Locate and safely sync the canonical Git memory repository, load bounded relevant context, search the local MemPalace index, create review-gated candidates, and perform safe handoff without storing secrets.
---

# Laoma Memory

Use the canonical Git repository as the source of truth. Treat MemPalace as a rebuildable local search index and `.memory-growth/` as a device-local candidate queue.

## Start or resume

1. Run from any directory:

   ```powershell
   python "<skill-dir>/scripts/laoma_memory.py" context --cwd "<current-working-directory>" --pull
   ```

2. If `pull_status` reports `skipped-dirty`, preserve the existing changes and continue from local context. Do not force a pull.
3. Read the returned `CURRENT_STATUS.md`, `SECURITY_RULES.md`, `MEMORY_INDEX.md`, matching project files, Git state, and candidate summaries.
4. Summarize the remembered state in at most five lines. Separate `CONFIRMED`, `OBSERVED`, and `TODO-VERIFY`; recheck drift-prone facts before relying on them.
5. When the bounded context is insufficient, search before opening more files:

   ```powershell
   python "<skill-dir>/scripts/laoma_memory.py" search "<query>"
   ```

Never print credentials, cookies, private keys, full personal identifiers, or unauthorized company content.

## Remember something

When the user explicitly says to remember something, or asks for a handoff, create a local candidate. Do not approve it automatically.

```powershell
python "<skill-dir>/scripts/laoma_memory.py" candidate `
  --title "<concise title>" `
  --category "fact|decision|pattern|playbook|preference|project" `
  --scope "<project or general>" `
  --source "<task, file, or verified observation>" `
  --confidence "CONFIRMED|OBSERVED|TODO-VERIFY" `
  --content "<sanitized reusable memory>"
```

If the scanner blocks the candidate, report only the finding type and line number. Do not echo the sensitive value.

## Review candidates

Use `candidates` to list, `show <id>` to inspect, and only run `approve <id>` or `reject <id>` after the user explicitly chooses. After an approval, run the repository audit, commit/push according to `prompts/CODEX_HANDOFF.md`, then update MemPalace.

```powershell
python "<skill-dir>/scripts/laoma_memory.py" candidates
python "<skill-dir>/scripts/laoma_memory.py" show "<id>"
python "<skill-dir>/scripts/laoma_memory.py" approve "<id>"
python "<skill-dir>/scripts/laoma_memory.py" reject "<id>" --reason "<reason>"
```

## Handoff

When the user says 收工、交接、記錄進度, or explicitly asks to persist task state:

1. Load and follow `prompts/CODEX_HANDOFF.md` from the located repository.
2. Update the matching project `AI_WORKLOG.md` and `NEXT_ACTIONS.md`; update `CURRENT_STATUS.md` only when the main active state changed.
3. Run tests and `tools/memory_growth.py harvest` followed by `audit`.
4. Leave new candidates local until explicit review.
5. Inspect the diff for sensitive information before commit/push.

Do not persist routine conversation merely because this Skill was used to read context.

## New device

Read [device-setup.md](references/device-setup.md) when the repository, Git hooks, or MemPalace is missing. Run device setup only with the user's authorization because it changes local configuration.
