# PROJECT CONTEXT

## 專案名稱

老馬 AI 工作記憶系統

## 目標

以私人 GitHub Repository 作為跨裝置、跨 AI 助理的單一可信工作記憶來源，讓工作可以安全且可追溯地交接。

## 使用者／利害關係人

- 老馬（Repository 擁有者與主要使用者）
- HOME-PC、OFFICE-PC、LAPTOP、PHONE 上經授權的 Codex／ChatGPT 工作階段

## 範圍

### 包含

- 裝置的非敏感環境摘要
- 專案目標、進度、決策、下一步與脫敏錯誤摘要
- 固定的開工、收工與跨裝置交接流程
- 自動產生候選記憶、敏感資訊掃描、去重、人工批准、過期稽核與本機語意索引
- 可從任意 Codex 工作目錄載入長期記憶的全域 `laoma-memory` Skill 與跨設備安裝器

### 不包含

- 密碼、API Key、Token、Cookie、私鑰或完整個資
- 未脫敏的公司機密、客戶資料、瀏覽紀錄或未授權私人檔案
- 大型專案原始碼與二進位產物

## 技術環境

- Git／GitHub 私人 Repository
- Markdown 記憶檔
- Windows 裝置上的 Codex 與 ChatGPT

## Repository／工作目錄

- Repository：`laoma-ai-work-memory`（私人 Repository）
- HOME-PC：`<Documents>/老馬的完全AI記憶`（脫敏路徑）

## 已確認事實

- HOME-PC 已於 2026-07-12 完成首次 Clone 與安全環境盤點。
- `prompts/CODEX_START.md` 與 `prompts/CODEX_HANDOFF.md` 是固定工作流程。
- 所有提交前必須檢查差異並排除敏感資訊。
- 自動化只建立本機候選；正式長期記憶必須經老馬明確批准後才能進入 Git。

## 待確認事項

- 其他裝置的實際環境與 GitHub 存取方式
- 其餘活躍專案的 Repository、範圍與安全分類

## 限制與風險

- 公司與私人資料必須隔離；不確定是否敏感時不得提交。
- 記憶內容可能過期，關鍵環境資訊應在實際裝置重新驗證。
- 自動擷取可能產生低價值或重複候選，因此採內容指紋、到期日與人工審批控制品質。

## 完成定義

- 每台授權裝置均有安全盤點與可用的 GitHub 交接流程。
- 每個活躍專案均有專屬脈絡、下一步、決策與追加式工作紀錄。
- 工作紀錄能自動形成候選，且正式寫入前通過安全、去重與人工審批。
