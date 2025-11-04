import pandas as pd

def csv_to_txt(csv_filename, output_filename, area_name):
    df = pd.read_csv(csv_filename, encoding='utf-8')
    
    # 按TCP延迟列排序并取前9个
    df_sorted = df.sort_values(by=df.columns[6])  # 第7列是TCP延迟
    top_9_ips = df_sorted.iloc[:9, 0]  # 前9行的第1列（IP地址）
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        for ip in top_9_ips:
            f.write(f"{ip}\n")
    
    
def csv_to_txtt(csv_filename, output_filename, area_name):
    df = pd.read_csv(csv_filename, encoding='utf-8')
    df_sorted = df.sort_values(by=df.columns[6])  # 第7列是TCP延迟
    top_9_ips = df_sorted.iloc[:9, 0]  # 前9行的第1列（IP地址）
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        for ip in top_9_ips:
            f.write(f"{ip}:2087#{area_name}{i+1}\n")
            
csv_to_txt("result.csv", "yd.txt", "xn")
csv_to_txtt("result.csv", "valid_ipsyd.txt", "xn")
