# 文件名: login_script.py
# 作用: 自动登录 ClawCloud Run，支持 GitHub 账号密码 + 2FA 自动验证

import os
import time
import shutil
import tempfile
import pyotp  # 用于生成 2FA 验证码
from playwright.sync_api import sync_playwright

def run_login():
    # 1. 获取环境变量中的敏感信息
    username = os.environ.get("GH_USERNAME")
    password = os.environ.get("GH_PASSWORD")
    totp_secret = os.environ.get("GH_2FA_SECRET")

    if not username or not password:
        print("❌ 错误: 必须设置 GH_USERNAME 和 GH_PASSWORD 环境变量。")
        return

    # 创建临时用户数据目录，确保每次都是全新状态
    temp_user_data_dir = tempfile.mkdtemp(prefix="browser_temp_")
    
    print("🚀 [Step 1] 启动浏览器 (全新状态)...")
    
    with sync_playwright() as p:
        try:
            # 启动浏览器，配置为全新状态
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',  # 禁用自动化控制特征
                    '--disable-web-security',  # 禁用同源策略（如果需要）
                    '--disable-extensions',  # 禁用扩展
                    '--disable-plugins',  # 禁用插件
                    '--disable-sync',  # 禁用同步
                    '--disable-default-apps',  # 禁用默认应用
                    '--disable-translate',  # 禁用翻译
                    '--disable-background-networking',  # 禁用后台网络
                    '--disable-background-timer-throttling',  # 禁用后台定时器限制
                    '--disable-backgrounding-occluded-windows',  # 禁用后台窗口遮挡
                    '--disable-renderer-backgrounding',  # 禁用渲染器后台运行
                    '--disable-features=TranslateUI,BlinkGenPropertyTrees'  # 禁用特定功能
                ]
            )
            
            # 创建上下文，指定临时用户数据目录，确保全新状态
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                # 不传入 user_data_dir 参数，让 Playwright 使用临时目录
                # 或者显式使用临时目录
                storage_state=None,  # 确保不加载任何存储状态
                # 禁用所有存储
                permissions=[],
                # 设置额外的上下文选项
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )
            
            # 在新上下文中创建页面
            page = context.new_page()
            
            # 添加脚本以覆盖 navigator.webdriver 属性，避免被检测
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)

            # 2. 访问 ClawCloud 登录页
            target_url = "https://us-west-1.run.claw.cloud/"
            print(f"🌐 [Step 2] 正在访问: {target_url}")
            
            # 清除可能存在的缓存和cookie
            context.clear_cookies()
            
            page.goto(target_url, wait_until="networkidle")
            
            # 强制等待页面加载完成
            time.sleep(2)

            # 3. 点击 GitHub 登录按钮
            print("🔍 [Step 3] 寻找 GitHub 按钮...")
            try:
                # 多种方式查找 GitHub 按钮
                login_selectors = [
                    "button:has-text('GitHub')",
                    "a:has-text('GitHub')",
                    "[data-provider='github']",
                    ".github-login",
                    "//button[contains(., 'GitHub')]",
                    "//a[contains(., 'GitHub')]"
                ]
                
                found_button = False
                for selector in login_selectors:
                    if page.locator(selector).count() > 0:
                        login_button = page.locator(selector).first
                        login_button.wait_for(state="visible", timeout=10000)
                        login_button.click()
                        print(f"✅ 使用选择器找到并点击 GitHub 按钮: {selector}")
                        found_button = True
                        break
                
                if not found_button:
                    # 如果没有找到特定按钮，尝试查找任何包含 "GitHub" 文本的元素
                    github_elements = page.locator(":text('GitHub')")
                    if github_elements.count() > 0:
                        github_elements.first.click()
                        print("✅ 点击包含 'GitHub' 文本的元素")
                        found_button = True
                
                if not found_button:
                    print("❌ 未找到 GitHub 登录按钮")
                    # 截图查看页面状态
                    page.screenshot(path="login_error_no_button.png")
                    raise Exception("GitHub 登录按钮未找到")
                    
            except Exception as e:
                print(f"⚠️ 点击 GitHub 按钮失败: {e}")
                # 尝试直接访问 GitHub OAuth URL
                try:
                    print("🔄 尝试直接访问 GitHub OAuth URL...")
                    page.goto("https://github.com/login/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=https://us-west-1.run.claw.cloud/auth/callback/github")
                    page.wait_for_load_state("networkidle")
                except Exception as oauth_error:
                    print(f"❌ OAuth 重定向也失败: {oauth_error}")
                    raise

            # 4. 处理 GitHub 登录表单
            print("⏳ [Step 4] 等待跳转到 GitHub...")
            try:
                # 等待 URL 变更为 github.com
                page.wait_for_url(lambda url: "github.com" in url, timeout=15000)
                
                # 检查是否在登录页面
                if "login" in page.url.lower():
                    print("🔒 输入账号密码...")
                    # 等待登录字段加载
                    page.wait_for_selector("#login_field", timeout=10000)
                    page.fill("#login_field", username)
                    page.fill("#password", password)
                    page.click("input[name='commit']") # 点击登录按钮
                    print("📤 登录表单已提交")
                    time.sleep(3)
            except Exception as e:
                print(f"ℹ️ GitHub 表单处理异常: {e}")
                # 截图查看当前状态
                page.screenshot(path="github_form_error.png")

            # 5. 【核心】处理 2FA 双重验证 (解决异地登录拦截)
            # 给页面一点时间跳转
            time.sleep(5)
            
            # 检查是否在 2FA 页面
            current_url = page.url
            print(f"🔗 当前 URL: {current_url}")
            
            if "two-factor" in current_url or "two_factor" in current_url or page.locator("#app_totp").count() > 0 or page.locator("#otp").count() > 0:
                print("🔐 [Step 5] 检测到 2FA 双重验证请求！")
                
                if totp_secret:
                    print("🔢 正在计算动态验证码 (TOTP)...")
                    try:
                        # 使用密钥生成当前的 6 位验证码
                        totp = pyotp.TOTP(totp_secret)
                        token = totp.now()
                        print(f"   生成的验证码: {token}")
                        
                        # 尝试多种可能的输入框选择器
                        otp_selectors = ["#app_totp", "#otp", "input[name='otp']", "input[type='text']", "input[autocomplete='one-time-code']"]
                        
                        for selector in otp_selectors:
                            if page.locator(selector).count() > 0:
                                page.fill(selector, token)
                                print(f"✅ 使用选择器 {selector} 填入验证码")
                                
                                # 尝试提交表单
                                submit_selectors = ["button[type='submit']", "input[type='submit']", "button:has-text('Verify')"]
                                for submit_selector in submit_selectors:
                                    if page.locator(submit_selector).count() > 0:
                                        page.click(submit_selector)
                                        print(f"✅ 点击提交按钮: {submit_selector}")
                                        break
                                break
                                
                    except Exception as e:
                        print(f"❌ 填入验证码失败: {e}")
                        page.screenshot(path="2fa_error.png")
                else:
                    print("❌ 致命错误: 检测到 2FA 但未配置 GH_2FA_SECRET Secret！")
                    page.screenshot(path="2fa_missing_secret.png")
                    exit(1)

            # 6. 处理授权确认页 (Authorize App)
            # 给页面时间跳转
            time.sleep(5)
            current_url = page.url.lower()
            
            if "authorize" in current_url or "oauth" in current_url:
                print("⚠️ 检测到授权请求，尝试点击 Authorize...")
                try:
                    authorize_selectors = [
                        "button:has-text('Authorize')",
                        "button:has-text('Authorize claw')",
                        "button[type='submit']",
                        "#authorize",
                        "input[name='authorize']"
                    ]
                    
                    for selector in authorize_selectors:
                        if page.locator(selector).count() > 0:
                            page.click(selector, timeout=5000)
                            print(f"✅ 点击授权按钮: {selector}")
                            break
                except Exception as auth_error:
                    print(f"⚠️ 授权点击失败: {auth_error}")

            # 7. 等待最终跳转结果
            print("⏳ [Step 6] 等待跳转回 ClawCloud 控制台...")
            # 等待较长的时间确保完全跳转
            time.sleep(10)
            page.wait_for_load_state("networkidle")
            
            final_url = page.url
            print(f"📍 最终页面 URL: {final_url}")
            
            # 获取页面标题和内容片段用于验证
            page_title = page.title()
            print(f"📄 页面标题: {page_title}")
            
            # 截图保存，用于 GitHub Actions 查看结果
            screenshot_path = "login_result.png"
            page.screenshot(path=screenshot_path)
            print(f"📸 已保存结果截图: {screenshot_path}")

            # 8. 验证是否成功
            is_success = False
            success_indicators = []
            
            # 获取页面文本内容用于检查
            page_text = page.content()
            
            # 检查点 A: 页面包含特定文字
            success_texts = ["App Launchpad", "Devbox", "Dashboard", "Welcome", "Console", "ClawCloud", "Projects"]
            for text in success_texts:
                if text.lower() in page_text.lower():
                    success_indicators.append(f"找到文本: {text}")
                    is_success = True
            
            # 检查点 B: URL 包含控制台特征
            if "private-team" in final_url or "console" in final_url or "dashboard" in final_url:
                success_indicators.append("URL 包含控制台特征")
                is_success = True
            
            # 检查点 C: 不在 GitHub 或登录页面
            elif "github.com" not in final_url and "login" not in final_url and "signin" not in final_url:
                success_indicators.append("不在 GitHub 或登录页面")
                is_success = True
            
            # 检查点 D: 页面有特定元素
            if page.locator("nav, header, footer, .dashboard, .sidebar").count() > 0:
                success_indicators.append("找到页面导航元素")
                is_success = True

            if is_success and success_indicators:
                print(f"🎉🎉🎉 登录成功！成功指标: {', '.join(success_indicators)}")
                print("✅ 任务完成")
            else:
                print("😭😭😭 登录失败。请下载 login_result.png 查看原因。")
                print(f"❌ 失败原因分析:")
                print(f"   - 最终 URL: {final_url}")
                print(f"   - 页面标题: {page_title}")
                print(f"   - 页面是否包含 'GitHub': {'github' in page_text.lower()}")
                print(f"   - 页面是否包含 'login': {'login' in page_text.lower()}")
                exit(1) # 抛出错误代码，让 Action 变红

        finally:
            # 确保浏览器关闭
            if 'browser' in locals():
                browser.close()
            
            # 清理临时目录
            try:
                if os.path.exists(temp_user_data_dir):
                    shutil.rmtree(temp_user_data_dir, ignore_errors=True)
                    print(f"🧹 已清理临时目录: {temp_user_data_dir}")
            except Exception as cleanup_error:
                print(f"⚠️ 清理临时目录时出错: {cleanup_error}")

if __name__ == "__main__":
    run_login()
