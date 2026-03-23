import os
import time
import random
import re
import shutil
import tempfile
import requests
import pyotp
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def send_telegram_notification(bot_token, chat_id, message, zanghu):
    """发送 Telegram 通知"""
    try:
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

def human_like_delay(min_seconds=0.5, max_seconds=2.0):
    """模拟人类随机延迟 - 增加基础延迟时间"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay

def extended_delay(min_seconds=2.0, max_seconds=5.0):
    """扩展延迟，用于关键步骤"""
    delay = random.uniform(min_seconds, max_seconds)
    print(f"⏳ 等待 {delay:.1f} 秒...")
    time.sleep(delay)
    return delay

def human_like_type(element, text, min_delay=50, max_delay=150):
    """模拟人类打字速度（增加延迟）"""
    for char in text:
        element.type(char)
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

def wait_for_page_fully_loaded(page, timeout=30000, step_name=""):
    """
    等待页面完全加载
    包括 DOM 加载、网络空闲和关键元素
    """
    print(f"⏳ [{step_name}] 等待页面完全加载...")
    try:
        # 等待 DOM 内容加载
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        print(f"   ✅ DOM 加载完成")
        
        # 额外等待，让页面开始渲染
        human_like_delay(1.0, 2.0)
        
        # 尝试等待网络空闲（不强制，避免超时）
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
            print(f"   ✅ 网络空闲")
        except:
            print(f"   ⚠️ 网络未完全空闲，继续执行")
        
        # 等待页面稳定（检查 loading 指示器）
        try:
            page.wait_for_function(
                """
                () => {
                    const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"], [class*="loader"]');
                    for (let el of loadingElements) {
                        if (el.offsetParent !== null && window.getComputedStyle(el).display !== 'none') {
                            return false;
                        }
                    }
                    return true;
                }
                """,
                timeout=15000
            )
            print(f"   ✅ 页面稳定，无 loading 指示器")
        except:
            print(f"   ⚠️ 可能有 loading 指示器仍在运行")
            
    except PlaywrightTimeoutError:
        print(f"   ⚠️ 页面加载超时，但继续执行")
    
    # 最终额外等待
    human_like_delay(1.5, 3.0)

def take_screenshot(page, filename, description=""):
    """截图并添加描述"""
    try:
        page.screenshot(path=filename, full_page=True)
        if description:
            print(f"📸 {description} - 已保存截图: {filename}")
        else:
            print(f"📸 已保存截图: {filename}")
        return True
    except Exception as e:
        print(f"⚠️ 截图失败 {filename}: {e}")
        return False

def check_login_success(page, final_url, page_text, page_title):
    """
    检查是否真正登录成功
    返回: (is_success, success_indicators)
    """
    success_indicators = []
    is_success = False
    
    # 关键检查点1: 页面标题不能为空
    if page_title and page_title.strip():
        success_indicators.append(f"页面标题存在: {page_title}")
        is_success = True
    else:
        print("⚠️ 页面标题为空，可能未完全加载或未登录成功")
    
    # 关键检查点2: 必须包含关键元素
    critical_keywords = ["App Launchpad", "Launchpad", "Dashboard", "Console", "ClawCloud"]
    found_critical = False
    for keyword in critical_keywords:
        if keyword.lower() in page_text.lower():
            success_indicators.append(f"找到关键文本: {keyword}")
            found_critical = True
            is_success = True
    
    if not found_critical:
        print("⚠️ 未找到关键文本，可能登录未成功")
        is_success = False
    
    # 检查点3: URL不能包含错误或登录相关词
    if "error" in final_url.lower() or "login" in final_url.lower() or "two-factor" in final_url.lower():
        print(f"⚠️ URL包含错误或登录相关词: {final_url}")
        is_success = False
    
    # 检查点4: 页面包含导航元素（登录成功后的特征）
    try:
        if page.locator("nav, header, footer, .dashboard, .sidebar, [role='navigation']").count() > 0:
            success_indicators.append("找到页面导航元素")
            is_success = True
    except:
        pass
    
    return is_success, success_indicators

def perform_login_attempt(attempt_number, username, password, totp_secret):
    """
    单次登录尝试
    返回: (success, execution_details, browser, page, context)
    """
    print(f"\n{'='*60}")
    print(f"🔄 第 {attempt_number} 次登录尝试")
    print(f"{'='*60}")
    
    attempt_details = {
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "success": False,
        "error_message": "",
        "final_url": "",
        "page_title": "",
        "balance": "未提取",
        "app_launchpad_clicked": False,
        "app_launchpad_loaded": False,
        "app_launchpad_modal_detected": False,
        "real_login_success": False,
        "attempt_number": attempt_number
    }
    
    temp_user_data_dir = tempfile.mkdtemp(prefix=f"browser_temp_{attempt_number}_")
    
    try:
        with sync_playwright() as p:
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
                timeout=90000  # 增加全局超时到90秒
            )
            
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
                }
            )
            
            page = context.new_page()
            page.set_default_timeout(90000)  # 增加页面超时到90秒
            
            # 反检测脚本
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
                window.chrome = { runtime: {} };
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );
                Object.defineProperty(document, 'hidden', { value: false });
                Object.defineProperty(document, 'visibilityState', { value: 'visible' });
            """)
            
            target_url = "https://us-west-1.run.claw.cloud/"
            print(f"🌐 访问目标网站: {target_url}")
            
            # 清除缓存
            context.clear_cookies()
            
            # 访问页面
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                wait_for_page_fully_loaded(page, step_name="初始页面")
                take_screenshot(page, f"step1_initial_page_attempt_{attempt_number}.png", "初始页面")
            except Exception as nav_error:
                print(f"⚠️ 页面加载异常: {nav_error}")
                raise
            
            # 点击 GitHub 登录按钮
            print("🔍 寻找 GitHub 按钮...")
            try:
                login_selectors = [
                    "button:has-text('GitHub')",
                    "a:has-text('GitHub')",
                    "[data-provider='github']",
                    ".github-login"
                ]
                
                found_button = False
                for selector in login_selectors:
                    if page.locator(selector).count() > 0:
                        login_button = page.locator(selector).first
                        login_button.wait_for(state="visible", timeout=15000)
                        login_button.hover()
                        human_like_delay(0.3, 0.8)
                        login_button.click()
                        print(f"✅ 点击 GitHub 按钮")
                        found_button = True
                        break
                
                if not found_button:
                    raise Exception("GitHub 登录按钮未找到")
                    
                # 点击后等待跳转
                extended_delay(2.0, 4.0)
                
            except Exception as e:
                print(f"❌ 点击 GitHub 按钮失败: {e}")
                raise
            
            # 处理 GitHub 登录
            try:
                page.wait_for_url(lambda url: "github.com" in url, timeout=20000)
                wait_for_page_fully_loaded(page, step_name="GitHub 登录页")
                take_screenshot(page, f"step2_github_login_attempt_{attempt_number}.png", "GitHub 登录页")
                
                current_url = page.url.lower()
                if "login" in current_url or "signin" in current_url:
                    print("🔒 输入账号密码...")
                    
                    # 等待输入框可见
                    page.wait_for_selector("#login_field", timeout=15000)
                    extended_delay(0.5, 1.5)
                    
                    # 输入用户名
                    user_input = page.locator("#login_field").first
                    user_input.click()
                    human_like_delay(0.3, 0.6)
                    user_input.fill("")
                    human_like_type(user_input, username, min_delay=60, max_delay=150)
                    print(f"✅ 用户名输入完成")
                    human_like_delay(0.8, 1.5)
                    
                    # 输入密码
                    pass_input = page.locator("#password").first
                    pass_input.click()
                    human_like_delay(0.3, 0.6)
                    human_like_type(pass_input, password, min_delay=70, max_delay=180)
                    print(f"✅ 密码输入完成")
                    human_like_delay(1.0, 2.0)
                    
                    # 截图（输入账号密码后）
                    take_screenshot(page, f"step3_credentials_entered_attempt_{attempt_number}.png", "输入账号密码后")
                    
                    # 点击登录
                    commit_button = page.locator("input[name='commit']").first
                    commit_button.hover()
                    human_like_delay(0.5, 1.0)
                    commit_button.click()
                    print(f"✅ 登录表单已提交")
                    
                    # 等待提交后的跳转
                    extended_delay(3.0, 5.0)
                    
            except Exception as e:
                print(f"⚠️ GitHub 表单处理异常: {e}")
            
            # 处理 2FA
            print("🔐 等待 2FA 验证...")
            extended_delay(3.0, 6.0)
            
            # 检查是否在2FA页面
            two_factor_detected = False
            current_url = page.url
            
            if "two-factor" in current_url.lower() or "sessions/two-factor" in current_url.lower():
                two_factor_detected = True
            
            if not two_factor_detected:
                if page.locator("#app_totp").count() > 0:
                    two_factor_detected = True
            
            if two_factor_detected:
                print("🔐 检测到 2FA 双重验证请求！")
                if totp_secret:
                    totp = pyotp.TOTP(totp_secret)
                    token = totp.now()
                    print(f"   生成的验证码: {token}")
                    
                    # 等待验证码输入框可见
                    page.wait_for_selector("#app_totp", timeout=15000)
                    extended_delay(1.0, 2.0)
                    
                    # 输入验证码
                    otp_input = page.locator("#app_totp").first
                    otp_input.hover()
                    human_like_delay(0.3, 0.6)
                    otp_input.click()
                    human_like_type(otp_input, token, min_delay=100, max_delay=250)
                    print(f"✅ 填入验证码")
                    
                    # 截图（填入验证码后）
                    take_screenshot(page, f"step4_2fa_entered_attempt_{attempt_number}.png", "填入验证码后")
                    
                    # 等待验证码被识别和验证
                    extended_delay(2.0, 3.0)
                    
                    print("⏳ 等待页面自动跳转...")
                    
                    # 等待页面跳转（最多等待30秒）
                    try:
                        page.wait_for_url(
                            lambda url: "two-factor" not in url.lower() and "sessions" not in url.lower(),
                            timeout=30000
                        )
                        print("✅ 页面已自动跳转，验证成功")
                        extended_delay(2.0, 4.0)
                    except:
                        # 如果没有自动跳转，尝试手动点击提交按钮
                        print("⚠️ 页面未自动跳转，尝试手动点击提交按钮...")
                        try:
                            submit_button = page.locator("button[type='submit']").first
                            if submit_button.is_visible(timeout=5000):
                                submit_button.hover()
                                human_like_delay(0.3, 0.7)
                                submit_button.click()
                                print(f"✅ 手动点击验证按钮")
                                extended_delay(3.0, 5.0)
                        except:
                            print("⚠️ 未找到提交按钮，继续等待...")
                else:
                    raise Exception("2FA 密钥未配置")
            else:
                print("ℹ️ 未检测到 2FA 验证")
            
            # 处理授权确认页
            print("⏳ 检查授权页面...")
            extended_delay(3.0, 5.0)
            current_url = page.url.lower()
            
            if "authorize" in current_url or "oauth" in current_url:
                print("⚠️ 检测到授权请求，尝试点击 Authorize...")
                try:
                    auth_button = page.locator("button:has-text('Authorize')").first
                    auth_button.wait_for(state="visible", timeout=10000)
                    auth_button.hover()
                    human_like_delay(0.5, 1.0)
                    auth_button.click()
                    print(f"✅ 点击授权按钮")
                    extended_delay(3.0, 5.0)
                except:
                    print("⚠️ 未找到授权按钮，可能已授权")
            
            # 等待最终跳转回 ClawCloud
            print("⏳ 等待跳转回 ClawCloud...")
            extended_delay(5.0, 8.0)
            
            # 等待页面完全加载
            try:
                page.wait_for_url(lambda url: "claw.cloud" in url, timeout=30000)
                print("✅ 已跳转到 ClawCloud")
                
                # 重要：等待页面完全加载，特别是控制台内容
                wait_for_page_fully_loaded(page, step_name="ClawCloud 控制台")
                
                # 额外等待确保动态内容加载
                extended_delay(3.0, 6.0)
                
            except Exception as e:
                print(f"⚠️ 等待跳转异常: {e}")
            
            final_url = page.url
            attempt_details["final_url"] = final_url
            page_title = page.title()
            attempt_details["page_title"] = page_title
            print(f"📍 最终页面 URL: {final_url}")
            print(f"📄 页面标题: {page_title}")
            
            # 保存最终截图
            take_screenshot(page, f"step5_final_page_attempt_{attempt_number}.png", "最终页面")
            
            # 检查是否真正登录成功
            page_text = page.content()
            is_success, indicators = check_login_success(page, final_url, page_text, page_title)
            
            if is_success:
                print(f"✅ 第 {attempt_number} 次尝试登录成功！")
                print(f"   成功指标: {indicators}")
                attempt_details["success"] = True
                attempt_details["real_login_success"] = True
                attempt_details["success_indicators"] = indicators
                
                # 执行后续操作（余额提取、App Launchpad等）
                perform_post_login_actions(page, attempt_details, attempt_number)
                
                # 返回成功
                return True, attempt_details, browser, context, page
            else:
                print(f"❌ 第 {attempt_number} 次尝试登录失败")
                print(f"   失败原因: 未检测到登录成功标志")
                attempt_details["error_message"] = "登录验证失败"
                
                # 关闭浏览器
                browser.close()
                return False, attempt_details, None, None, None
                
    except Exception as e:
        print(f"❌ 第 {attempt_number} 次尝试发生异常: {e}")
        attempt_details["error_message"] = str(e)
        return False, attempt_details, None, None, None

