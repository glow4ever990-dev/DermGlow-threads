#!/bin/zsh
# 雙擊：把「下載」資料夾裡剛存的圖片和影片收進新的一篇貼文
cd "$(dirname "$0")" || exit 1
mkdir -p posts posted

HOURS=${1:-12}       # 只看最近幾小時內下載的，預設 12 小時
FILES=()
while IFS= read -r f; do FILES+=("$f"); done < <(
  find "$HOME/Downloads" -maxdepth 1 -type f \
    \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.heic' \
       -o -iname '*.mp4' -o -iname '*.mov' \) \
    -newermt "-${HOURS} hours" 2>/dev/null | sort
)

if [ ${#FILES[@]} -eq 0 ]; then
  echo "最近 $HOURS 小時內，下載資料夾裡沒有圖片或影片。"
  echo ""
  echo "（這個視窗可以直接關掉）"
  exit 0
fi

echo "找到這些檔案（最近 $HOURS 小時內下載的）："
echo ""
for f in "${FILES[@]}"; do echo "   $(basename "$f")"; done
echo ""

LAST=$(ls posts posted 2>/dev/null | sed -n 's/^\([0-9]\{1,\}\).*/\1/p' | sort -n | tail -1)
NEXT=$(printf "%03d" $(( 10#${LAST:-0} + 1 )))

echo -n "把這 ${#FILES[@]} 個檔案收進新的一篇（$NEXT）嗎？[y = 好 / 其他鍵 = 算了]："
read -r ANS
[ "$ANS" = "y" ] || [ "$ANS" = "Y" ] || { echo "沒有動任何檔案。"; exit 0; }

mkdir -p "posts/$NEXT"
i=1
for f in "${FILES[@]}"; do
  EXT="${f##*.}"
  mv "$f" "posts/$NEXT/$i.${EXT:l}"    # 改成 1.jpg 2.jpg…，順序就是發布順序
  echo "   → posts/$NEXT/$i.${EXT:l}"
  i=$((i + 1))
done

: > "posts/$NEXT/文案.txt"
open -a TextEdit "posts/$NEXT/文案.txt"

echo ""
echo "==============================="
echo " 檔案收好了，文案視窗也開了"
echo "  1. 寫文案，Command+S 存檔"
echo "  2. 雙擊「同步到雲端」"
echo "  （HEIC 會在同步時自動轉成 jpg）"
echo "==============================="
echo ""
echo "（這個視窗可以直接關掉）"
