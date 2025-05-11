import pandas as pd
import sys
import requests
import json

def get_country(ip):
    """
    通过 API 获取 IP 地址的归属地国家。

    Args:
        ip: IP 地址字符串。

    Returns:
        国家名称字符串，如果获取失败则返回 "Unknown"。
    """
    try:
        url = f"https://dooh.pk67.dpdns.org/ip-info?ip={ip}"
        response = requests.get(url)
        response.raise_for_status()  # 检查 HTTP 状态码是否正常
        data = response.json()
        if data['status'] == 'success':
            return data['country']
        else:
            return "Unknown"
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IP info for {ip}: {e}")
        return "Unknown"
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response for {ip}: {e}")
        return "Unknown"


def csv_to_txt(csv_filename, output_filename, area_name):
    """
    将 CSV 文件中的 IP 地址和下载速度提取出来，并写入到 TXT 文件中，
    同时通过 API 获取 IP 地址的归属地国家，并添加到输出字符串中。
    """
    df = pd.read_csv(csv_filename, encoding='utf-8')
    ips = df.iloc[:, 0]
    download_speeds = df.iloc[:, 5]

    with open(output_filename, 'w', encoding='utf-8') as f:
        for i, (ip, speed) in enumerate(zip(ips, download_speeds)):
            country = get_country(ip)
            f.write(f"{ip}#{area_name}{i+1}+{country}\n")

def csv_to_txtt(csv_filename, output_filename, area_name):
    df = pd.read_csv(csv_filename, encoding='utf-8')
    ips = df.iloc[:, 0]
    download_speeds = df.iloc[:, 5]

    with open(output_filename, 'w', encoding='utf-8') as f:
        for i, (ip, speed) in enumerate(zip(ips, download_speeds)):
            country = get_country(ip)
            f.write(f"{ip}:2087#{area_name}{i+1}+{country}\n")
            
csv_to_txt("HKG.csv", "ivv.txt", "xn")
csv_to_txtt("HKG.csv", "valid_ips.txt", "xn")
