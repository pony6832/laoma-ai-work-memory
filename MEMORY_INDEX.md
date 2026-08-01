# 老馬 AI 工作記憶索引

本 Repository 是老馬跨裝置、跨專案的 AI 工作記憶中樞。

## 使用原則

1. GitHub 是唯一可信的專案狀態來源（Single Source of Truth）。
2. ChatGPT 負責理解、規劃、整理與跨專案協調。
3. Codex 負責在實際裝置上執行程式、修改檔案與回報結果。
4. 每次工作結束必須更新 `CURRENT_STATUS.md` 與該專案的 `AI_WORKLOG.md`。
5. 不保存密碼、API Key、Token、Cookie、身分證號、公司機密原文或未授權私人資料。

## 核心檔案

- `CURRENT_STATUS.md`：目前正在做什麼、下一步是什麼。
- `devices/`：各裝置與工作環境。
- `projects/PROJECT_INDEX.md`：專案總表。
- `prompts/`：ChatGPT 與 Codex 的固定交接 Prompt。
- `projects/_template/`：新專案標準模板。
- `SELF_GROWING_MEMORY.md`：候選、審批、稽核、Git 與 MemPalace 的完整閉環。
- `knowledge/`：經人工批准的正式長期記憶。
- `.memory-growth/`：不進 Git的本機候選與審批狀態。
- `tools/memory_growth.py`：擷取、去重、敏感資訊掃描、批准、拒絕與過期稽核工具。
- `skills/laoma-memory/`：可安裝到任意 Codex 設備的全域長期記憶 Skill 正式來源。
- `tools/install_laoma_memory_skill.ps1`：驗證、備份並安裝／更新全域 Skill。

## 已知主要工作範圍

- 攝影、影音製播、新聞媒體內容製作
- AI 圖像、角色卡、分鏡、Seedance 2.0 影片工作流
- 本地端 AI 影片資料庫、語音辨識、影像檢索與知識庫
- Windows 11、Adobe、GPU 與影音工具問題排查
- GitHub / Codex 跨裝置工作延續

## 資料可信度標記

- `CONFIRMED`：老馬已明確確認。
- `OBSERVED`：由既有工作紀錄歸納，尚未再次確認。
- `TODO-VERIFY`：待確認，不能當作正式事實。

## 自我生長流程

1. Codex／ChatGPT 在工作結束時更新 `AI_WORKLOG.md`。
2. 工具自動將尚未處理的紀錄轉為本機候選。
3. 敏感資訊掃描與內容指紋去重必須通過。
4. 老馬明確批准後，候選才寫入 `knowledge/`。
5. Git 同步正式記憶，MemPalace 更新本機語意索引。
6. 到期或被修正的記憶保留歷史，只標示待複查或取代關係。
