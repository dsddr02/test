# 文件名: login_script.py
# 作用: 自动登录 ClawCloud Run，支持 GitHub 账号密码 + 2FA 自动验证

import os
import time
import pyotp  # 用于生成 2FA 验证码
from playwright.sync_api import sync_playwright

def take_screenshot(page, step_name, counter=0):
    """辅助函数：保存截图并添加序号"""
    if counter > 0:
        filename = f"screenshot_{counter:02d}_{step_name}.png"
    else:
        filename = f"screenshot_{step_name}.png"
    
    page.screenshot(path=filename)
    print(f"📸 已保存截图: {filename}")
    return filename

def run_login():
    # 截图计数器
    screenshot_counter = 1
    
    # 1. 获取环境变量中的敏感信息
    username = os.environ.get("GH_USERNAME")
    password = os.environ.get("GH_PASSWORD")
    totp_secret = os.environ.get("GH_2FA_SECRET")

    if not username or not password:
        print("❌ 错误: 必须设置 GH_USERNAME 和 GH_PASSWORD 环境变量。")
        return

    print("🚀 [Step 1] 启动浏览器...")
    with sync_playwright() as p:
        # 启动浏览器 (headless=True 表示无头模式，适合服务器运行)
        browser = p.chromium.launch(headless=True)
        # 设置大一点的分辨率，避免页面布局错乱
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # 初始页面截图
        take_screenshot(page, "01_initial_browser", screenshot_counter)
        screenshot_counter += 1

        # 2. 访问 ClawCloud 登录页
        target_url = "https://us-west-1.run.claw.cloud/"
        print(f"🌐 [Step 2] 正在访问: {target_url}")
        page.goto(target_url)
        page.wait_for_load_state("networkidle")
        
        # 访问后截图
        take_screenshot(page, "02_clawcloud_landing_page", screenshot_counter)
        screenshot_counter += 1

        # 3. 点击 GitHub 登录按钮
        print("🔍 [Step 3] 寻找 GitHub 按钮...")
        try:
            # 精确查找包含 'GitHub' 文本的按钮
            login_button = page.locator("button:has-text('GitHub')")
            login_button.wait_for(state="visible", timeout=10000)
            
            # 点击前截图
            take_screenshot(page, "03_before_github_click", screenshot_counter)
            screenshot_counter += 1
            
            login_button.click()
            print("✅ GitHub 按钮已点击")
            
            # 点击后截图
            take_screenshot(page, "04_after_github_click", screenshot_counter)
            screenshot_counter += 1
            
        except Exception as e:
            print(f"⚠️ 未找到 GitHub 按钮 (可能已自动登录或页面变动): {e}")
            take_screenshot(page, "error_github_button_not_found", screenshot_counter)
            screenshot_counter += 1

        # 4. 处理 GitHub 登录表单
        print("⏳ [Step 4] 等待跳转到 GitHub...")
        try:
            # 等待 URL 变更为 github.com
            page.wait_for_url(lambda url: "github.com" in url, timeout=15000)
            
            # GitHub 页面截图
            take_screenshot(page, "05_github_login_page", screenshot_counter)
            screenshot_counter += 1
            
            # 如果是在登录页，则填写账号密码
            if "login" in page.url:
                print("🔒 输入账号密码...")
                
                # 填写用户名前截图
                take_screenshot(page, "06_before_username_input", screenshot_counter)
                screenshot_counter += 1
                
                page.fill("#login_field", username)
                
                # 填写用户名后截图
                take_screenshot(page, "07_after_username_input", screenshot_counter)
                screenshot_counter += 1
                
                page.fill("#password", password)
                
                # 填写密码后截图（密码字段会显示为点，但截图可看到表单状态）
                take_screenshot(page, "08_after_password_input", screenshot_counter)
                screenshot_counter += 1
                
                page.click("input[name='commit']") # 点击登录按钮
                
                # 点击登录按钮后截图
                take_screenshot(page, "09_after_login_submit", screenshot_counter)
                screenshot_counter += 1
                
                print("📤 登录表单已提交")
        except Exception as e:
            print(f"ℹ️ 跳过账号密码填写 (可能已自动登录): {e}")

        # 5. 【核心】处理 2FA 双重验证 (解决异地登录拦截)
        # 给页面一点时间跳转
        page.wait_for_timeout(3000)
        
        # 2FA 页面截图（如果有）
        take_screenshot(page, "10_before_2fa_check", screenshot_counter)
        screenshot_counter += 1
        
        # 检查 URL 是否包含 two-factor 或页面是否有验证码输入框
        if "two-factor" in page.url or page.locator("#app_totp").count() > 0:
            print("🔐 [Step 5] 检测到 2FA 双重验证请求！")
            
            if totp_secret:
                print("🔢 正在计算动态验证码 (TOTP)...")
                try:
                    # 使用密钥生成当前的 6 位验证码
                    totp = pyotp.TOTP(totp_secret)
                    token = totp.now()
                    print(f"   生成的验证码: {token}")
                    
                    # 2FA 页面截图（填写前）
                    take_screenshot(page, "11_2fa_page_before_input", screenshot_counter)
                    screenshot_counter += 1
                    
                    # 填入 GitHub 的验证码输入框 (ID 通常是 app_totp)
                    page.fill("#app_totp", token)
                    
                    # 2FA 页面截图（填写后）
                    take_screenshot(page, "12_2fa_page_after_input", screenshot_counter)
                    screenshot_counter += 1
                    
                    print("✅ 验证码已填入，GitHub 应会自动跳转...")
                    
                    # 某些情况下可能需要手动回车，这里做个保险
                    # page.keyboard.press("Enter")
                    
                except Exception as e:
                    print(f"❌ 填入验证码失败: {e}")
            else:
                print("❌ 致命错误: 检测到 2FA 但未配置 GH_2FA_SECRET Secret！")
                take_screenshot(page, "error_2fa_secret_missing", screenshot_counter)
                screenshot_counter += 1
                exit(1)

        # 6. 处理授权确认页 (Authorize App)
        # 第一次登录可能会出现
        page.wait_for_timeout(3000)
        
        # 授权页面前截图
        take_screenshot(page, "13_before_authorize_check", screenshot_counter)
        screenshot_counter += 1
        
        if "authorize" in page.url.lower():
            print("⚠️ 检测到授权请求，尝试点击 Authorize...")
            try:
                # 授权页截图（点击前）
                take_screenshot(page, "14_authorize_page_before_click", screenshot_counter)
                screenshot_counter += 1
                
                page.click("button:has-text('Authorize')", timeout=5000)
                
                # 授权页截图（点击后）
                take_screenshot(page, "15_authorize_page_after_click", screenshot_counter)
                screenshot_counter += 1
                
            except:
                pass

        # 7. 等待最终跳转结果
        print("⏳ [Step 6] 等待跳转回 ClawCloud 控制台 (约20秒)...")
        
        # 等待过程中的中间状态截图
        take_screenshot(page, "16_before_final_wait", screenshot_counter)
        screenshot_counter += 1
        
        # 强制等待较长时间，确保页面完全重定向
        page.wait_for_timeout(5000)
        
        take_screenshot(page, "17_mid_wait_5s", screenshot_counter)
        screenshot_counter += 1
        
        page.wait_for_timeout(5000)
        
        take_screenshot(page, "18_mid_wait_10s", screenshot_counter)
        screenshot_counter += 1
        
        page.wait_for_timeout(10000)
        
        # 最终页面截图
        take_screenshot(page, "19_final_page_after_wait", screenshot_counter)
        screenshot_counter += 1
        
        final_url = page.url
        print(f"📍 最终页面 URL: {final_url}")
        
        # 最终结果截图（之前的截图函数已覆盖）
        page.screenshot(path="login_result.png")
        print("📸 已保存最终结果截图: login_result.png")

        # 8. 验证是否成功
        # 成功的标志：URL 不再是 GitHub，且包含控制台特征
        is_success = False
        
        # 检查点 A: 页面包含特定文字 (最准确)
        if page.get_by_text("App Launchpad").count() > 0 or page.get_by_text("Devbox").count() > 0:
            is_success = True
        # 检查点 B: URL 包含 console 特征
        elif "private-team" in final_url or "console" in final_url:
            is_success = True
        # 检查点 C: 只要不是登录页也不是 GitHub 验证页
        elif "signin" not in final_url and "github.com" not in final_url:
            is_success = True

        # 最终状态截图
        status_name = "success" if is_success else "failed"
        take_screenshot(page, f"20_final_status_{status_name}", screenshot_counter)
        
        if is_success:
            print("🎉🎉🎉 登录成功！任务完成。")
        else:
            print("😭😭😭 登录失败。请查看所有截图文件分析原因。")
            exit(1) # 抛出错误代码，让 Action 变红

        browser.close()
        
        # 打印所有截图信息
        print("\n📁 本次登录过程已保存以下截图：")
        for i in range(1, screenshot_counter + 1):
            print(f"  - screenshot_{i:02d}_*.png")

if __name__ == "__main__":
    run_login()
