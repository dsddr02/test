#!/bin/bash
export LANG=zh_CN.UTF-8

if [ -z "$DOMAIN" ] || [ -z "$TOKEN" ] || [ -z "$FILENAME" ]; then
  echo "错误：缺少必须的环境变量 (DOMAIN, TOKEN, FILENAME)"
  exit 1
fi

if [ ! -f "$FILENAME" ]; then
  echo "错误：文件 $FILENAME 不存在"
  exit 1
fi

BASE64_TEXT=$(head -n 65 "$FILENAME" | base64 -w 0)
curl -s -k "https://${DOMAIN}/${FILENAME}?token=${TOKEN}&b64=${BASE64_TEXT}"
if [ $? -eq 0 ]; then
  echo "成功更新 $FILENAME"
else
  echo "更新 $FILENAME 失败"
  exit 1
fi
