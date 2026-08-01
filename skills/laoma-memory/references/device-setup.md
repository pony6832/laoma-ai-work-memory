# New-device setup

## Preconditions

- The user has authorized this device to access the private memory repository.
- Git authentication already works; never request or print a token.
- Company and personal trust boundaries remain separate.

## Existing clone

Run:

```powershell
python "<skill-dir>/scripts/laoma_memory.py" doctor
python "<skill-dir>/scripts/laoma_memory.py" device-setup --mine
```

`device-setup` enables the tracked Git hooks. With `--mine`, it also updates MemPalace if a local executable is found.

## Missing clone

Stop and ask the user for the intended visible clone location. Clone the private repository there, then run `device-setup --mine`. Never guess credentials or embed them in the remote URL.

## Missing MemPalace

The Skill still works with bounded Markdown context and a local text-search fallback. Report that semantic search is unavailable; do not install MemPalace unless the user asks.

## Device-local state

- Git-tracked approved memories sync across devices.
- `.memory-growth/` candidates do not sync.
- MemPalace data does not sync and can be rebuilt with `mine`.
- `core.hooksPath` is local Git configuration and must be enabled once per clone.
