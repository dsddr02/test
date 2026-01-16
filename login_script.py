# 文件名: login_script.py
# 作用: 自动登录 ClawCloud Run，支持 GitHub 账号密码 + 2FA 自动验证

import os
import time
import random
import shutil
import tempfile
import requests  # 添加 requests 库用于 Telegram API
import pyotp  # 用于生成 2FA 验证码
from playwright.sync_api import sync_playwright

def send_telegram_notification(bot_token, chat_id, message, zanghu):
    """发送 Telegram 通知"""
    try:
        # 在消息中添加 zanghu 变量
        full_message = f"{message}\n\n📦 仓库: {zanghu}"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": full_message,
            "parse_mode": "HTML",
            "disable_notification": False
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("📤 Telegram 通知发送成功")
            return True
        else:
            print(f"⚠️ Telegram 通知发送失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发送 Telegram 通知时出错: {e}")
        return False

def human_like_delay(min_seconds=0.3, max_seconds=1.5):
    """模拟人类随机延迟"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay

def human_like_type(element, text, min_delay=30, max_delay=100):
    """模拟人类打字速度（毫秒级延迟）"""
    for char in text:
        element.type(char)
        # 随机延迟，模拟人类打字速度
        time.sleep(random.uniform(min_delay/1000, max_delay/1000))

def check_website_accessible(url, timeout=10):
    """检查网站是否可访问"""
    try:
        response = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 网站检查失败: {e}")
        return False

def run_login():
    # 获取环境变量中的敏感信息
    username = os.environ.get("GH_USERNAME")
    password = os.environ.get("GH_PASSWORD")
    totp_secret = os.environ.get("GH_2FA_SECRET")
    tele_bottoken = os.environ.get("GH_BOTTOKEN")
    tele_chatid = os.environ.get("GH_CHATID")
    zanghu = os.environ.get("ZANGHU", "未知仓库")  # 添加默认值

    # 初始化执行状态
    execution_status = "unknown"
    execution_details = {
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "success": False,
        "error_message": "",
        "final_url": "",
        "page_title": "",
        "app_launchpad_clicked": False,
        "app_launchpad_loaded": False,
        "app_launchpad_modal_detected": False
    }

    if not username or not password:
        error_msg = "❌ 错误: 必须设置 GH_USERNAME 和 GH_PASSWORD 环境变量。"
        print(error_msg)
        execution_status = "failed"
        execution_details["error_message"] = error_msg
        return execution_status, execution_details

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
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-sync',
                    '--disable-default-apps',
                    '--disable-translate',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI,BlinkGenPropertyTrees'
                ],
                # 增加超时时间
                timeout=60000
            )
            
            # 创建上下文，指定临时用户数据目录，确保全新状态
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                storage_state=None,
                permissions=[],
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Cache-Control': 'no-cache',
                },
                # 增加上下文超时
                timeout=60000
            )
            
            # 在新上下文中创建页面
            page = context.new_page()
            
            # 设置页面超时
            page.set_default_timeout(60000)
            
            # 增强反检测脚本
            page.add_init_script("""
                // 基础反检测
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // 模拟插件 (Headless Chrome 默认无插件)
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // 模拟语言
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });

                // 模拟 window.chrome
                window.chrome = { runtime: {} };

                // 绕过权限检测
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );

                // 隐藏自动化特征
                Object.defineProperty(navigator, 'userAgent', {
                    get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
                });

                // 覆盖常见自动化检测属性
                Object.defineProperty(document, 'hidden', { value: false });
                Object.defineProperty(document, 'visibilityState', { value: 'visible' });
            """)

            # 2. 检查网站是否可访问
            target_url = "https://us-west-1.run.claw.cloud/"
            print(f"🌐 [Step 2] 检查网站可访问性: {target_url}")
            
            # 首先使用 requests 检查网站是否可访问
            print("🔍 使用 requests 检查网站...")
            if not check_website_accessible(target_url):
                print("⚠️ 网站可能无法访问或网络有问题，尝试继续...")
            
            # 清除可能存在的缓存和cookie
            context.clear_cookies()
            
            print(f"🚀 正在访问: {target_url}")
            
            try:
                # 使用更宽松的等待条件，避免因网络慢而超时
                page.goto(
                    target_url, 
                    wait_until="domcontentloaded",  # 改为 domcontentloaded，不等待所有资源加载
                    timeout=45000  # 增加到45秒
                )
                
                # 等待页面基本加载
                page.wait_for_load_state("domcontentloaded")
                
                print(f"✅ 页面基本加载完成，等待网络空闲...")
                
                # 尝试等待网络空闲，但设置超时
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    print("⚠️ 网络未完全空闲，继续执行...")
                
            except Exception as nav_error:
                print(f"⚠️ 页面加载异常: {nav_error}")
                # 尝试直接重试一次
                try:
                    print("🔄 尝试重新加载页面...")
                    page.reload(wait_until="domcontentloaded", timeout=30000)
                except Exception as retry_error:
                    print(f"❌ 重新加载也失败: {retry_error}")
                    raise nav_error
            
            # 模拟人类等待页面加载
            delay = human_like_delay(2.0, 4.0)
            print(f"⏳ 随机延迟 {delay:.2f} 秒模拟人类浏览...")

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
                        login_button.wait_for(state="visible", timeout=15000)
                        
                        # 模拟人类悬停操作
                        print("🖱️ 模拟悬停在 GitHub 按钮上...")
                        login_button.hover()
                        human_like_delay(0.2, 0.5)
                        
                        # 模拟人类点击前延迟
                        human_like_delay(0.3, 0.8)
                        
                        login_button.click()
                        print(f"✅ 使用选择器找到并点击 GitHub 按钮: {selector}")
                        found_button = True
                        
                        # 点击后随机延迟
                        human_like_delay(1.0, 2.5)
                        break
                
                if not found_button:
                    # 如果没有找到特定按钮，尝试查找任何包含 "GitHub" 文本的元素
                    github_elements = page.locator(":text('GitHub')")
                    if github_elements.count() > 0:
                        # 模拟人类悬停操作
                        github_elements.first.hover()
                        human_like_delay(0.2, 0.5)
                        
                        # 模拟人类点击前延迟
                        human_like_delay(0.3, 0.8)
                        
                        github_elements.first.click()
                        print("✅ 点击包含 'GitHub' 文本的元素")
                        found_button = True
                
                if not found_button:
                    print("❌ 未找到 GitHub 登录按钮")
                    # 截图并尝试其他方法
                    page.screenshot(path="login_error_no_button.png")
                    
                    # 检查页面内容
                    page_content = page.content()
                    if "GitHub" not in page_content:
                        print("⚠️ 页面内容中没有找到 'GitHub' 文本")
                        print(f"页面标题: {page.title()}")
                        print(f"当前URL: {page.url}")
                    
                    raise Exception("GitHub 登录按钮未找到")
                    
            except Exception as e:
                print(f"⚠️ 点击 GitHub 按钮失败: {e}")
                # 尝试直接访问 GitHub OAuth URL
                try:
                    print("🔄 尝试直接访问 GitHub OAuth URL...")
                    oauth_url = "https://github.com/login/oauth/authorize"
                    page.goto(oauth_url, wait_until="domcontentloaded", timeout=30000)
                    human_like_delay(1.0, 2.0)
                except Exception as oauth_error:
                    print(f"❌ OAuth 重定向也失败: {oauth_error}")
                    raise

            # 4. 处理 GitHub 登录表单
            print("⏳ [Step 4] 等待跳转到 GitHub...")
            try:
                # 等待 URL 变更为 github.com
                page.wait_for_url(
                    lambda url: "github.com" in url, 
                    timeout=20000,
                    wait_until="domcontentloaded"
                )
                human_like_delay(1.0, 2.0)
                
                # 检查是否在登录页面
                current_url = page.url.lower()
                if "login" in current_url or "signin" in current_url:
                    print("🔒 输入账号密码...")
                    # 等待登录字段加载
                    try:
                        page.wait_for_selector("#login_field", timeout=15000)
                    except:
                        # 尝试其他选择器
                        page.wait_for_selector("input[name='login']", timeout=5000)
                    
                    # 模拟人类输入用户名
                    print("👤 模拟人类输入用户名...")
                    user_input_selectors = ["#login_field", "input[name='login']", "input[type='text']"]
                    user_input = None
                    
                    for selector in user_input_selectors:
                        if page.locator(selector).count() > 0:
                            user_input = page.locator(selector).first
                            break
                    
                    if user_input:
                        # 点击输入框前随机延迟
                        human_like_delay(0.3, 0.8)
                        user_input.click()
                        human_like_delay(0.2, 0.4)
                        
                        # 清空可能存在的文本
                        user_input.fill("")
                        human_like_delay(0.1, 0.3)
                        
                        # 模拟人类打字速度输入用户名
                        human_like_type(user_input, username, min_delay=40, max_delay=120)
                        print(f"✅ 用户名输入完成")
                        human_like_delay(0.5, 1.0)
                        
                        # 模拟人类输入密码
                        print("🔑 模拟人类输入密码...")
                        pass_input_selectors = ["#password", "input[name='password']", "input[type='password']"]
                        pass_input = None
                        
                        for selector in pass_input_selectors:
                            if page.locator(selector).count() > 0:
                                pass_input = page.locator(selector).first
                                break
                        
                        if pass_input:
                            # 点击输入框前随机延迟
                            human_like_delay(0.3, 0.8)
                            pass_input.click()
                            human_like_delay(0.2, 0.4)
                            
                            # 模拟人类打字速度输入密码
                            human_like_type(pass_input, password, min_delay=50, max_delay=150)
                            print(f"✅ 密码输入完成")
                            human_like_delay(0.8, 1.5)
                            
                            # 找到并点击登录按钮
                            print("🖱️ 准备点击登录按钮...")
                            commit_button_selectors = [
                                "input[name='commit']",
                                "button[type='submit']",
                                "button:has-text('Sign in')",
                                "[value='Sign in']"
                            ]
                            
                            for selector in commit_button_selectors:
                                if page.locator(selector).count() > 0:
                                    # 悬停并延迟后点击
                                    commit_button = page.locator(selector).first
                                    commit_button.hover()
                                    human_like_delay(0.3, 0.7)
                                    commit_button.click()
                                    print(f"✅ 登录表单已提交 (使用选择器: {selector})")
                                    break
                        else:
                            print("❌ 未找到密码输入框")
                    else:
                        print("❌ 未找到用户名输入框")
                    
                    # 点击后随机延迟
                    human_like_delay(2.0, 3.5)
                else:
                    print(f"ℹ️ 当前不在登录页面，URL: {current_url}")
            except Exception as e:
                print(f"ℹ️ GitHub 表单处理异常: {e}")
                page.screenshot(path="github_form_error.png")

            # 5. 【核心】处理 2FA 双重验证 (解决异地登录拦截)
            print("⏳ [Step 5] 等待可能的 2FA 验证...")
            human_like_delay(3.0, 5.0)
            
            # 检查是否在 2FA 页面
            current_url = page.url
            print(f"🔗 当前 URL: {current_url}")
            
            two_factor_detected = False
            for term in ["two-factor", "two_factor", "app_totp", "otp"]:
                if term in current_url.lower():
                    two_factor_detected = True
                    break
            
            if not two_factor_detected:
                # 检查页面元素
                for selector in ["#app_totp", "#otp", "input[name='otp']"]:
                    if page.locator(selector).count() > 0:
                        two_factor_detected = True
                        break
            
            if two_factor_detected:
                print("🔐 检测到 2FA 双重验证请求！")
                
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
                                otp_input = page.locator(selector).first
                                
                                # 模拟人类操作：悬停、点击、输入
                                otp_input.hover()
                                human_like_delay(0.2, 0.4)
                                otp_input.click()
                                human_like_delay(0.3, 0.6)
                                
                                # 模拟人类输入验证码
                                human_like_type(otp_input, token, min_delay=80, max_delay=200)
                                print(f"✅ 使用选择器 {selector} 填入验证码")
                                
                                # 点击后随机延迟
                                human_like_delay(0.5, 1.2)
                                
                                # 尝试提交表单
                                submit_selectors = ["button[type='submit']", "input[type='submit']", "button:has-text('Verify')"]
                                for submit_selector in submit_selectors:
                                    if page.locator(submit_selector).count() > 0:
                                        submit_button = page.locator(submit_selector).first
                                        submit_button.hover()
                                        human_like_delay(0.3, 0.7)
                                        submit_button.click()
                                        print(f"✅ 点击验证按钮: {submit_selector}")
                                        
                                        # 提交后等待
                                        human_like_delay(2.0, 3.5)
                                        break
                                break
                                
                    except Exception as e:
                        print(f"❌ 填入验证码失败: {e}")
                        page.screenshot(path="2fa_error.png")
                else:
                    print("❌ 致命错误: 检测到 2FA 但未配置 GH_2FA_SECRET Secret！")
                    page.screenshot(path="2fa_missing_secret.png")
                    execution_status = "failed"
                    execution_details["error_message"] = "2FA 密钥未配置"
                    return execution_status, execution_details

            # 6. 处理授权确认页 (Authorize App)
            human_like_delay(4.0, 6.0)
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
                            auth_button = page.locator(selector).first
                            auth_button.hover()
                            human_like_delay(0.3, 0.8)
                            auth_button.click()
                            print(f"✅ 点击授权按钮: {selector}")
                            
                            # 点击后等待
                            human_like_delay(2.5, 4.0)
                            break
                except Exception as auth_error:
                    print(f"⚠️ 授权点击失败: {auth_error}")

            # 7. 等待最终跳转结果
            print("⏳ [Step 6] 等待跳转回 ClawCloud 控制台...")
            human_like_delay(8.0, 12.0)
            
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except:
                print("⚠️ 页面加载超时，继续执行...")
            
            final_url = page.url
            execution_details["final_url"] = final_url
            print(f"📍 最终页面 URL: {final_url}")
            
            # 获取页面标题和内容片段用于验证
            page_title = page.title()
            execution_details["page_title"] = page_title
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

            # 9. 登录成功后执行额外操作
            if is_success and success_indicators:
                print(f"🎉🎉🎉 登录成功！成功指标: {', '.join(success_indicators)}")
                execution_status = "success"
                execution_details["success"] = True
                execution_details["success_indicators"] = success_indicators
                
                print("\n" + "="*50)
                print("🚀 [额外步骤] 开始执行登录后操作")
                print("="*50)
                
                # 9.1 刷新页面确保所有资源加载完成
                print("🔄 [步骤 9.1] 刷新页面...")
                try:
                    # 模拟人类刷新前的随机延迟
                    human_like_delay(1.0, 2.5)
                    page.reload(wait_until="domcontentloaded", timeout=30000)
                    human_like_delay(3.0, 5.0)
                    print("✅ 页面刷新完成")
                    
                    # 截图保存刷新后的页面
                    refresh_screenshot_path = "after_refresh.png"
                    page.screenshot(path=refresh_screenshot_path)
                    print(f"📸 已保存刷新后截图: {refresh_screenshot_path}")
                    
                except Exception as refresh_error:
                    print(f"⚠️ 刷新页面时出错: {refresh_error}")
                
                # 9.2 查找并点击 "App Launchpad" 按钮
                print("🔍 [步骤 9.2] 查找 App Launchpad 按钮...")
                try:
                    # 多种选择器来查找 App Launchpad 按钮
                    app_launchpad_selectors = [
                        "button:has-text('App Launchpad')",
                        "a:has-text('App Launchpad')",
                        "//button[contains(., 'App Launchpad')]",
                        "//a[contains(., 'App Launchpad')]",
                        "[href*='launchpad']",
                        "[href*='app-launchpad']",
                        ".app-launchpad",
                        "#app-launchpad",
                        "nav a:has-text('App')",
                        "nav button:has-text('Launchpad')"
                    ]
                    
                    button_found = False
                    for selector in app_launchpad_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                button = page.locator(selector).first
                                button.wait_for(state="visible", timeout=15000)
                                
                                print(f"✅ 找到 App Launchpad 按钮: {selector}")
                                
                                # 模拟人类操作：悬停、滚动、点击
                                button.hover()
                                human_like_delay(0.3, 0.8)
                                button.scroll_into_view_if_needed()
                                human_like_delay(0.5, 1.0)
                                
                                # 保存点击前的截图
                                before_click_path = "before_app_launchpad_click.png"
                                page.screenshot(path=before_click_path)
                                print(f"📸 已保存点击前截图: {before_click_path}")
                                
                                # 点击按钮前随机延迟
                                human_like_delay(0.4, 0.9)
                                button.click()
                                print(f"✅ 点击 App Launchpad 按钮: {selector}")
                                execution_details["app_launchpad_clicked"] = True
                                button_found = True
                                
                                # 点击后等待
                                human_like_delay(2.0, 3.5)
                                break
                        except Exception as selector_error:
                            print(f"   ⚠️ 选择器 {selector} 失败: {selector_error}")
                            continue
                    
                    if not button_found:
                        print("⚠️ 未找到 App Launchpad 按钮，尝试其他方法...")
                        
                        # 方法2: 查找所有包含 "Launchpad" 的元素
                        all_launchpad_elements = page.locator(":text('Launchpad')")
                        if all_launchpad_elements.count() > 0:
                            print(f"✅ 找到 {all_launchpad_elements.count()} 个包含 'Launchpad' 的元素")
                            
                            # 模拟人类操作：悬停、滚动
                            first_element = all_launchpad_elements.first
                            first_element.hover()
                            human_like_delay(0.3, 0.7)
                            first_element.scroll_into_view_if_needed()
                            
                            # 保存点击前的截图
                            before_click_path = "before_app_launchpad_click.png"
                            page.screenshot(path=before_click_path)
                            print(f"📸 已保存点击前截图: {before_click_path}")
                            
                            # 点击前随机延迟
                            human_like_delay(0.4, 0.8)
                            first_element.click()
                            execution_details["app_launchpad_clicked"] = True
                            print("✅ 点击第一个包含 'Launchpad' 的元素")
                            
                            # 点击后等待
                            human_like_delay(2.0, 3.5)
                        else:
                            print("❌ 未找到任何 App Launchpad 相关元素")
                            execution_details["app_launchpad_clicked"] = False
                
                except Exception as app_error:
                    print(f"❌ 点击 App Launchpad 按钮时出错: {app_error}")
                    execution_details["app_launchpad_clicked"] = False
                
                # 9.3 等待并验证 App Launchpad 模态窗口加载
                print("🔍 [步骤 9.3] 等待 App Launchpad 模态窗口加载...")
                try:
                    # 等待模态窗口出现
                    print("⏳ 等待模态窗口/弹出窗口出现...")
                    human_like_delay(3.0, 5.0)
                    
                    # 方法1: 等待特定模态窗口元素
                    modal_selectors = [
                        ".modal", ".modal-dialog", ".modal-content", ".modal-overlay", 
                        ".ant-modal", ".el-dialog", ".drawer", ".overlay",
                        "[role='dialog']", "[aria-modal='true']"
                    ]
                    
                    modal_detected = False
                    modal_element = None
                    
                    for selector in modal_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                modal_element = page.locator(selector).first
                                modal_element.wait_for(state="visible", timeout=10000)
                                print(f"✅ 检测到模态窗口元素: {selector}")
                                execution_details["app_launchpad_modal_detected"] = True
                                modal_detected = True
                                break
                        except:
                            continue
                    
                    # 方法2: 如果没有检测到标准模态元素，检查是否有新的UI元素出现
                    if not modal_detected:
                        print("⚠️ 未检测到标准模态窗口，检查是否有新内容出现...")
                        human_like_delay(3.0, 5.0)  # 给更多时间加载
                        
                        # 检查是否有常见弹出窗口内容
                        popup_indicators = [
                            "Applications", "Memory", "CPU", "Status", 
                            "Launchpad", "Close", "×", "✕", "❌"
                        ]
                        
                        page_text = page.content()
                        found_indicators = []
                        for indicator in popup_indicators:
                            if indicator in page_text:
                                found_indicators.append(indicator)
                        
                        if len(found_indicators) >= 2:
                            print(f"✅ 检测到弹出窗口内容，找到关键词: {', '.join(found_indicators)}")
                            execution_details["app_launchpad_modal_detected"] = True
                            modal_detected = True
                    
                    # 方法3: 检测屏幕是否变暗或有覆盖层
                    if not modal_detected:
                        try:
                            # 查找覆盖层（通常模态窗口会有背景覆盖）
                            overlays = page.locator("[class*='overlay'], [class*='backdrop'], [class*='mask']")
                            if overlays.count() > 0:
                                print("✅ 检测到覆盖层/遮罩层，可能是模态窗口背景")
                                execution_details["app_launchpad_modal_detected"] = True
                                modal_detected = True
                        except:
                            pass
                    
                    if modal_detected:
                        print("✅ App Launchpad 模态窗口已检测到")
                        execution_details["app_launchpad_loaded"] = True
                        
                        # 等待一小段时间让模态窗口完全加载
                        human_like_delay(2.0, 4.0)
                        
                        # 保存模态窗口截图
                        modal_screenshot_path = "app_launchpad_modal.png"
                        page.screenshot(path=modal_screenshot_path)
                        print(f"📸 已保存模态窗口截图: {modal_screenshot_path}")
                        
                        # 保存页面详细信息
                        page_content = page.content()
                        with open("app_launchpad_info.txt", "w", encoding="utf-8") as f:
                            f.write("=== App Launchpad 信息 ===\n")
                            f.write(f"检测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"模态窗口检测: {'是' if execution_details['app_launchpad_modal_detected'] else '否'}\n")
                            f.write(f"URL: {page.url}\n")
                            f.write(f"页面标题: {page.title()}\n")
                            
                            # 提取关键信息
                            keywords_to_find = ["Applications", "Memory", "CPU", "Status", "Running", "Stopped", "Launchpad"]
                            for keyword in keywords_to_find:
                                if keyword in page_content:
                                    f.write(f"找到关键词: {keyword}\n")
                            
                            # 如果可能，获取模态窗口内容
                            if modal_element:
                                try:
                                    modal_text = modal_element.text_content()[:500]  # 只取前500字符
                                    f.write(f"模态窗口内容预览: {modal_text}\n")
                                except:
                                    pass
                        
                        print("✅ App Launchpad 操作完成")
                        
                    else:
                        print("⚠️ 未检测到明显的模态窗口，但可能已成功打开")
                        execution_details["app_launchpad_loaded"] = False
                        
                        # 无论如何保存当前页面截图
                        human_like_delay(2.0, 3.0)
                        unknown_modal_path = "unknown_modal_state.png"
                        page.screenshot(path=unknown_modal_path)
                        print(f"📸 已保存当前状态截图: {unknown_modal_path}")
                
                except Exception as modal_error:
                    print(f"⚠️ 检测模态窗口时出错: {modal_error}")
                    execution_details["app_launchpad_loaded"] = False
                    
                    # 出错时也保存截图
                    error_modal_path = "modal_detection_error.png"
                    page.screenshot(path=error_modal_path)
                    print(f"📸 已保存错误状态截图: {error_modal_path}")
                
                print("✅✅✅ 所有任务完成")
                
            else:
                print("😭😭😭 登录失败。请下载 login_result.png 查看原因。")
                print(f"❌ 失败原因分析:")
                print(f"   - 最终 URL: {final_url}")
                print(f"   - 页面标题: {page_title}")
                print(f"   - 页面是否包含 'GitHub': {'github' in page_text.lower()}")
                print(f"   - 页面是否包含 'login': {'login' in page_text.lower()}")
                execution_status = "failed"
                execution_details["success"] = False
                execution_details["error_message"] = "登录验证失败"
                
                # 保存更多调试信息
                with open("debug_info.txt", "w") as f:
                    f.write(f"URL: {final_url}\n")
                    f.write(f"Title: {page_title}\n")
                    f.write(f"Contains GitHub: {'github' in page_text.lower()}\n")
                    f.write(f"Contains Login: {'login' in page_text.lower()}\n")

        except Exception as e:
            print(f"❌ 执行过程中发生异常: {e}")
            execution_status = "failed"
            execution_details["success"] = False
            execution_details["error_message"] = str(e)
            
            # 尝试截图保存错误状态
            try:
                page.screenshot(path="final_error.png")
                print("📸 已保存错误状态截图: final_error.png")
            except:
                pass
            
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
    
    return execution_status, execution_details

def main():
    """主函数，包含 Telegram 通知逻辑"""
    start_time = time.time()
    
    # 获取 Telegram 相关环境变量
    tele_bottoken = os.environ.get("GH_BOTTOKEN")
    tele_chatid = os.environ.get("GH_CHATID")
    zanghu = os.environ.get("ZANGHU", "Unknown Repository")
    
    # 检查 Telegram 配置
    if not tele_bottoken or not tele_chatid:
        print("⚠️ 警告: Telegram 机器人令牌或聊天ID未配置，将跳过通知")
    
    try:
        # 执行登录任务
        print("="*50)
        print(f"🚀 开始执行 ClawCloud 自动登录任务")
        print(f"📅 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📦 目标仓库: {zanghu}")
        print("="*50)
        
        status, details = run_login()
        
        end_time = time.time()
        execution_duration = round(end_time - start_time, 2)
        
        # 准备通知消息
        if status == "success":
            emoji = "🎉"
            status_text = "成功"
            
            # 添加 App Launchpad 操作状态
            app_status = ""
            if details.get("app_launchpad_clicked"):
                if details.get("app_launchpad_loaded"):
                    app_status = "✅ App Launchpad 已成功打开并加载"
                elif details.get("app_launchpad_modal_detected"):
                    app_status = "✅ App Launchpad 已打开（模态窗口已检测）"
                else:
                    app_status = "⚠️ App Launchpad 已点击但状态不确定"
            else:
                app_status = "❌ App Launchpad 未点击"
                
        else:
            emoji = "❌"
            status_text = "失败"
            app_status = "未执行"
        
        # 构建通知消息
        message = f"""