def perform_post_login_actions(page, details, attempt_number):
    """执行登录后的操作（余额提取、App Launchpad等）- 增加更多等待"""
    print("\n" + "="*50)
    print("🚀 [额外步骤] 开始执行登录后操作")
    print("="*50)
    
    # 步骤1: 等待页面完全稳定
    print("📌 [步骤 0] 等待控制台完全加载...")
    extended_delay(3.0, 5.0)
    wait_for_page_fully_loaded(page, step_name="控制台准备")
    
    # 步骤2: 刷新页面确保所有资源加载完成
    print("🔄 [步骤 1] 刷新页面...")
    try:
        extended_delay(1.0, 2.5)
        page.reload(wait_until="domcontentloaded", timeout=30000)
        
        # 刷新后等待页面完全加载
        extended_delay(3.0, 5.0)
        wait_for_page_fully_loaded(page, step_name="刷新后页面")
        
        take_screenshot(page, f"step6_after_refresh_attempt_{attempt_number}.png", "刷新页面后")
        print("✅ 页面刷新完成")
        
    except Exception as refresh_error:
        print(f"⚠️ 刷新页面时出错: {refresh_error}")
    
    # 步骤3: 提取余额（增加等待时间）
    print("💰 [步骤 2] 尝试提取账户余额...")
    try:
        # 等待余额元素出现
        extended_delay(2.0, 4.0)
        
        balance_selectors = [
            "text=/$[0-9.,]+",
            "text=/¥[0-9.,]+",
            "text=/€[0-9.,]+",
            "text=/£[0-9.,]+",
            "[class*='balance']",
            "[class*='credit']",
            "[class*='amount']",
            "//*[contains(text(), '$') and not(contains(text(), '$$'))]"
        ]
        
        balance_found = False
        raw_balance = "未找到"
        
        # 等待最多15秒让余额信息加载
        for i in range(3):  # 最多尝试3次
            for selector in balance_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        balance_elem = page.locator(selector).first
                        if balance_elem.is_visible(timeout=3000):
                            raw_balance = balance_elem.inner_text(timeout=5000).strip()
                            
                            if "$" in raw_balance or "€" in raw_balance or "¥" in raw_balance:
                                currency_match = re.search(r'([$€¥£])\s*([0-9,]+(?:\.[0-9]+)?)', raw_balance)
                                if currency_match:
                                    currency_symbol = currency_match.group(1)
                                    amount = currency_match.group(2)
                                    raw_balance = f"{currency_symbol}{amount}"
                                
                                print(f"💰 提取到的余额: {raw_balance}")
                                balance_found = True
                                break
                except:
                    continue
            
            if balance_found:
                break
            
            if i < 2:  # 如果不是最后一次尝试
                print(f"   ⏳ 等待余额加载，第 {i+1}/3 次尝试...")
                extended_delay(2.0, 3.0)
        
        if not balance_found:
            # 尝试正则匹配
            page_text = page.content()
            currency_patterns = [r'\$\s*[\d,]+(?:\.\d{2})?', r'€\s*[\d,]+(?:\.\d{2})?']
            for pattern in currency_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    raw_balance = matches[0].strip()
                    print(f"💰 正则匹配到的余额: {raw_balance}")
                    balance_found = True
                    break
        
        details["balance"] = raw_balance if balance_found else "未找到"
        
        if balance_found:
            print(f"✅ 成功提取余额: {raw_balance}")
        else:
            print("⚠️ 未能提取到余额信息")
            
    except Exception as balance_error:
        print(f"❌ 提取余额时出错: {balance_error}")
        details["balance"] = "提取失败"
    
    # 步骤4: 查找并点击 App Launchpad（增加等待时间）
    print("🔍 [步骤 3] 查找 App Launchpad 按钮...")
    extended_delay(2.0, 4.0)
    
    try:
        app_launchpad_selectors = [
            "button:has-text('App Launchpad')",
            "a:has-text('App Launchpad')",
            "//button[contains(., 'App Launchpad')]",
            "[href*='launchpad']",
            "button:has-text('Launchpad')",
            "a:has-text('Launchpad')"
        ]
        
        button_found = False
        for selector in app_launchpad_selectors:
            try:
                if page.locator(selector).count() > 0:
                    button = page.locator(selector).first
                    if button.is_visible(timeout=10000):
                        print(f"✅ 找到 App Launchpad 按钮: {selector}")
                        
                        # 滚动到按钮位置
                        button.scroll_into_view_if_needed()
                        extended_delay(0.5, 1.0)
                        
                        # 悬停
                        button.hover()
                        human_like_delay(0.5, 1.0)
                        
                        # 点击
                        button.click()
                        print(f"✅ 点击 App Launchpad 按钮")
                        details["app_launchpad_clicked"] = True
                        button_found = True
                        break
            except:
                continue
        
        if not button_found:
            # 尝试查找任何包含 Launchpad 的元素
            print("⚠️ 未找到标准按钮，尝试查找包含 'Launchpad' 的元素...")
            all_launchpad = page.locator(":text('Launchpad')")
            if all_launchpad.count() > 0:
                element = all_launchpad.first
                element.scroll_into_view_if_needed()
                extended_delay(0.5, 1.0)
                element.click()
                details["app_launchpad_clicked"] = True
                print("✅ 点击包含 'Launchpad' 的元素")
            else:
                print("❌ 未找到任何 App Launchpad 相关元素")
                details["app_launchpad_clicked"] = False
        
        # 步骤5: 等待模态窗口加载
        if details["app_launchpad_clicked"]:
            print("🔍 [步骤 4] 等待 App Launchpad 模态窗口加载...")
            
            # 等待模态窗口出现
            extended_delay(3.0, 5.0)
            
            modal_selectors = [
                ".modal", ".modal-dialog", "[role='dialog']", 
                ".ant-modal", ".el-dialog", ".drawer",
                "[class*='modal']", "[class*='dialog']"
            ]
            
            modal_detected = False
            max_wait_attempts = 5  # 最多等待5次
            
            for attempt in range(max_wait_attempts):
                for selector in modal_selectors:
                    if page.locator(selector).count() > 0:
                        modal = page.locator(selector).first
                        if modal.is_visible(timeout=3000):
                            print(f"✅ 检测到模态窗口: {selector}")
                            modal_detected = True
                            break
                
                if modal_detected:
                    break
                
                if attempt < max_wait_attempts - 1:
                    print(f"   ⏳ 等待模态窗口出现... ({attempt + 1}/{max_wait_attempts})")
                    extended_delay(2.0, 3.0)
            
            if not modal_detected:
                # 检查页面内容判断是否打开
                page_text = page.content()
                if "Memory" in page_text or "CPU" in page_text or "Status" in page_text:
                    print("✅ 检测到模态窗口内容（通过关键词）")
                    modal_detected = True
            
            details["app_launchpad_modal_detected"] = modal_detected
            details["app_launchpad_loaded"] = modal_detected
            
            if modal_detected:
                print("✅ App Launchpad 模态窗口已检测到")
                # 等待模态窗口内容加载
                extended_delay(2.0, 4.0)
                take_screenshot(page, f"step7_app_launchpad_modal_attempt_{attempt_number}.png", "App Launchpad 模态窗口")
            else:
                print("⚠️ 未检测到模态窗口，但可能已打开")
                take_screenshot(page, f"step7_unknown_modal_state_attempt_{attempt_number}.png", "未知状态")
                
    except Exception as app_error:
        print(f"❌ App Launchpad 操作失败: {app_error}")
        details["app_launchpad_clicked"] = False
    
    print("✅✅✅ 所有任务完成")
    extended_delay(2.0, 3.0)  # 最后等待确保所有操作完成

