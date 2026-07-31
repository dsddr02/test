import time
import random
import logging
from pathlib import Path
from cloakbrowser import launch
from fake_useragent import UserAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(name)

# 要访问的HF(抱脸)space地址支持多个
URLS = [
    "https://mowupo-mohujj.hf.space"
    ]

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

def visit_url(page, url, index):
    try:
        logger.info(f"[{index}] 正在访问: {url}")

        time.sleep(random.uniform(0.5, 2.0))

        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        page.wait_for_timeout(random.randint(1000, 3000))

        page.mouse.move(random.randint(100, 800), random.randint(100, 600))

        page.evaluate("window.scrollBy(0, 200)")

        title = page.title()
        logger.info(f"[{index}] 页面标题: {title}")

        safe_name = url.replace("https://", "").replace("/", "_").replace(".", "_")
        screenshot_path = SCREENSHOT_DIR / f"{index:02d}_{safe_name}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"[{index}] 截图保存: {screenshot_path}")

        return {"url": url, "title": title, "status": "success"}

    except Exception as e:
        logger.error(f"[{index}] 访问失败: {e}")
        error_path = SCREENSHOT_DIR / f"error_{index:02d}.png"
        try:
            page.screenshot(path=str(error_path))
        except:
            pass
        return {"url": url, "error": str(e), "status": "failed"}

def batch_visit():
    browser = launch(
        headless=True,
        humanize=True,          
        args=[
            "--no-sandbox",           
            "--disable-dev-shm-usage",
        ]
    )

    ua = UserAgent()
    results = []

    for idx, url in enumerate(URLS, 1):
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=ua.random,
        )
        page = context.new_page()

        result = visit_url(page, url, idx)
        results.append(result)

        context.close() 

    browser.close() 

    success = sum(1 for r in results if r["status"] == "success")
    logger.info(f"✅ 完成：成功 {success}/{len(URLS)}")
    return results

if name == "main":
    batch_visit()
