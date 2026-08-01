[CmdletBinding()]
param(
    [switch]$Replace,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'

function Get-TreeFingerprint {
    param([Parameter(Mandatory)][string]$Root)

    $resolvedRoot = (Resolve-Path -LiteralPath $Root -ErrorAction Stop).Path
    $files = Get-ChildItem -LiteralPath $resolvedRoot -Recurse -Force -File |
        Where-Object { $_.FullName -notmatch '[\\/]__pycache__[\\/]' -and $_.Extension -ne '.pyc' } |
        Sort-Object FullName
    $parts = foreach ($file in $files) {
        $relative = $file.FullName.Substring($resolvedRoot.Length).TrimStart('\', '/')
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        "$relative|$hash"
    }
    $bytes = [Text.Encoding]::UTF8.GetBytes(($parts -join "`n"))
    $stream = [IO.MemoryStream]::new($bytes)
    try {
        return (Get-FileHash -InputStream $stream -Algorithm SHA256).Hash
    }
    finally {
        $stream.Dispose()
    }
}

$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot) -ErrorAction Stop).Path
$source = Join-Path $repoRoot 'skills\laoma-memory'
$required = @(
    'SKILL.md',
    'agents\openai.yaml',
    'references\device-setup.md',
    'scripts\laoma_memory.py'
)

foreach ($relative in $required) {
    $requiredPath = Join-Path $source $relative
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Canonical Skill is missing a required file: $relative"
    }
}

$sourceItem = Get-Item -LiteralPath $source -Force
if (($sourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'Canonical Skill must not be a junction or symbolic link.'
}

$codexRoot = if ($env:CODEX_HOME) {
    [IO.Path]::GetFullPath($env:CODEX_HOME)
}
else {
    [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.codex'))
}
$skillsRoot = Join-Path $codexRoot 'skills'
New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
$skillsRoot = (Resolve-Path -LiteralPath $skillsRoot -ErrorAction Stop).Path
$destination = Join-Path $skillsRoot 'laoma-memory'

$sourceFingerprint = Get-TreeFingerprint -Root $source
$destinationExists = Test-Path -LiteralPath $destination
if ($destinationExists) {
    $destinationItem = Get-Item -LiteralPath $destination -Force
    if (($destinationItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'Global laoma-memory must not be a junction or symbolic link.'
    }
    $destinationFingerprint = Get-TreeFingerprint -Root $destination
    if ($destinationFingerprint -eq $sourceFingerprint) {
        Write-Output "laoma-memory is current: $destination"
        exit 0
    }
    if ($Check) {
        Write-Output "laoma-memory needs an update: $destination"
        exit 1
    }
    if (-not $Replace) {
        throw 'Global laoma-memory differs. Review it, then use -Replace; the previous version will be backed up.'
    }
}
elseif ($Check) {
    Write-Output "laoma-memory is not installed: $destination"
    exit 1
}

$stage = Join-Path $skillsRoot ('.laoma-memory-stage-' + [guid]::NewGuid().ToString('N'))
Copy-Item -LiteralPath $source -Destination $stage -Recurse -Force
$stage = (Resolve-Path -LiteralPath $stage -ErrorAction Stop).Path
if ((Get-TreeFingerprint -Root $stage) -ne $sourceFingerprint) {
    throw 'Staged copy verification failed; installation stopped.'
}

$backup = $null
if ($destinationExists) {
    $backup = Join-Path $skillsRoot ('laoma-memory.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    if (Test-Path -LiteralPath $backup) {
        throw "Backup destination already exists: $backup"
    }
    Move-Item -LiteralPath $destination -Destination $backup
}

try {
    Move-Item -LiteralPath $stage -Destination $destination
}
catch {
    if ($backup -and -not (Test-Path -LiteralPath $destination) -and (Test-Path -LiteralPath $backup)) {
        Move-Item -LiteralPath $backup -Destination $destination
    }
    throw
}

$configPath = Join-Path $codexRoot 'laoma-memory.json'
$config = @{ repo = $repoRoot } | ConvertTo-Json
[IO.File]::WriteAllText($configPath, $config + "`n", [Text.UTF8Encoding]::new($false))

Write-Output "laoma-memory installed: $destination"
Write-Output "Memory repository path saved: $configPath"
if ($backup) {
    Write-Output "Previous version backup: $backup"
}
