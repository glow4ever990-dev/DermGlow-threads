#!/bin/zsh
# 雙擊這個圖示，自動建好下一篇的 txt 並打開，寫完存檔就行
cd "$(dirname "$0")" || exit 1
mkdir -p posts posted

# 找出目前用到的最大編號（posts 和 posted 都看，避免重號）
LAST=$(ls posts posted 2>/dev/null | sed -n 's/^\([0-9]\{1,\}\).*/\1/p' | sort -n | tail -1)
NEXT=$(printf "%03d" $(( 10#${LAST:-0} + 1 )))
FILE="posts/$NEXT.txt"

if [ -e "$FILE" ]; then
  echo "$FILE 已經存在，直接打開"
else
  : > "$FILE"
  echo "已建立 $FILE"
fi

open -a TextEdit "$FILE"

echo ""
echo "==============================="
echo " 接下來："
echo "  1. 在剛打開的視窗裡寫文案（最多 500 字）"
echo "  2. 想帶話題標籤就在最後加一行，例如 #澳洲生活"
echo "  3. 按 Command+S 存檔，關掉視窗"
echo "  4. 回桌面雙擊「同步到雲端」"
echo "==============================="
echo ""
echo "（這個視窗可以直接關掉）"
