#!/bin/zsh
# 雙擊：幫還沒有文案的資料夾補上文案；都有的話才開新的一篇
cd "$(dirname "$0")" || exit 1
mkdir -p posts posted

# 先找有圖但還沒有文案的資料夾（編號最小的優先）
TARGET=""
for d in posts/*/(N); do
  if [ -z "$(find "$d" -maxdepth 1 -name '*.txt' -print -quit 2>/dev/null)" ]; then TARGET="${d%/}/文案.txt"; break; fi
done

if [ -n "$TARGET" ]; then
  : > "$TARGET"
  echo "這個資料夾還沒有文案，幫你補上：$TARGET"
else
  LAST=$(ls posts posted 2>/dev/null | sed -n 's/^\([0-9]\{1,\}\).*/\1/p' | sort -n | tail -1)
  NEXT=$(printf "%03d" $(( 10#${LAST:-0} + 1 )))
  TARGET="posts/$NEXT.txt"
  [ -e "$TARGET" ] || : > "$TARGET"
  echo "已建立新的一篇：$TARGET"
fi

open -a TextEdit "$TARGET"

echo ""
echo "==============================="
echo " 接下來："
echo "  1. 在剛打開的視窗裡寫，簡體也沒關係"
echo "  2. Command+S 存檔，關掉視窗"
echo "  3. 雙擊「同步到雲端」：會自動轉繁體、轉圖檔、檢查"
echo "==============================="
echo ""
echo "（這個視窗可以直接關掉）"
