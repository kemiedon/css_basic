#!/usr/bin/env python3
"""
自動 push 腳本
- 自動 commit 所有 changes
- commit message 使用 0001, 0002... 遞增數字的規則
- 檢查前一個 commit 是否遵循規範，如果沒有則從 0001 開始
- 自動處理子模組的 push
- 自動同步遠端：本地超前 → push；遠端超前 → pull --rebase → push；分歧 → 試圖整合或提示
"""

import subprocess
import re
import sys
import time
import os

DEFAULT_ENCODING = "utf-8"
WAIT_TIME = 1  # 等待檔案寫入的時間（秒）


def run_git(args, check=True, cwd=None):
    """統一執行 git，避免 Windows 預設編碼造成解碼失敗。"""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding=DEFAULT_ENCODING,
        errors="replace",
        check=check,
        cwd=cwd,
    )


def has_staged_changes(cwd=None):
    """檢查是否有 staged 變更（git add 後真正會被 commit 的內容）。"""
    result = run_git(["diff", "--cached", "--name-only"], check=False, cwd=cwd)
    return bool((result.stdout or "").strip())


def get_previous_commit_message():
    """取得前一個 commit message"""
    try:
        result = run_git(["log", "-1", "--pretty=%B"], check=True)
        return (result.stdout or "").strip()
    except subprocess.CalledProcessError:
        return None


def is_valid_message(message):
    """檢查 message 是否符合規範 (0001, 0002...)"""
    return bool(re.match(r"^\d+$", message))


def generate_next_message(current_message):
    """根據當前 message 生成下一個 message"""
    if not current_message or not is_valid_message(current_message):
        return "0001"

    try:
        current_num = int(current_message)
        next_num = current_num + 1
        return f"{next_num:04d}"
    except ValueError:
        return "0001"


