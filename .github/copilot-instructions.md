# GitHub Copilot 指令

## 第一條：語言與溝通風格

    - MUST 使用繁體中文。
    - MUST NOT 使用簡體中文、英文或日文。
    - IF 說明內容，THEN MUST 使用國中生程度的簡單詞彙。

- MUST 將每次對話回應控制在 20 行以內。
  - MUST NOT 在對話中顯示程式碼區塊（code blocks）。
  - IF 需要說明實作細節，THEN 使用文字描述或結構化清單。
  - IF 說明技術概念或問題，THEN MUST 用「舊的做法 vs 新的做法」或「A 情況 vs B 情況」的對比結構呈現，避免抽象描述。
  - IF 解釋問題，THEN 先說「現在的問題是什麼」，再說「需要改什麼」，最多兩步，不要一次列出所有相關細節。

## 第二條：自動 Push 規定

    - IF 所有檔案編輯和驗證完成，THEN 執行 .github/tools/auto_push.py
    - MUST 將 auto_push 作為最後一個工具調用（在所有編輯、驗證、檢查工具之後）
    - 執行前先執行 sync 確保檔案系統同步
    - MUST 將所有變更自動 commit 和 push 到遠端倉庫
    - auto_push 完成後才輸出文字回應給用戶

## 第二條之一：Squash 總結規定

    - IF commit 序號是 10 的倍數（如 0010、0020、0030），THEN MUST 在該次 commit 後自動執行 squash。
    - Squash 範圍：將該筆以及前 9 筆（共 10 筆）合併為 1 筆總結 commit。
    - Squash commit message 格式：`SQUASH-XXXX: commits YYYY~XXXX 總結`（例：`SQUASH-0010: commits 0001~0010 總結`）。
    - Squash 完成後 MUST 使用 `git push --force-with-lease` 推送（因 history 已改寫）。
    - MUST NOT 在非 10 的倍數時執行 squash。

## 第三條：臨時腳本規定

    - IF 需要建立臨時腳本（如處理大檔案），THEN MUST 將檔案建立於系統暫存區（Windows: $env:TEMP）。
    - ELSE MUST NOT 在專案根目錄或工作區建立任何臨時檔案。
    - IF 腳本執行完畢，THEN MUST 立即刪除。（用 Remove-Item $env:TEMP\temp_fix.py）
    - MUST 確保 Git 倉庫乾淨。（git status 顯示 nothing to commit）

## 第四條：批次任務自動執行

    - IF 用戶請求處理多個檔案（如「標記這六個檔案」），THEN MUST 自動連續處理所有檔案。
    - MUST NOT 處理完單一檔案後詢問是否繼續。
    - MUST 使用 manage_todo_list 追蹤進度，但無須等待用戶確認即可繼續下一個項目。
    - IF 所有檔案處理完畢，THEN 執行 auto_push.py 統一提交。

## 第五條：縮排規定

    - MUST 使用 4 個空格進行縮排。
    - MUST NOT 使用 2 個空格。
    - MUST NOT 使用 Tab 字元。

## 第八條：Python 優先規定

    - IF 一個 skill 步驟可以用 Python 腳本自動化，THEN MUST 優先撰寫 Python 腳本執行，而非純靠 Copilot agent 手動操作。
    - 判斷標準：涉及檔案讀寫、API 呼叫、批次處理、資料轉換、格式輸出等任務，均視為「可自動化」。
    - MUST 將腳本放入 skill 資料夾的`scripts/` 子目錄，並在 `SKILL.md` 步驟總覽中正確登記腳本名稱。
    - IF 步驟確實不適合腳本化（如需判斷、確認、使用者互動），THEN 才可標記為 `Copilot`。

## 第八條之一：Python 套件管理規定

    - IF 需要在腳本中安裝 Python 套件，THEN MUST 使用`uv pip install <package>`。
    - IF 在終端機執行安裝指令，THEN MUST 優先使用 `uv pip install`。
    - MUST NOT 使用 `pip install` (除非 `uv` 不可用)。

## 第八條之二：Python 腳本結構規範

    - MUST 每個 .py 檔案頂部寫明：功能描述、檔案結構、使用方式（格式參考 send_email.py）
    - MUST 單檔 < 150 行；超過則拆為 config.py（設定）+ tools.py（工具函式）+ 主程式
    - MUST 單函式 20~50 行；超過則拆輔助函式
    - MUST 所有設定（路徑、API 參數、常數）集中在 config.py 或檔頭常數區，不散落 main()
    - MUST main() 保持線性流程：讀取 → 執行 → 儲存，不超過 20 行
    - MUST 所有函式加 type hints（參數與回傳值）

## 第九條：Chrome DevTools MCP 測試規定

    - MUST NOT 擅自關閉用戶的 Chrome 瀏覽器（如`Stop-Process -Name chrome`）。
    - IF Chrome DevTools MCP 無法連接，THEN 直接詢問用戶而非自動重啟。
    - MUST 使用 `mcp_io_github_chr_list_pages` 檢查現有頁面，切換到正確頁面而非開新頁。
    - MUST 尊重用戶手動開啟的瀏覽器實例和頁面狀態。

## 第十條：專案架構與開發規範

本專案為美股分析小助理，技術棧：FastAPI + Vue 3 + TypeScript + OpenAI API + moomoo OpenAPI。

### 核心原則

    - moomoo API 只允許在 `backend/app/integrations/moomoo_client.py` 中直接呼叫。
    - OpenAI API 只允許在 `backend/app/integrations/openai_client.py` 與 `backend/app/services/llm_analysis_service.py` 中呼叫。
    - LLM 不得直接執行交易，也不得產生保證獲利的內容。
    - 所有交易判斷必須是條件式與風險揭露式。
    - 所有使用者可見分析都必須包含「非投資建議，僅供研究與教育用途」。
    - MVP 階段只支援美股與 paper trading / read-only mode。

### 後端規範

    - 使用 Python 3.11+，FastAPI 與 Pydantic。
    - API response 必須有明確 schema。
    - 技術指標計算要寫 unit tests。
    - 不得在程式碼中 hardcode API key、帳戶、密碼。
    - 外部服務錯誤要轉成清楚的 application error。

### 前端規範

    - 使用 Vue 3 Composition API + TypeScript + Tailwind CSS。
    - API 型別要放在 `frontend/src/types`。
    - API 呼叫要集中在 `frontend/src/api`。
    - 不要在 component 中直接寫 fetch。

### 測試規範

    - `indicator_service`、`signal_engine`、`risk_guard` 必須有 unit tests。
    - OpenAI 與 moomoo 外部呼叫必須可 mock。
    - PR 前至少跑 backend unit tests 與 frontend typecheck。

## 第十一條：Skill 開發計畫規定

    - IF 用戶與 Copilot 完成一個 skill 的需求討論（包含功能範圍、執行模式、Decisions），THEN MUST 自動建立一份 skill 開發計畫檔。
    - 計畫檔路徑：`config/plans/skills/{skill-name}/`（依功能分子資料夾）
    - 計畫檔 MUST 包含：重點摘要、觸發模式表、完整步驟（Phase A…最後 Phase）、Decisions 表、排除範圍、相關檔案清單。
    - 計畫檔建立後，對應的 prompts 提示詞 MUST 同步存為 `prompts/{skill-name}.prompt.md`。
    - MUST NOT 等待用戶額外要求才建立；需求討論結束確認後立即執行。
