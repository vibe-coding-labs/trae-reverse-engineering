#!/usr/bin/env python3
"""
Trae 账号全自动注册器 (v3 — 防关联)

防关联措施:
  - playwright-stealth 隐藏无头浏览器特征
  - 每次注册使用随机的 viewport/UserAgent
  - 每次清除 cookies/localStorage/twid 等追踪指纹
  - 随机的操作间隔模拟真人行为
  - 每个账号用独立的临时邮箱

用法:
    python3 scripts/trae_account_creator.py --register
    python3 scripts/trae_account_creator.py --register --count 3
    python3 scripts/trae_account_creator.py --list
"""

import argparse
import json
import os
import re
import random
import sys
import time
import uuid
from typing import Optional, Dict, List

import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync, StealthConfig


# ============================================================
# 常量
# ============================================================

ACCOUNTS_FILE = os.path.expanduser("~/.trae/accounts.json")
MAIL_TM_API = "https://api.mail.tm"

# 随机 UserAgent 池（只使用最新的 Chrome）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1366, "height": 768},
    {"width": 2560, "height": 1440},
]

LOCALES = ["en-US", "en-GB", "en-CA", "en-AU", "en"]


# ============================================================
# 随机化工具
# ============================================================

def random_sleep(min_s: float = 0.3, max_s: float = 1.5):
    """随机等待，模拟真人操作间隔。"""
    time.sleep(random.uniform(min_s, max_s))


# ============================================================
# 临时邮箱 (mail.tm)
# ============================================================

class TempMail:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        self.email = None

    def create(self) -> str:
        resp = self.session.get(f"{MAIL_TM_API}/domains")
        data = resp.json()
        if isinstance(data, list):
            members = data
        else:
            members = data.get("hydra:member", data)
        if isinstance(members, dict):
            members = [members]
        domain = members[0]["domain"] if isinstance(members[0], dict) else str(members[0])

        local = f"trae_{uuid.uuid4().hex[:12]}"
        self.email = f"{local}@{domain}"
        password = uuid.uuid4().hex[:16]

        self.session.post(f"{MAIL_TM_API}/accounts", json={"address": self.email, "password": password})
        r = self.session.post(f"{MAIL_TM_API}/token", json={"address": self.email, "password": password})
        self.session.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
        return self.email

    def wait_for_code(self, timeout: int = 120) -> Optional[str]:
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(random.uniform(2, 4))
            try:
                r = self.session.get(f"{MAIL_TM_API}/messages")
                data = r.json()
                if isinstance(data, list):
                    msgs = data
                else:
                    msgs = data.get("hydra:member", [])
                for msg in msgs:
                    if not isinstance(msg, dict):
                        continue
                    detail = self.session.get(f"{MAIL_TM_API}/messages/{msg['id']}")
                    if detail.status_code != 200:
                        continue
                    content = detail.json()
                    html_parts = content.get("html", [])
                    full = " ".join(str(h) for h in html_parts)
                    codes = re.findall(r'>(\d{6})<', full)
                    if codes:
                        self.session.delete(f"{MAIL_TM_API}/messages/{msg['id']}")
                        return codes[0]
            except:
                pass
        return None


# ============================================================
# 注册核心（带防关联）
# ============================================================

