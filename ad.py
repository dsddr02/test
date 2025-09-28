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
                if isp == "电信" and re.match(ip_pattern, ip):
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



def update_cloudflare_dns(ip_list):
    cf_token = os.environ.get("CF_API_TOKEN")
    zone_id = os.environ.get("CF_ZONE_ID")
    record_name = os.environ.get("CF_RECORD_NAME")

    if not (cf_token and zone_id and record_name):
        raise ValueError("缺少 CF_API_TOKEN / CF_ZONE_ID / CF_RECORD_NAME 环境变量")

    headers = {
        "Authorization": f"Bearer {cf_token}",
        "Content-Type": "application/json",
    }

    if not ip_list:
        print("⚠️ 没有获取到新的 IP，本次跳过更新，保留现有 DNS 配置")
        return

    # 先获取现有记录，全部删除
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={record_name}"
    resp = requests.get(url, headers=headers).json()
    if resp["success"] and resp["result"]:
        for record in resp["result"]:
            record_id = record["id"]
            del_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
            requests.delete(del_url, headers=headers)
        print(f"已清理旧的 DNS 记录: {record_name}")

    # 新建多条 A 记录
    for ip in ip_list:
        data = {
            "type": "A",
            "name": record_name,
            "content": ip,
            "ttl": 60,     # 5分钟
            "proxied": False,  # 如果你要走CF代理，可以改成 True
        }
        add_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
        resp = requests.post(add_url, headers=headers, json=data).json()
        if resp["success"]:
            print(f"✅ 已添加 ")
        else:
            print(f"❌ 添加失败: {ip}, {resp}")


if __name__ == "__main__":
    ips = get_telecom_ips()
    update_cloudflare_dns(ips)
