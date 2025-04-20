import pandas as pd
import sys

def csv_to_txt(csv_filename, output_filename, area_name):
    df = pd.read_csv(csv_filename, encoding='utf-8')
    ips = df.iloc[:, 0]
    download_speeds = df.iloc[:, 5]

    with open(output_filename, 'w', encoding='utf-8') as f:
        for i, (ip, speed) in enumerate(zip(ips, download_speeds)):
            #f.write(f"{ip}:8443#{area_name}{i+1}\n")
            f.write(f"{ip}\n")
def csv_to_txtt(csv_filename, output_filename, area_name):
    df = pd.read_csv(csv_filename, encoding='utf-8')
    ips = df.iloc[:, 0]
    download_speeds = df.iloc[:, 5]

    with open(output_filename, 'w', encoding='utf-8') as f:
        for i, (ip, speed) in enumerate(zip(ips, download_speeds)):
            f.write(f"{ip}:8443#{area_name}{i+1}\n")
            
csv_to_txt("HKG.csv", "ivv.txt", "xn")
csv_to_txtt("HKG.csv", "valid_ips.txt", "xn")