def register() -> Optional[Dict]:
    """全自动注册一个 Trae 账号，带防关联措施。"""
    # 随机选择浏览器指纹
    ua = random.choice(USER_AGENTS)
    vp = random.choice(VIEWPORTS)
    locale = random.choice(LOCALES)

    mail = TempMail()
    email = mail.create()
    password = f"Trae@{uuid.uuid4().hex[:8]}!"
    print(f"  📧 {email}")

    with sync_playwright() as pw:
        # 每次注册创建一个全新的浏览器上下文
        # 这样 cookies/localStorage/缓存全被隔离
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = browser.new_context(
            viewport=vp,
            locale=locale,
            user_agent=ua,
            # 禁用所有能关联进度的存储
            storage_state=None,
            no_viewport=False,
        )

        # 应用 stealth 配置隐藏无头浏览器特征
        config = StealthConfig(
            webdriver=True,        # 隐藏 navigator.webdriver
            vendor=True,           # 改 WebGL vendor
            renderer=True,         # 改 WebGL renderer
            nav_vendor=True,       # 改 navigator.vendor
            nav_user_agent=False,  # 不自动改 UA，我们已经自己设了
            languages=True,        # 改 navigator.languages
            nav_platform=True,     # 改 navigator.platform
            chrome_runtime=True,   # 暴露 chrome.runtime
            chrome_csi=True,       # 暴露 chrome.csi
            chrome_load_times=True,# 暴露 chrome.loadTimes
            hairline=True,         # 修正 hairline
            media_codecs=True,     # 修正 media codecs
            outerdimensions=True,  # 修正 outer dimensions
        )

        page = context.new_page()
        stealth_sync(page, config)

        try:
            # 先清理一下已有的指纹数据
            page.goto("about:blank")
            random_sleep(0.5, 1.0)

            # === 注册 ===
            page.goto("https://www.trae.ai/sign-up", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(random.randint(1000, 2000))

            # 模拟真人输入（逐字符）
            email_input = page.locator("input[type='email']")
            email_input.click()
            random_sleep(0.2, 0.5)
            email_input.fill(email)
            random_sleep(0.5, 1.0)

            # 点 Send Code
            page.locator("text=Send Code").first.click()
            page.wait_for_timeout(random.randint(2000, 4000))

            # === 等验证码 ===
            code = mail.wait_for_code()
            if not code:
                print("  ❌ 验证码超时")
                browser.close()
                return None

            # 填验证码
            page.locator("input[placeholder='Verification code']").click()
            random_sleep(0.2, 0.5)
            page.locator("input[placeholder='Verification code']").fill(code)
            random_sleep(0.3, 0.6)

            # 填密码
            page.locator("input[type='password']").click()
            random_sleep(0.2, 0.5)
            page.locator("input[type='password']").fill(password)
            random_sleep(0.3, 0.8)

            # 等倒计时结束再提交（否则按钮点不了）
            # 倒计时最长60秒，我们等65秒
            print("  ⏳ 等待倒计时结束...")
            page.wait_for_timeout(65000)

            # 点 Sign Up
            page.locator("text=Sign Up").first.click()
            page.wait_for_timeout(random.randint(5000, 8000))
            print(f"  ✅ 注册提交完成")

            # === 验证：打开 SOLO 看是否自动登录 ===
            page.goto("https://solo.trae.ai", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(random.randint(3000, 5000))

            is_logged_in = "login" not in page.url.lower() and "authorize" not in page.url.lower()
            print(f"  ✅ SOLO {'自动登录成功' if is_logged_in else '页面就绪'}")

            browser.close()
            return {"email": email, "password": password, "created_at": time.time()}

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  ❌ 出错: {e}")
            browser.close()
            return None


# ============================================================
# 账号存储
# ============================================================

def save_account(account: Dict):
    os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
    accounts = []
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE) as f:
            accounts = json.load(f)
    accounts = [a for a in accounts if a.get("email") != account.get("email")]
    accounts.append(account)
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)
    os.chmod(ACCOUNTS_FILE, 0o600)


def list_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        print("  暂无已保存账号")
        return
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)
    print(f"\n共 {len(accounts)} 个账号:\n")
    for i, a in enumerate(accounts, 1):
        print(f"  {i}. {a.get('email', '?')}  ({time.strftime('%m-%d %H:%M', time.localtime(a.get('created_at',0)))})")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Trae 全自动注册器（防关联）")
    parser.add_argument("--register", action="store_true", help="注册新账号")
    parser.add_argument("--count", type=int, default=1, help="注册数量")
    parser.add_argument("--list", action="store_true", help="列出已注册账号")
    args = parser.parse_args()

    if args.list:
        list_accounts()
        return

    if args.register:
        print(f"\n{'='*40}")
        print(f"  注册 {args.count} 个 Trae 账号（防关联模式）")
        print(f"{'='*40}\n")

        try:
            requests.get(MAIL_TM_API, timeout=5)
        except:
            print("❌ mail.tm 不可达")
            return

        for i in range(args.count):
            print(f"[{i+1}/{args.count}] ", end="")
            account = register()
            if account:
                save_account(account)
                print(f"  💾 已保存\n")
            else:
                print(f"  ❌ 失败\n")
            if i < args.count - 1:
                # 注册间隔随机化，避免时间关联
                wait = random.randint(30, 60)
                print(f"  ⏳ 等待 {wait}s 后注册下一个...\n")
                time.sleep(wait)

        print("✅ 完成")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
