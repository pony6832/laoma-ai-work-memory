# 自我生長記憶庫

## 核心原則

本系統會自動產生「候選記憶」，但不會自動把候選變成永久事實。正式寫入前必須經過敏感資訊掃描、去重與人工批准。

流程：

`AI_WORKLOG → 本機候選 → 安全掃描 → 人工批准 → knowledge/ → Git → MemPalace 索引`

## 日常使用

在 Repository 根目錄執行：

```powershell
# 從所有 AI_WORKLOG 擷取尚未處理的工作紀錄
python tools/memory_growth.py harvest

# 查看候選
python tools/memory_growth.py list
python tools/memory_growth.py show <候選 ID>

# 批准或拒絕
python tools/memory_growth.py approve <候選 ID>
python tools/memory_growth.py reject <候選 ID> --reason "不具長期價值"

# 全庫安全、格式與過期檢查
python tools/memory_growth.py audit
```

也可手動建立候選：

```powershell
python tools/memory_growth.py capture `
  --title "已驗證的操作經驗" `
  --category playbook `
  --scope "專案名稱" `
  --source "任務或檔案來源" `
  --confidence CONFIRMED `
  --content "可重用且已脫敏的內容"
```

## 自動化

- `pre-commit`：掃描準備提交的新增文字，發現疑似憑證或個資就阻擋提交。
- `post-commit`：從 `projects/**/AI_WORKLOG.md` 擷取新工作紀錄為本機候選。
- `.memory-growth/`：本機審批佇列，不進 Git、不跨裝置同步。
- `knowledge/`：批准後的正式記憶，經 Git 同步並由 MemPalace 索引。

## 記憶生命週期

- `CONFIRMED`：使用者明確確認或已直接驗證。
- `OBSERVED`：從工作紀錄歸納，仍可能需要複查。
- `TODO-VERIFY`：只能作為線索，不能當成正式事實。
- 有 `expires` 的記憶到期後由 `audit` 標記；系統不自動刪除。
- 修正舊記憶時應新增更正記憶並在內容中註明取代關係，保留可追溯性。

## MemPalace

Git 是正式來源，MemPalace 只是本機搜尋索引。批准並提交後執行：

```powershell
mempalace mine .
mempalace sync . --dry-run
```

先預覽同步差異；只有在確認刪除與移動結果正確後才套用正式同步。
