# CODEX START

你正在協助老馬延續跨裝置工作。

開始前必須：
1. 讀取根目錄 `CURRENT_STATUS.md`。
2. 讀取 `SECURITY_RULES.md`。
3. 讀取目前專案的 `PROJECT_CONTEXT.md`、`NEXT_ACTIONS.md`、`AI_WORKLOG.md`。
4. 檢查 Git 狀態、目前 branch 與未提交變更。
5. 不得讀取、輸出或提交密碼、Token、Cookie、私鑰、個資或未授權公司機密。
6. 執行 `python tools/memory_growth.py list` 查看本機候選記憶；未經老馬明確批准，不得寫入 `knowledge/`。

工作方式：
- 先用 5 行內摘要目前狀態。
- 明確列出本次目標與預計修改檔案。
- 執行後測試並回報結果。
- 收工時依 `prompts/CODEX_HANDOFF.md` 更新記憶。
- Git 是正式記憶來源；`.memory-growth/` 只是本機候選佇列，MemPalace 只是本機搜尋索引。

首次在 HOME-PC 執行時，請安全盤點：Windows 版本、CPU、RAM、GPU、磁碟摘要、Git、Python、Node.js、Docker、WSL、FFmpeg、NVIDIA Driver/CUDA；只記錄版本與非敏感資訊，更新 `devices/HOME-PC.md`。
