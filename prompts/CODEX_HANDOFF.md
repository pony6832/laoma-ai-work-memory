# CODEX HANDOFF

工作結束前：
1. 執行必要測試並記錄結果。
2. 檢查 `git diff`，確認沒有密碼、Token、Cookie、私鑰、個資或公司機密。
3. 在專案的 `AI_WORKLOG.md` 追加本次紀錄。
4. 更新專案的 `NEXT_ACTIONS.md`。
5. 如本專案是目前主要工作，更新根目錄 `CURRENT_STATUS.md`。
6. 執行 `python tools/memory_growth.py harvest`，把新工作紀錄轉成「本機候選記憶」。
7. 執行 `python tools/memory_growth.py list`；候選只能由老馬明確批准或拒絕，不得自動升格。
8. 執行 `python tools/memory_growth.py audit`，並確認 Git 提交前安全鉤子通過。
9. 使用清楚的 Commit message 提交並 Push。
10. 執行 `mempalace mine .` 更新本機語意索引；刪除或移動檔案時先執行 `mempalace sync . --dry-run`。

交接摘要固定格式：
- DEVICE：
- PROJECT：
- COMPLETED：
- TEST RESULT：
- FILES CHANGED：
- OPEN PROBLEMS：
- EXACT NEXT STEP：
- COMMIT SHA／PR：