def run_command(command, description):
    """執行命令並顯示狀態"""
    try:
        print(f"執行: {description}...")
        if command and command[0] == "git":
            result = run_git(command[1:], check=True)
        else:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding=DEFAULT_ENCODING,
                errors="replace",
                check=True,
            )
        print(f"✓ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        print(f"✗ {description} 失敗: {stderr}")
        return False


def ensure_remote_synced(cwd=None):
    """
    確保本地與遠端同步。
    - 本地超前 → 無動作，待後續 push
    - 遠端超前 → 自動 pull --rebase
    - 分歧 → 試圖 pull --rebase；失敗則提示手動處理

    回傳 True 表示同步完成或無須同步；False 表示失敗需手動干預。
    """
    # 取得目前分支
    branch_result = run_git(["branch", "--show-current"], cwd=cwd)
    if branch_result.returncode != 0 or not branch_result.stdout.strip():
        print("✗ 無法取得目前分支")
        return False

    branch = branch_result.stdout.strip()

    # 更新遠端參照
    print("正在更新遠端參照...")
    fetch_result = run_git(["fetch"], cwd=cwd, check=False)
    if fetch_result.returncode != 0:
        print("⚠ fetch 失敗，使用舊的遠端參照繼續")

    # 計算 merge-base 判斷分歧
    try:
        merge_base = run_git(
            ["merge-base", "HEAD", f"origin/{branch}"], check=False, cwd=cwd
        ).stdout.strip()
        head = run_git(["rev-parse", "HEAD"], check=False, cwd=cwd).stdout.strip()
        remote = run_git(
            ["rev-parse", f"origin/{branch}"], check=False, cwd=cwd
        ).stdout.strip()

        # 本地超前（remote 沒有 local 的提交）
        if merge_base == remote:
            print(f"✓ 本地 {branch} 超前遠端，待推送")
            return True

        # 遠端超前（local 沒有 remote 的提交）
        if merge_base == head:
            print(f"⚠ 遠端 {branch} 超過本地，自動拉取...")
            result = run_git(
                ["pull", "--rebase", "origin", branch], check=False, cwd=cwd
            )
            if result.returncode == 0:
                print(f"✓ 自動 rebase 完成")
                return True
            else:
                print(f"✗ Rebase 衝突，請手動解決：git pull --rebase")
                return False

        # 雙方分歧
        print(f"⚠ 本地和遠端分歧，嘗試 rebase...")
        result = run_git(["pull", "--rebase", "origin", branch], check=False, cwd=cwd)
        if result.returncode == 0:
            print(f"✓ Rebase 成功")
            return True
        else:
            print(
                f"✗ Rebase 衝突，請手動解決：git rebase --continue 或 git rebase --abort"
            )
            return False
    except Exception as e:
        print(f"⚠ 無法連接遠端，離線推送：{e}")
        return True  # 讓後續 push 嘗試


def run_command(command, description):
    """執行命令並顯示狀態"""
    try:
        print(f"執行: {description}...")
        if command and command[0] == "git":
            result = run_git(command[1:], check=True)
        else:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding=DEFAULT_ENCODING,
                errors="replace",
                check=True,
            )
        print(f"✓ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        print(f"✗ {description} 失敗: {stderr}")
        return False


def process_submodule(submodule_path):
    """處理單個 submodule 的 commit 和 push"""
    original_dir = os.getcwd()

    try:
        # 確保路徑存在
        if not os.path.exists(submodule_path):
            print(f"✗ Submodule {submodule_path} 不存在")
            return False

        os.chdir(submodule_path)

        # 等待檔案寫入
        time.sleep(WAIT_TIME)

        # 檢查是否有變更
        result = run_git(["status", "--porcelain"], check=False)
        if not result.stdout.strip():
            return True

        # 取得前一個 commit message
        prev_message = get_previous_commit_message()
        next_message = generate_next_message(prev_message)

        print(f"\n[Submodule: {submodule_path}]")
        print(f"前一個 commit: {prev_message if prev_message else '無'}")
        print(f"下一個 commit: {next_message}")

        # Add, commit, push
        if not run_command(["git", "add", "-A"], "git add -A"):
            return False

        # 有些情況（例如換行自動轉換或 filter）會讓 working tree 看似有變更，但 add 後其實沒有 staged 差異。
        # 這時候直接跳過 commit/push，避免 `git commit` 因 nothing to commit 而被當成失敗。
        if not has_staged_changes():
            print(
                f"⚠ Submodule {submodule_path} 無可提交內容（add 後無 staged 變更），跳過 commit/push"
            )
            return True

        if not run_command(
            ["git", "commit", "-m", next_message], f"git commit -m '{next_message}'"
        ):
            return False

        # 自動同步遠端再推送
        if not ensure_remote_synced():
            print(f"⚠ Submodule {submodule_path} 同步失敗，跳過推送")
            return False

        if not run_command(["git", "push"], "git push"):
            return False

        print(f"✓ Submodule {submodule_path} 完成")
        return True

    except Exception as e:
        print(f"✗ Submodule {submodule_path} 錯誤: {e}")
        return False
    finally:
        os.chdir(original_dir)


def is_squash_commit(message: str) -> bool:
    """判斷是否為 squash 的 10 的倍數 commit。"""
    try:
        return int(message) % 10 == 0
    except (ValueError, TypeError):
        return False


def get_squash_log(count: int = 10) -> str:
    """取得最近 count 筆 commit 的 oneline log。"""
    result = run_git(["log", f"-{count}", "--oneline"], check=False)
    return (result.stdout or "").strip()


def do_squash(next_message: str) -> bool:
    """
    將最近 10 筆 commit 合併為 1 筆總結 commit。
    使用 git reset --soft HEAD~10 + git commit。
    需要 force push（因 history 改寫）。
    """
    num = int(next_message)
    start_num = num - 9
    squash_msg = f"SQUASH-{next_message}: commits {start_num:04d}~{next_message} 總結"

    log_summary = get_squash_log(10)
    full_msg = f"{squash_msg}\n\n{log_summary}"

    print(f"\n[Squash] 觸發第 {num} 筆，合併最近 10 筆 commits...")
    print(f"[Squash] 訊息：{squash_msg}")

    # soft reset 10 筆（保留 working tree 與 index）
    result = run_git(["reset", "--soft", "HEAD~10"], check=False)
    if result.returncode != 0:
        print(f"✗ Squash reset 失敗: {result.stderr}")
        return False

    # 重新 commit 為單筆總結
    result = run_git(["commit", "-m", full_msg], check=False)
    if result.returncode != 0:
        print(f"✗ Squash commit 失敗: {result.stderr}")
        return False

    print(f"✓ Squash commit 完成")

    # force push（history 已改寫）
    result = run_git(["push", "--force-with-lease"], check=False)
    if result.returncode != 0:
        print(f"✗ Squash force push 失敗: {result.stderr}")
        return False

    print(f"✓ Squash force push 完成")
    return True


def main():
    print("=== 自動 Push 腳本 ===\n")

    # 檢查 git 倉庫
    try:
        run_git(["rev-parse", "--git-dir"], check=True)
    except subprocess.CalledProcessError:
        print("錯誤: 不是 git 倉庫")
        sys.exit(1)

    # 等待檔案寫入
    print("等待檔案寫入...")
    time.sleep(WAIT_TIME)

    # 處理所有 submodules
    print("檢查 submodules...")
    result = run_git(
        ["config", "--file", ".gitmodules", "--name-only", "--get-regexp", "path"],
        check=False,
    )
    if result.stdout.strip():
        print("發現 submodules，先進行提交...\n")
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            # 格式: submodule.<name>.path
            try:
                # 從 git config 取得實際的 submodule 路徑
                path_result = run_git(
                    ["config", "--file", ".gitmodules", "--get", line], check=False
                )
                if path_result.stdout.strip():
                    submodule_path = path_result.stdout.strip()
                    process_submodule(submodule_path)
            except Exception as e:
                print(f"提取 submodule 路徑失敗: {e}")

    # 檢查主倉庫是否有 changes (包含 submodule reference 更新)
    print("\n檢查主倉庫變更...")
    result = run_git(["status", "--porcelain"], check=False)
    if not result.stdout.strip():
        print("無任何 changes，無須 commit")
        return

    # 取得前一個 commit message
    prev_message = get_previous_commit_message()
    print(f"[主倉庫]")
    print(f"前一個 commit message: {prev_message if prev_message else '無'}")

    # 生成下一個 message
    next_message = generate_next_message(prev_message)
    print(f"下一個 commit message: {next_message}\n")

    # git add all
    if not run_command(["git", "add", "-A"], "git add -A"):
        sys.exit(1)

    # 有些情況（例如換行自動轉換或 filter）會讓 status 顯示有變更，但 add 後其實沒有 staged 差異。
    # 這時候不需要 commit，直接完成遠端同步/推送即可。
    if not has_staged_changes():
        print("⚠ 無可提交內容（add 後無 staged 變更），跳過 commit")
        print("\n[主倉庫] 同步遠端...")
        if not ensure_remote_synced():
            print("✗ 遠端同步失敗，中止推送")
            sys.exit(1)
        if not run_command(["git", "push"], "git push"):
            sys.exit(1)
        print("\n✓ 所有操作完成")
        return

    # git commit
    if not run_command(
        ["git", "commit", "-m", next_message], f"git commit -m '{next_message}'"
    ):
        sys.exit(1)

    # 自動同步遠端
    print("\n[主倉庫] 同步遠端...")
    if not ensure_remote_synced():
        print("✗ 遠端同步失敗，中止推送")
        sys.exit(1)

    # git push
    if not run_command(["git", "push"], "git push"):
        sys.exit(1)

    # 若為 10 的倍數，執行 squash 總結
    if is_squash_commit(next_message):
        if not do_squash(next_message):
            print("⚠ Squash 失敗，history 未合併，請手動處理")

    print("\n✓ 所有操作完成")


if __name__ == "__main__":
    main()
