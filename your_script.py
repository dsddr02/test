import time
import random
import logging
from pathlib import Path
# 注意：cloakbrowser、fake_useragent 需要提前安装
# pip install cloakbrowser fake-useragent
from cloakbrowser import launch
from fake_useragent import UserAgent

# 日志基础配置（清理非法空格，标准英文空格）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# 修复 __name__ 变量
logger = logging.getLogger(__name__)

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

        # 跳转页面，超时60秒
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(random.randint(1000, 3000))

        # 模拟鼠标移动
        page.mouse.move(random.randint(100, 800), random.randint(100, 600))
        # 页面向下滚动
        page.evaluate("window.scrollBy(0, 200)")

        title = page.title()
        logger.info(f"[{index}] 页面标题: {title}")

        # 处理文件名特殊字符
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
        except Exception:
            pass
        return {"url": url, "error": str(e), "status": "failed"}


def batch_visit():
    # 启动浏览器
    browser = launch(
        headless=True,
        humanize=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
    )

    # 兼容fake_useragent加载失败场景
    try:
        ua = UserAgent()
        random_ua = ua.random
    except Exception:
        # 加载UA库失败时使用兜底UA
        random_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    results = []

    for idx, url in enumerate(URLS, 1):
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=random_ua,
        )
        page = context.new_page()

        result = visit_url(page, url, idx)
        results.append(result)

        # 关闭当前上下文释放资源
        context.close()

    browser.close()

    success = sum(1 for r in results if r["status"] == "success")
    logger.info(f"✅ 完成：成功 {success}/{len(URLS)}")
    return results


# 修复入口判断 __name__ == "__main__"
if __name__ == "__main__":
    batch_visit()
