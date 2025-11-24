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
        required_columns = ['IP 地址', '平均延迟']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"CSV文件中缺少必要的列: {col}")
        
        # 按平均延迟排序，取前top_n个（延迟越低越好）
        df_sorted = df.sort_values('平均延迟', ascending=True).head(top_n)
        
        # 提取IP地址列表
        ip_list = df_sorted['IP 地址'].tolist()
        
        print(f"从 {csv_file} 中获取到前 {top_n} 个延迟最低的IP:")
        for i, ip in enumerate(ip_list):
            latency = df_sorted.iloc[i]['平均延迟']
            print(f"  {i+1}. {ip} (延迟: {latency} ms)")
        
        return ip_list
        
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV文件不存在: {csv_file}")
    except Exception as e:
        raise Exception(f"读取CSV文件时出错: {e}")
def parse_record_names(record_names_str: str) -> List[str]:
    """
    解析记录名字符串，支持逗号、分号、空格分隔
    
    Args:
        record_names_str: 记录名字符串
    
    Returns:
        记录名列表
    """
    if not record_names_str:
        return []
    
    # 支持多种分隔符：逗号、分号、空格
    import re
    record_names = re.split(r'[,\s;]+', record_names_str.strip())
    
    # 过滤空字符串
    record_names = [name.strip() for name in record_names if name.strip()]
    
    print(f"解析到 {len(record_names)} 个域名记录:")
    for i, name in enumerate(record_names):
        print(f"  {i+1}. {name}")
    
    return record_names

def update_cloudflare_dns(ip_list: List[str]) -> None:
    """
    更新Cloudflare DNS记录，每个域名匹配一个IP
    
    Args:
        ip_list: IP地址列表
    """
    cf_token = os.environ.get("CF_API_TOKEN")
    zone_id = os.environ.get("CF_ZONE_ID")
    record_names_str = os.environ.get("CF_RECORD_NAME", "")

    if not (cf_token and zone_id and record_names_str):
        raise ValueError("缺少 CF_API_TOKEN / CF_ZONE_ID / CF_RECORD_NAME 环境变量")

    # 解析多个记录名
    record_names = parse_record_names(record_names_str)
    if not record_names:
        raise ValueError("CF_RECORD_NAME 环境变量中没有有效的域名记录")

    headers = {
        "Authorization": f"Bearer {cf_token}",
        "Content-Type": "application/json",
    }

    if not ip_list:
        print("⚠️ 没有获取到新的 IP，本次跳过更新，保留现有 DNS 配置")
        return

    # 检查域名和IP数量是否匹配
    if len(record_names) > len(ip_list):
        print(f"⚠️ 警告: 域名数量({len(record_names)})多于IP数量({len(ip_list)})，部分域名将无法分配IP")
    elif len(ip_list) > len(record_names):
        print(f"ℹ️ 信息: IP数量({len(ip_list)})多于域名数量({len(record_names)})，将使用前{len(record_names)}个IP")

    # 取最小数量，确保每个域名都能匹配到一个IP
    min_count = min(len(record_names), len(ip_list))
    matched_domains = record_names[:min_count]
    matched_ips = ip_list[:min_count]

    print(f"\n🔗 域名与IP匹配关系:")
    for i, (domain, ip) in enumerate(zip(matched_domains, matched_ips)):
        print(f"  {i+1}. {domain} -> {ip}")

    # 为每个域名清理旧记录并添加新记录
    total_success = 0
    
    for i, (record_name, ip) in enumerate(zip(matched_domains, matched_ips)):
        print(f"\n🔄 正在处理域名 {i+1}/{min_count}: {record_name}")
        
        # 先获取该域名的现有记录，全部删除
        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={record_name}"
        resp = requests.get(url, headers=headers).json()
        
        deleted_count = 0
        if resp["success"] and resp["result"]:
            for record in resp["result"]:
                record_id = record["id"]
                del_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
                delete_resp = requests.delete(del_url, headers=headers).json()
                if delete_resp["success"]:
                    print(f"  ✅ 已删除旧记录: {record['name']} -> {record['content']}")
                    deleted_count += 1
                else:
                    print(f"  ❌ 删除旧记录失败: {record['name']}")
            print(f"  📝 已清理 {deleted_count} 条旧的 DNS 记录: {record_name}")

        # 为该域名新建单条 A 记录
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
            print(f"  ✅ 已添加 DNS 记录: {record_name} -> {ip}")
            total_success += 1
        else:
            print(f"  ❌ 添加失败: {record_name} -> {ip}, 错误: {resp.get('errors', '未知错误')}")

    print(f"\n🎯 DNS 更新完成!")
    print(f"📈 成功更新: {total_success}/{min_count} 条记录")
    
    # 显示未使用的资源
    if len(record_names) > min_count:
        unused_domains = record_names[min_count:]
        print(f"⚠️ 未使用的域名: {', '.join(unused_domains)}")
    
    if len(ip_list) > min_count:
        unused_ips = ip_list[min_count:]
        print(f"ℹ️ 未使用的IP: {', '.join(unused_ips)}")

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


