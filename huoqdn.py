import os
import requests
import pandas as pd
from typing import List

def get_top_ips_from_csv(csv_file: str, top_n: int = 5) -> List[str]:
    """
    从CSV文件中获取延迟最低的top N个IP地址
    
    Args:
        csv_file: CSV文件路径
        top_n: 要获取的IP数量，默认为5
    
    Returns:
        IP地址列表
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file)
        
        # 确保必要的列存在
        required_columns = ['IP 地址', '下载速度(MB/s)']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"CSV文件中缺少必要的列: {col}")
        
        # 按平均延迟排序，取前top_n个
        df_sorted = df.sort_values('下载速度(MB/s)').head(top_n)
        
        # 提取IP地址列表
        ip_list = df_sorted['IP 地址'].tolist()
        
        print(f"从 {csv_file} 中获取到前 {top_n} 个最低延迟的IP:")
        for ip in ip_list:
            print(f"  - {ip}")
        
        return ip_list
        
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV文件不存在: {csv_file}")
    except Exception as e:
        raise Exception(f"读取CSV文件时出错: {e}")

def update_cloudflare_dns(ip_list: List[str]) -> None:
    """
    更新Cloudflare DNS记录
    
    Args:
        ip_list: IP地址列表
    """
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
            delete_resp = requests.delete(del_url, headers=headers).json()
            if delete_resp["success"]:
                print(f"✅ 已删除旧记录: {record['name']} -> {record['content']}")
            else:
                print(f"❌ 删除旧记录失败: {record['name']}")
        print(f"已清理旧的 DNS 记录: {record_name}")

    # 新建多条 A 记录
    success_count = 0
    for ip in ip_list:
        data = {
            "type": "A",
            "name": record_name,
            "content": ip,
            "ttl": 300,     # 5分钟
            "proxied": False,  # 如果你要走CF代理，可以改成 True
        }
        add_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
        resp = requests.post(add_url, headers=headers, json=data).json()
        if resp["success"]:
            print(f"✅ 已添加 DNS 记录: {record_name} -> {ip}")
            success_count += 1
        else:
            print(f"❌ 添加失败: {ip}, 错误: {resp.get('errors', '未知错误')}")

    print(f"\n📊 DNS 更新完成: 成功添加 {success_count}/{len(ip_list)} 条记录")

def main():
    """
    主函数：从CSV获取IP并更新DNS
    """
    csv_file = "result.csv"  # 可以根据需要修改文件名
    top_n = 5  # 可以根据需要修改数量
    
    try:
        # 从CSV文件获取top IP
        print("🚀 开始从CSV文件获取IP地址...")
        ip_list = get_top_ips_from_csv(csv_file, top_n)
        
        # 更新Cloudflare DNS
        print("\n🔄 开始更新Cloudflare DNS记录...")
        update_cloudflare_dns(ip_list)
        
        print("\n🎉 所有操作已完成！")
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        exit(1)

if __name__ == "__main__":
    main()