def main():
    """主函数，包含重试机制"""
    start_time = time.time()
    max_retries = 3
    
    # 获取环境变量
    username = os.environ.get("GH_USERNAME")
    password = os.environ.get("GH_PASSWORD")
    totp_secret = os.environ.get("GH_2FA_SECRET")
    tele_bottoken = os.environ.get("GH_BOTTOKEN")
    tele_chatid = os.environ.get("GH_CHATID")
    zanghu = os.environ.get("ZANGHU", "Unknown Repository")
    
    # 检查必要配置
    if not username or not password:
        print("❌ 错误: 必须设置 GH_USERNAME 和 GH_PASSWORD 环境变量。")
        if tele_bottoken and tele_chatid:
            send_telegram_notification(tele_bottoken, tele_chatid, 
                "❌ ClawCloud 自动登录失败: 未配置用户名或密码", zanghu)
        exit(1)
    
    print("="*50)
    print(f"🚀 开始执行 ClawCloud 自动登录任务")
    print(f"📅 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📦 目标仓库: {zanghu}")
    print(f"🔄 最大重试次数: {max_retries}")
    print("="*50)
    
    # 重试循环
    attempt = 1
    last_details = None
    
    while attempt <= max_retries:
        success, details, browser, context, page = perform_login_attempt(attempt, username, password, totp_secret)
        last_details = details
        
        if success:
            print(f"\n🎉 登录成功！共尝试 {attempt} 次")
            execution_status = "success"
            
            # 清理浏览器
            if browser:
                try:
                    extended_delay(1.0, 2.0)
                    browser.close()
                except:
                    pass
            break
        else:
            print(f"\n⚠️ 第 {attempt} 次尝试失败")
            
            # 清理浏览器（如果还没关闭）
            if browser:
                try:
                    browser.close()
                except:
                    pass
            
            if attempt < max_retries:
                wait_time = random.uniform(15, 45)  # 增加重试等待时间
                print(f"⏳ 等待 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"❌ 已达到最大重试次数 ({max_retries})，登录失败")
                execution_status = "failed"
                break
        
        attempt += 1
    
    # 计算执行时长
    end_time = time.time()
    execution_duration = round(end_time - start_time, 2)
    
    # 准备通知消息
    if execution_status == "success" and last_details:
        emoji = "🎉"
        status_text = f"成功 (尝试 {last_details.get('attempt_number', '?')} 次)"
        
        app_status = ""
        if last_details.get("app_launchpad_clicked"):
            if last_details.get("app_launchpad_loaded"):
                app_status = "✅ App Launchpad 已成功打开并加载"
            elif last_details.get("app_launchpad_modal_detected"):
                app_status = "✅ App Launchpad 已打开（模态窗口已检测）"
            else:
                app_status = "⚠️ App Launchpad 已点击但状态不确定"
        else:
            app_status = "❌ App Launchpad 未点击"
        
        message = f"""
<b>ClawCloud 自动登录 {emoji}</b>

📊 <b>执行结果:</b> {status_text}
🔄 <b>重试次数:</b> {attempt}/{max_retries}
⏱️ <b>执行时长:</b> {execution_duration}秒
📅 <b>开始时间:</b> {last_details['start_time']}
🌐 <b>最终URL:</b> {last_details.get('final_url', 'N/A')[:100]}...
📄 <b>页面标题:</b> {last_details.get('page_title', 'N/A')[:50]}
💰 <b>账户余额:</b> {last_details.get('balance', '未提取')}
🚀 <b>App Launchpad:</b> {app_status}
        """
        
        if last_details.get('success_indicators'):
            message += f"\n✅ <b>成功指标:</b>\n• " + "\n• ".join(last_details['success_indicators'])
            
    else:
        emoji = "❌"
        status_text = f"失败 (尝试 {max_retries} 次)"
        
        error_msg = last_details.get('error_message', '未知错误') if last_details else '未知错误'
        message = f"""
<b>ClawCloud 自动登录 {emoji}</b>

📊 <b>执行结果:</b> {status_text}
🔄 <b>重试次数:</b> {max_retries}/{max_retries}
⏱️ <b>执行时长:</b> {execution_duration}秒
❌ <b>错误信息:</b> {error_msg}
        """
    
    print(f"\n📤 准备发送 Telegram 通知...")
    print(f"   状态: {status_text}")
    print(f"   重试次数: {attempt}/{max_retries}")
    
    # 发送 Telegram 通知
    if tele_bottoken and tele_chatid:
        send_telegram_notification(tele_bottoken, tele_chatid, message, zanghu)
    else:
        print("⚠️ 跳过 Telegram 通知 (未配置)")
    
    # 退出
    if execution_status == "success":
        print(f"\n✅ 任务执行完成，状态: {status_text}")
        exit(0)
    else:
        print(f"\n❌ 任务执行完成，状态: {status_text}")
        exit(1)

if __name__ == "__main__":
    main()
