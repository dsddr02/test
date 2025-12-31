# 文件名: login_script.py
# 作用: 自动登录 ClawCloud Run，支持 GitHub 账号密码 + 2FA 自动验证

import os
import time
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
        "app_launchpad_loaded": False
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
                storage_state=None,  # 确保不加载任何存储状态
                permissions=[],  # 禁用所有存储
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
                page.screenshot(path="github_form_error.png")

            # 5. 【核心】处理 2FA 双重验证 (解决异地登录拦截)
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
                    execution_status = "failed"
                    execution_details["error_message"] = "2FA 密钥未配置"
                    return execution_status, execution_details

            # 6. 处理授权确认页 (Authorize App)
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
            time.sleep(10)
            page.wait_for_load_state("networkidle")
            
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
                    page.reload(wait_until="networkidle")
                    time.sleep(5)
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
                                button.wait_for(state="visible", timeout=10000)
                                
                                print(f"✅ 找到 App Launchpad 按钮: {selector}")
                                
                                # 确保按钮可见且在视图中
                                button.scroll_into_view_if_needed()
                                time.sleep(1)
                                
                                # 点击按钮
                                button.click()
                                print(f"✅ 点击 App Launchpad 按钮: {selector}")
                                execution_details["app_launchpad_clicked"] = True
                                button_found = True
                                
                                # 等待页面加载或跳转
                                time.sleep(5)
                                page.wait_for_load_state("networkidle")
                                
                                # 截图保存点击后的页面
                                click_screenshot_path = "after_app_launchpad_click.png"
                                page.screenshot(path=click_screenshot_path)
                                print(f"📸 已保存点击后截图: {click_screenshot_path}")
                                
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
                            all_launchpad_elements.first.click()
                            execution_details["app_launchpad_clicked"] = True
                            print("✅ 点击第一个包含 'Launchpad' 的元素")
                            
                            # 等待并截图
                            time.sleep(5)
                            page.wait_for_load_state("networkidle")
                            page.screenshot(path="after_launchpad_click.png")
                            
                        else:
                            print("❌ 未找到任何 App Launchpad 相关元素")
                            execution_details["app_launchpad_clicked"] = False
                
                except Exception as app_error:
                    print(f"❌ 点击 App Launchpad 按钮时出错: {app_error}")
                    execution_details["app_launchpad_clicked"] = False
                
                # 9.3 验证 App Launchpad 是否加载成功
                print("🔍 [步骤 9.3] 验证 App Launchpad 加载状态...")
                try:
                    # 等待一段时间让页面完全加载
                    time.sleep(8)
                    page.wait_for_load_state("networkidle")
                    
                    # 获取当前页面信息
                    current_url_after_click = page.url
                    current_title_after_click = page.title()
                    
                    print(f"   📍 点击后 URL: {current_url_after_click}")
                    print(f"   📄 点击后标题: {current_title_after_click}")
                    
                    # 检查是否成功加载 App Launchpad
                    page_content = page.content().lower()
                    app_launchpad_indicators = [
                        "Applications",
                        "Memory",
                        "CPU",
                        "Status"
                    ]
                    
                    indicators_found = []
                    for indicator in app_launchpad_indicators:
                        if indicator in page_content:
                            indicators_found.append(indicator)
                    
                    if len(indicators_found) >= 2:
                        print(f"✅ App Launchpad 加载成功，找到关键词: {', '.join(indicators_found)}")
                        execution_details["app_launchpad_loaded"] = True
                        
                        # 保存最终截图
                        final_screenshot_path = "app_launchpad_final.png"
                        page.screenshot(path=final_screenshot_path)
                        print(f"📸 已保存 App Launchpad 最终截图: {final_screenshot_path}")
                        
                        # 保存页面信息
                        with open("page_info.txt", "w") as f:
                            f.write(f"最终URL: {current_url_after_click}\n")
                            f.write(f"最终标题: {current_title_after_click}\n")
                            f.write(f"找到的关键词: {', '.join(indicators_found)}\n")
                            f.write(f"App Launchpad 点击状态: {execution_details['app_launchpad_clicked']}\n")
                            f.write(f"App Launchpad 加载状态: {execution_details['app_launchpad_loaded']}\n")
                    else:
                        print("⚠️ App Launchpad 加载状态不确定")
                        execution_details["app_launchpad_loaded"] = False
                
                except Exception as verify_error:
                    print(f"❌ 验证 App Launchpad 加载状态时出错: {verify_error}")
                    execution_details["app_launchpad_loaded"] = False
                
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
                app_status += "✅ App Launchpad 点击成功"
                if details.get("app_launchpad_loaded"):
                    app_status += "并加载成功"
                else:
                    app_status += "但加载状态不确定"
            else:
                app_status = "⚠️ App Launchpad 未点击"
                
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
