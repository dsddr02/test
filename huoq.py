import os
import re
from playwright.sync_api import sync_playwright
import requests
import time
from datetime import datetime

def get_telecom_ips():
    url = os.environ.get("TARGET_URL")
    if not url:
        raise ValueError("缺少环境变量 TARGET_URL")

    ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"

    today_str = datetime.now().strftime("%Y/%m/%d")
    telecom_ips = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")

        # 最多等待 60 秒，直到表格中出现今天的日期
        found_today = False
        for _ in range(60):
            rows = page.query_selector_all("table.table-striped tbody tr")
            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) >= 8:
                    last_update = cells[-1].inner_text().strip()
                    if last_update.startswith(today_str):
                        found_today = True
                        break
            if found_today:
                break
            time.sleep(1)

        if not found_today:
            print("未能捕获到今天的数据，可能是接口未更新或反爬限制。")
        
        # 提取电信 IP
        rows = page.query_selector_all("table.table-striped tbody tr")

        print("抓取到的行数:", len(rows))

        for row in rows:
            cells = row.query_selector_all("th, td")
            if len(cells) >= 3:
                isp = cells[1].inner_text().strip()
                ip = cells[2].inner_text().strip()
                print("调试行:", isp, ip)  # 调试用
                if isp == "移动" and re.match(ip_pattern, ip):
                    telecom_ips.append(ip)

        browser.close()

    unique_ips = sorted(set(telecom_ips))
    with open("ip.txt", "w", encoding="utf-8") as f:
        for ip in unique_ips:
            f.write(ip + "\n")

    print(f"成功提取 {len(unique_ips)} 个电信IP地址，已保存到 ip.txt")
    for ip in unique_ips[:10]:
        print(" -", ip)

    return unique_ips

if __name__ == "__main__":
    get_telecom_ips()
