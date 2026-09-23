#!/bin/zsh
# 雙擊檢查 posts 裡的內容有沒有問題（只看不改）
cd "$(dirname "$0")" || exit 1
python3 check.py
echo ""
echo "（這個視窗可以直接關掉）"