<b>ClawCloud 自动登录 {emoji}</b>

📊 <b>执行结果:</b> {status_text}
⏱️ <b>执行时长:</b> {execution_duration}秒
📅 <b>开始时间:</b> {details['start_time']}
🌐 <b>最终URL:</b> {details['final_url'][:100]}...
📄 <b>页面标题:</b> {details['page_title'][:50]}
🚀 <b>App Launchpad:</b> {app_status}
        """
        
        # 添加成功或失败的详细信息
        if status == "success":
            indicators = details.get('success_indicators', [])
            if indicators:
                message += f"\n✅ <b>成功指标:</b>\n• " + "\n• ".join(indicators)
        else:
            error_msg = details.get('error_message', '未知错误')
            message += f"\n❌ <b>错误信息:</b> {error_msg}"
        
        print(f"\n📤 准备发送 Telegram 通知...")
        print(f"   状态: {status_text}")
        print(f"   时长: {execution_duration}秒")
        print(f"   App Launchpad 状态: {app_status}")
        
        # 发送 Telegram 通知（如果配置了）
        if tele_bottoken and tele_chatid:
            send_telegram_notification(tele_bottoken, tele_chatid, message, zanghu)
        else:
            print("⚠️ 跳过 Telegram 通知 (未配置)")
        
        # 根据执行状态退出
        if status == "success":
            print(f"\n✅ 任务执行完成，状态: {status_text}")
            exit(0)
        else:
            print(f"\n❌ 任务执行完成，状态: {status_text}")
            exit(1)
            
    except Exception as e:
        # 处理未捕获的异常
        error_time = time.time()
        duration = round(error_time - start_time, 2)
        
        error_message = f"""
<b>ClawCloud 自动登录 💥</b>

📊 <b>执行结果:</b> 异常失败
⏱️ <b>执行时长:</b> {duration}秒
📅 <b>开始时间:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}
❌ <b>错误信息:</b> {str(e)[:200]}
        """
        
        print(f"💥 未捕获的异常: {e}")
        
        # 发送异常通知
        if tele_bottoken and tele_chatid:
            send_telegram_notification(tele_bottoken, tele_chatid, error_message, zanghu)
        
        exit(1)

if __name__ == "__main__":
    main()
